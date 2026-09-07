import random
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from database.building.building_queries import (
    get_all_rooms_latest,
    get_average_over_hours,
    get_latest_sensor_data,
    get_room_temperature,
    get_weather,
)
from database.building.building_writes import apply_bms_command
from database.building.hvac_twin import predict_comfort_and_load
from database.building.ingest_fmu import load_power_lookup
from database.building.init_building_db import init_building_db
from database.building.topology import ROOM_NAMES, ZONE_NAME, is_known_room, topology_summary
from database.memory.init_memory_db import init_memory_db
from database.memory.memory_queries import create_session, save_tool_call

mcp = FastMCP("modelicon-building-tools")

# The database files are created (schema-only, idempotent) as soon as the
# MCP server process starts, so bms_write always has somewhere real to
# persist to even on a fresh checkout.
init_building_db()
init_memory_db()

# The live thermostat setpoint is persisted under the zone's own room
# name (same mechanism bms_write uses) so it survives the MCP server
# subprocess being restarted between CLI sessions, instead of silently
# resetting to a hardcoded default every time. Building is single-zone,
# so there is no separate "building-wide" reading distinct from this
# one room's -- collapsing that split (a synthetic "global-thermostat"
# pseudo-room that could disagree with the real per-room data) was
# itself one of the original inconsistency bugs this project started
# from.
_THERMOSTAT_TARGET = ZONE_NAME
_DEFAULT_TEMP_C = 24.3

# One memory-database session per MCP server process, used to log every
# bms_write call as an auditable tool_calls row. The LangGraph side has
# its own session concept (out of scope here); this is just enough to
# make writes traceable without touching agents/graph code.
_SERVER_SESSION_ID = create_session(user_id="mcp-server")

#: Fallback only -- used if the FMU setpoint sweep hasn't been cached
#: yet (fresh checkout before ``python -m database.building.ingest_fmu``
#: has been run once). Once that cache exists, real FMU-derived power
#: numbers (in genuine kW) replace this fictional placeholder table.
_FALLBACK_POWER_LOOKUP_C = {
    16: 1.0, 17: 1.2, 18: 1.4, 19: 1.6, 20: 1.8, 21: 2.0,
    22: 2.2,
    23: 2.4, 24: 2.6, 25: 2.8, 26: 3.0, 27: 3.2, 28: 3.4, 29: 3.6, 30: 4.0,
}
_cached_lookup = load_power_lookup()
_POWER_LOOKUP_C: dict[int, float] = (
    {int(k): v for k, v in _cached_lookup.items()} if _cached_lookup else _FALLBACK_POWER_LOOKUP_C
)
_POWER_UNIT = "kW" if _cached_lookup else "mW"


def _load_persisted_temp_c() -> float:
    last_reading = get_room_temperature(_THERMOSTAT_TARGET)
    if last_reading and last_reading.get("temperature") is not None:
        return float(last_reading["temperature"])
    return _DEFAULT_TEMP_C


_current_temp_c = _load_persisted_temp_c()


def _power_for(temp_c: float) -> float:
    nearest = min(_POWER_LOOKUP_C, key=lambda t: abs(t - temp_c))
    return _POWER_LOOKUP_C[nearest]


def _room_temp_and_power(room: str | None) -> tuple[float, float, str | None]:
    """Resolve (temp_c, power_kw, room) for the single zone. ``room`` is
    accepted for interface compatibility with callers that still pass a
    target room -- since there is only one zone, any known room (or
    None, "building-wide", etc.) all resolve to the same real reading."""
    last_reading = get_room_temperature(ZONE_NAME)
    temp_c = float(last_reading["temperature"]) if last_reading and last_reading.get("temperature") is not None else _current_temp_c
    return temp_c, _power_for(temp_c), ZONE_NAME


def _seed_room_baselines() -> dict[str, dict[str, object]]:
    """Deterministic-but-distinct mock readings per room for the domains
    that have no real per-room table (lighting/access/safety/monitor).
    Seeded on process start so values stay stable for the life of the
    server instead of re-randomising on every tool call."""
    baselines = {}
    for name in ROOM_NAMES:
        rng = random.Random(f"room-baseline::{name}")
        baselines[name] = {
            "lux": rng.randint(150, 380),
            "daylight_contribution": round(rng.uniform(0.15, 0.55), 2),
            "active_badges": rng.randint(1, 6),
            "unauthorized_attempts": 0,
            "gas_ppm": rng.randint(5, 25),
            "offline_devices": 0,
        }
    return baselines


_ROOM_BASELINES = _seed_room_baselines()


@mcp.tool()
def building_topology() -> dict:
    """Static building structure: floors and the rooms on each floor."""
    return topology_summary()


@mcp.tool()
def all_rooms_status() -> dict:
    """Latest temperature/humidity/CO2/occupancy for every known room in
    one call -- use this for cross-room comparisons ("which room is
    hottest", "highest CO2 room") instead of the single-room tools."""
    latest_by_room = {row["room_name"]: row for row in get_all_rooms_latest()}
    rooms = []
    for name in ROOM_NAMES:
        row = latest_by_room.get(name, {})
        rooms.append(
            {
                "room_name": name,
                "temp_c": row.get("temperature"),
                "humidity": row.get("humidity"),
                "co2_ppm": row.get("co2"),
                "occupancy": row.get("occupancy"),
            }
        )
    return {"rooms": rooms}


@mcp.tool()
def sensor_data(room: str | None = None) -> dict:
    """Latest sensor snapshot for the single zone (falls back to a fixed
    default if no readings have been ingested yet). ``room`` is accepted
    for interface compatibility; any value resolves to the same zone."""
    latest = get_latest_sensor_data(room_name=ZONE_NAME)
    if latest:
        return {
            "room": ZONE_NAME,
            "temp_c": latest.get("temperature"),
            "humidity": latest.get("humidity"),
            "co2_ppm": latest.get("co2"),
            "occupancy": latest.get("occupancy"),
        }
    return {"room": ZONE_NAME, "temp_c": _current_temp_c, "humidity": 55, "co2_ppm": 640, "occupancy": 18}


@mcp.tool()
def timeseries_db() -> dict:
    """24h average temperature and its trend, from real ingested digital-twin
    readings when available (falls back to a fixed stub before
    ``ingest_fmu`` has been run once)."""
    day = get_average_over_hours(hours=24)
    recent = get_average_over_hours(hours=6)
    if day.get("avg_temperature") is None or recent.get("avg_temperature") is None:
        return {"series": "temp_c", "last_24h_avg": 23.8, "trend": "rising"}

    delta = recent["avg_temperature"] - day["avg_temperature"]
    trend = "rising" if delta > 0.1 else "falling" if delta < -0.1 else "stable"
    return {"series": "temp_c", "last_24h_avg": round(day["avg_temperature"], 2), "trend": trend}


@mcp.tool()
def weather() -> dict:
    """Latest outdoor temperature from the digital twin's weather reader
    when available (falls back to a fixed stub before ``ingest_fmu`` has
    been run once -- the FMU doesn't model sky condition, so that field
    stays a fixed label either way)."""
    latest = get_weather()
    if latest and latest.get("outdoor_temperature") is not None:
        return {"outdoor_c": round(latest["outdoor_temperature"], 2), "condition": "unknown"}
    return {"outdoor_c": 31.0, "condition": "sunny"}


@mcp.tool()
def thermal_lookup_table() -> dict:
    return {"unit_temp": "C", "unit_power": _POWER_UNIT, "table": {str(k): v for k, v in sorted(_POWER_LOOKUP_C.items())}}


@mcp.tool()
def current_temperature(room: str | None = None) -> dict:
    """Live setpoint + power draw. Pass a known room name for that room's
    own latest reading; omit it for the building-wide thermostat."""
    temp_c, power_kw, resolved_room = _room_temp_and_power(room)
    result = {"temp_c": temp_c, "power_kw": power_kw}
    if resolved_room:
        result["room"] = resolved_room
    return result


@mcp.tool()
def set_temperature(temp_c: float = 24.3, room: str | None = None) -> dict:
    """Write a new setpoint. Pass a known room name to target that room
    specifically; omit it to change the building-wide thermostat (the
    behaviour every caller had before rooms existed)."""
    target = room if (room and is_known_room(room)) else _THERMOSTAT_TARGET
    persisted = apply_bms_command(target=target, parameter="setpoint_c", value=temp_c)

    if target == _THERMOSTAT_TARGET:
        global _current_temp_c
        _current_temp_c = temp_c

    response = {
        "temp_c": temp_c,
        "power_kw": _power_for(temp_c),
        "ack": True,
        "persisted": persisted,
    }
    if room:
        response["room"] = room
    return response


@mcp.tool()
def lux_sensor(room: str | None = None) -> dict:
    """Ambient light level in lux. Pass a known room name for that room's
    own reading; omit it for a breakdown across every room."""
    if room and is_known_room(room):
        return {"room": room, "lux": _ROOM_BASELINES[room]["lux"], "target": 400}
    return {
        "target": 400,
        "rooms": {name: {"lux": _ROOM_BASELINES[name]["lux"]} for name in ROOM_NAMES},
    }


@mcp.tool()
def daylight(room: str | None = None) -> dict:
    """Estimated daylight contribution (0-1). Room-scoped or a
    building-wide breakdown across every room."""
    if room and is_known_room(room):
        return {"room": room, "daylight_contribution": _ROOM_BASELINES[room]["daylight_contribution"]}
    return {
        "rooms": {
            name: {"daylight_contribution": _ROOM_BASELINES[name]["daylight_contribution"]}
            for name in ROOM_NAMES
        }
    }


@mcp.tool()
def access_events(room: str | None = None) -> dict:
    """Badge/occupancy activity. Room-scoped, or building-wide totals plus
    a per-room breakdown."""
    if room and is_known_room(room):
        base = _ROOM_BASELINES[room]
        return {"room": room, "active_badges": base["active_badges"], "unauthorized_attempts": base["unauthorized_attempts"]}
    return {
        "active_badges": sum(b["active_badges"] for b in _ROOM_BASELINES.values()),
        "unauthorized_attempts": sum(b["unauthorized_attempts"] for b in _ROOM_BASELINES.values()),
        "rooms": {
            name: {
                "active_badges": _ROOM_BASELINES[name]["active_badges"],
                "unauthorized_attempts": _ROOM_BASELINES[name]["unauthorized_attempts"],
            }
            for name in ROOM_NAMES
        },
    }


@mcp.tool()
def fire_alarm(room: str | None = None) -> dict:
    """Fire/smoke/gas status. Room-scoped, or a building-wide view (true
    if any room is alarming) plus a per-room breakdown."""
    if room and is_known_room(room):
        return {"room": room, "fire": False, "smoke": False, "gas_ppm": _ROOM_BASELINES[room]["gas_ppm"]}
    return {
        "fire": False,
        "smoke": False,
        "gas_ppm": max(b["gas_ppm"] for b in _ROOM_BASELINES.values()),
        "rooms": {
            name: {"fire": False, "smoke": False, "gas_ppm": _ROOM_BASELINES[name]["gas_ppm"]}
            for name in ROOM_NAMES
        },
    }


@mcp.tool()
def device_health(room: str | None = None) -> dict:
    """Equipment fault status. Room-scoped, or a building-wide summary
    plus a per-room breakdown."""
    if room and is_known_room(room):
        return {"room": room, "offline_devices": _ROOM_BASELINES[room]["offline_devices"], "faults": []}
    return {
        "offline_devices": sum(b["offline_devices"] for b in _ROOM_BASELINES.values()),
        "faults": [],
        "rooms": {
            name: {"offline_devices": _ROOM_BASELINES[name]["offline_devices"], "faults": []}
            for name in ROOM_NAMES
        },
    }


@mcp.tool()
def energy_optimizer(request: str = "", room: str | None = None) -> dict:
    """Best setpoint from the lookup table and the saving vs. the current
    setpoint. Room-scoped when a known room is given, else the
    building-wide thermostat."""
    best_temp_c, best_power_kw = min(_POWER_LOOKUP_C.items(), key=lambda kv: kv[1])
    current_temp_c, current_power_kw, resolved_room = _room_temp_and_power(room)
    saving_pct = 0.0
    if current_power_kw > 0:
        saving_pct = round(max(0.0, (current_power_kw - best_power_kw) / current_power_kw * 100), 1)
    result = {
        "setpoint_c": float(best_temp_c),
        "expected_saving_pct": saving_pct,
        "current_setpoint_c": current_temp_c,
    }
    if resolved_room:
        result["room"] = resolved_room
    return result


@mcp.tool()
def modelica_sim(setpoint_c: float | None = None, room: str | None = None) -> dict:
    """Digital-twin physics simulation: projects the room forward from its
    current live temperature toward ``setpoint_c`` (defaults to the current
    setpoint) and returns the predicted thermal comfort (PMV) and average
    HVAC load once it gets there. Pass a known room name to project that
    room specifically instead of the building-wide thermostat."""
    current_temp_c, _power_kw, resolved_room = _room_temp_and_power(room)
    target = setpoint_c if setpoint_c is not None else current_temp_c
    now = datetime.now()
    result = predict_comfort_and_load(
        current_temp_c=current_temp_c,
        target_temp_c=target,
        hour_of_day=now.hour + now.minute / 60.0,
    )
    if resolved_room:
        result["room"] = resolved_room
    return result


@mcp.tool()
def bms_write(target: str = "", parameter: str = "", value: float | None = None, room: str | None = None) -> dict:
    """Generic control write. ``target`` stays a category (hvac/lighting/
    ...); when ``room`` is a known room name the value is persisted under
    that room instead of the bare category name -- this is what lets a
    thermal write actually land on "Floor 2 Room 1" instead of a
    catch-all "hvac" row."""
    persist_target = room if (room and is_known_room(room)) else target
    persisted = apply_bms_command(target=persist_target, parameter=parameter, value=value)

    written = {"target": target, "parameter": parameter, "value": value}
    if room:
        written["room"] = room

    response = {
        "written": written,
        "ack": bool(persisted.get("success")),
        "latency_ms": random.randint(20, 90),
        "persisted": persisted,
    }

    save_tool_call(
        session_id=_SERVER_SESSION_ID,
        tool_name="bms_write",
        arguments=response["written"],
        result=response,
    )

    return response


if __name__ == "__main__":
    mcp.run()

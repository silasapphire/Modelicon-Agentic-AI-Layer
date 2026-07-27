import random

from mcp.server.fastmcp import FastMCP

from database.building.building_queries import get_latest_sensor_data, get_room_temperature
from database.building.building_writes import apply_bms_command
from database.building.init_building_db import init_building_db
from database.building.topology import is_known_room, topology_summary
from database.memory.init_memory_db import init_memory_db
from database.memory.memory_queries import create_session, save_tool_call

mcp = FastMCP("modelicon-building-tools")

# The database files are created (schema-only, idempotent) as soon as the
# MCP server process starts, so bms_write always has somewhere real to
# persist to even on a fresh checkout.
init_building_db()
init_memory_db()

# The live thermostat setpoint is persisted under this well-known target
# name (same mechanism bms_write uses) so it survives the MCP server
# subprocess being restarted between CLI sessions, instead of silently
# resetting to a hardcoded default every time.
_THERMOSTAT_TARGET = "global-thermostat"
_DEFAULT_TEMP_C = 24.3

# One memory-database session per MCP server process, used to log every
# bms_write call as an auditable tool_calls row. The LangGraph side has
# its own session concept (out of scope here); this is just enough to
# make writes traceable without touching agents/graph code.
_SERVER_SESSION_ID = create_session(user_id="mcp-server")

_POWER_LOOKUP_C = {
    16: 1.0, 17: 1.2, 18: 1.4, 19: 1.6, 20: 1.8, 21: 2.0,
    22: 2.2,
    23: 2.4, 24: 2.6, 25: 2.8, 26: 3.0, 27: 3.2, 28: 3.4, 29: 3.6, 30: 4.0,
}
def _load_persisted_temp_c() -> float:
    last_reading = get_room_temperature(_THERMOSTAT_TARGET)
    if last_reading and last_reading.get("temperature") is not None:
        return float(last_reading["temperature"])
    return _DEFAULT_TEMP_C


_current_temp_c = _load_persisted_temp_c()


def _power_for(temp_c: float) -> float:
    nearest = min(_POWER_LOOKUP_C, key=lambda t: abs(t - temp_c))
    return _POWER_LOOKUP_C[nearest]


@mcp.tool()
def building_topology() -> dict:
    """Static building structure: floors and the rooms on each floor."""
    return topology_summary()


@mcp.tool()
def sensor_data(room: str | None = None) -> dict:
    """Latest sensor snapshot. Pass a known room name for a room-scoped
    reading (falls back to the building-wide default if that room has no
    readings yet); omit it for the whole-building snapshot."""
    if room and is_known_room(room):
        latest = get_latest_sensor_data(room_name=room)
        if latest:
            return {
                "room": room,
                "temp_c": latest.get("temperature"),
                "humidity": latest.get("humidity"),
                "co2_ppm": latest.get("co2"),
                "occupancy": latest.get("occupancy"),
            }
    return {"temp_c": _current_temp_c, "humidity": 55, "co2_ppm": 640, "occupancy": 18}


@mcp.tool()
def timeseries_db() -> dict:
    return {"series": "temp_c", "last_24h_avg": 23.8, "trend": "rising"}


@mcp.tool()
def weather() -> dict:
    return {"outdoor_c": 31.0, "condition": "sunny"}


@mcp.tool()
def thermal_lookup_table() -> dict:
    return {"unit_temp": "C", "unit_power": "mW", "table": {str(k): v for k, v in sorted(_POWER_LOOKUP_C.items())}}


@mcp.tool()
def current_temperature(room: str | None = None) -> dict:
    """Live setpoint + power draw. Pass a known room name for that room's
    own latest reading; omit it for the building-wide thermostat."""
    if room and is_known_room(room):
        last_reading = get_room_temperature(room)
        temp_c = float(last_reading["temperature"]) if last_reading and last_reading.get("temperature") is not None else _current_temp_c
        return {"room": room, "temp_c": temp_c, "power_mw": _power_for(temp_c)}
    return {"temp_c": _current_temp_c, "power_mw": _power_for(_current_temp_c)}


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
        "power_mw": _power_for(temp_c),
        "ack": True,
        "persisted": persisted,
    }
    if room:
        response["room"] = room
    return response


@mcp.tool()
def lux_sensor() -> dict:
    return {"lux": 210, "target": 400}


@mcp.tool()
def daylight() -> dict:
    return {"daylight_contribution": 0.35}


@mcp.tool()
def access_events() -> dict:
    return {"active_badges": 18, "unauthorized_attempts": 0}


@mcp.tool()
def fire_alarm() -> dict:
    return {"fire": False, "smoke": False, "gas_ppm": 12}


@mcp.tool()
def device_health() -> dict:
    return {"offline_devices": 0, "faults": []}


@mcp.tool()
def energy_optimizer(request: str = "") -> dict:
    best_temp_c, best_power_mw = min(_POWER_LOOKUP_C.items(), key=lambda kv: kv[1])
    current_power_mw = _power_for(_current_temp_c)
    saving_pct = 0.0
    if current_power_mw > 0:
        saving_pct = round(max(0.0, (current_power_mw - best_power_mw) / current_power_mw * 100), 1)
    return {"setpoint_c": float(best_temp_c), "expected_saving_pct": saving_pct}


@mcp.tool()
def modelica_sim(setpoint_c: float | None = None) -> dict:
    return {"predicted_comfort_pmv": 0.3, "predicted_load_kw": 37.8}


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

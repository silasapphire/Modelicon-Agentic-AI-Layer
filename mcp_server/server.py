import random

from mcp.server.fastmcp import FastMCP

from database.building.building_queries import get_room_temperature
from database.building.building_writes import apply_bms_command
from database.building.init_building_db import init_building_db
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
    16: 5.0, 17: 4.2, 18: 3.5, 19: 2.9, 20: 2.4, 21: 1.6,
    22: 1.0,
    23: 1.3, 24: 1.7, 25: 2.2, 26: 2.8, 27: 3.5, 28: 4.3, 29: 5.2, 30: 6.2,
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
def sensor_data() -> dict:
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
def current_temperature() -> dict:
    return {"temp_c": _current_temp_c, "power_mw": _power_for(_current_temp_c)}


@mcp.tool()
def set_temperature(temp_c: float = 24.3) -> dict:
    global _current_temp_c
    _current_temp_c = temp_c
    persisted = apply_bms_command(target=_THERMOSTAT_TARGET, parameter="setpoint_c", value=temp_c)
    return {
        "temp_c": _current_temp_c,
        "power_mw": _power_for(_current_temp_c),
        "ack": True,
        "persisted": persisted,
    }


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
def bms_write(target: str = "", parameter: str = "", value: float | None = None) -> dict:
    persisted = apply_bms_command(target=target, parameter=parameter, value=value)

    response = {
        "written": {"target": target, "parameter": parameter, "value": value},
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

import random

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("modelicon-building-tools")

_POWER_LOOKUP_C = {
    16: 5.0, 17: 4.2, 18: 3.5, 19: 2.9, 20: 2.4, 21: 1.6,
    22: 1.0,
    23: 1.3, 24: 1.7, 25: 2.2, 26: 2.8, 27: 3.5, 28: 4.3, 29: 5.2, 30: 6.2,
}
_current_temp_c = 24.3


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
    return {"temp_c": _current_temp_c, "power_mw": _power_for(_current_temp_c), "ack": True}


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
    return {
        "written": {"target": target, "parameter": parameter, "value": value},
        "ack": True,
        "latency_ms": random.randint(20, 90),
    }


if __name__ == "__main__":
    mcp.run()

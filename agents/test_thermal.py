from unittest.mock import patch

from agents.thermal import thermal_agent

_LOOKUP = {
    "16": 5.0, "17": 4.2, "18": 3.5, "19": 2.9, "20": 2.4, "21": 1.6,
    "22": 1.0,
    "23": 1.3, "24": 1.7, "25": 2.2, "26": 2.8, "27": 3.5, "28": 4.3, "29": 5.2, "30": 6.2,
}


def _fake_call_tool(name, **kwargs):
    if name == "current_temperature":
        return {"temp_c": 27.0, "power_mw": 3.5}
    if name == "thermal_lookup_table":
        return {"unit_temp": "C", "unit_power": "mW", "table": _LOOKUP}
    raise AssertionError(f"unexpected tool call: {name}")


def test_thermal_agent_computes_best_setpoint_from_lookup_table():
    with patch("agents.thermal.chat", return_value="Set it to 22C to save energy."):
        with patch("agents.thermal.call_tool", side_effect=_fake_call_tool):
            result = thermal_agent({"user_request": "best temperature to minimise energy?"})
    readings = result["domain_outputs"]["thermal"]["readings"]
    assert readings["best_setpoint_c"] == 22.0
    assert readings["best_setpoint_power_mw"] == 1.0
    assert readings["current_temperature"]["temp_c"] == 27.0


def test_thermal_agent_reports_current_temperature():
    with patch("agents.thermal.chat", return_value="It is currently 27C."):
        with patch("agents.thermal.call_tool", side_effect=_fake_call_tool):
            result = thermal_agent({"user_request": "what is the temperature?"})
    assert "27" in result["log"][0] or "It is currently 27C." in result["domain_outputs"]["thermal"]["recommendation"]


def test_thermal_agent_handles_empty_lookup_table():
    def empty_call_tool(name, **kwargs):
        if name == "current_temperature":
            return {"temp_c": 24.3, "power_mw": 1.7}
        if name == "thermal_lookup_table":
            return {"table": {}}
        raise AssertionError(f"unexpected tool call: {name}")

    with patch("agents.thermal.chat", return_value="ok"):
        with patch("agents.thermal.call_tool", side_effect=empty_call_tool):
            result = thermal_agent({"user_request": "status?"})
    readings = result["domain_outputs"]["thermal"]["readings"]
    assert readings["best_setpoint_c"] is None
    assert readings["best_setpoint_power_mw"] is None

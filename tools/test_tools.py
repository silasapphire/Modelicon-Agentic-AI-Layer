import pytest

from tools.mock_tools import call_tool

TOOL_NAMES = [
    "sensor_data",
    "timeseries_db",
    "weather",
    "thermal_lookup_table",
    "current_temperature",
    "set_temperature",
    "lux_sensor",
    "daylight",
    "access_events",
    "fire_alarm",
    "device_health",
    "energy_optimizer",
    "modelica_sim",
    "bms_write",
]


@pytest.fixture
def reset_temperature():
    yield
    call_tool("set_temperature", temp_c=24.3)


@pytest.mark.parametrize("name", TOOL_NAMES)
def test_every_registered_tool_returns_dict(name):
    result = call_tool(name)
    assert isinstance(result, dict)
    assert "error" not in result


def test_sensor_data_shape():
    result = call_tool("sensor_data")
    assert "temp_c" in result
    assert "humidity" in result


def test_bms_write_echoes_kwargs():
    result = call_tool("bms_write", target="hvac", parameter="setpoint_c", value=24)
    assert result["ack"] is True
    assert result["written"] == {"target": "hvac", "parameter": "setpoint_c", "value": 24}


def test_unknown_tool_returns_error():
    result = call_tool("not_a_real_tool")
    assert "error" in result
    assert "not_a_real_tool" in result["error"]


def test_unknown_tool_does_not_raise():
    for name in ["", "sensor_dat", "BMS_WRITE", "hvac"]:
        result = call_tool(name)
        assert "error" in result


def test_thermal_lookup_table_has_a_minimum_at_22c():
    result = call_tool("thermal_lookup_table")
    table = result["table"]
    assert table["22"] == 1.0
    assert min(table.values()) == 1.0


def test_set_temperature_updates_current_temperature(reset_temperature):
    call_tool("set_temperature", temp_c=19)
    result = call_tool("current_temperature")
    assert result["temp_c"] == 19
    assert result["power_mw"] == 2.9


def test_set_temperature_updates_sensor_data(reset_temperature):
    call_tool("set_temperature", temp_c=20)
    result = call_tool("sensor_data")
    assert result["temp_c"] == 20


def test_energy_optimizer_recommends_the_lookup_table_minimum(reset_temperature):
    call_tool("set_temperature", temp_c=30)
    result = call_tool("energy_optimizer", request="minimise energy use")
    assert result["setpoint_c"] == 22.0
    assert result["expected_saving_pct"] > 0

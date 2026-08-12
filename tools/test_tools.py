import pytest

from tools.mock_tools import call_tool

TOOL_NAMES = [
    "building_topology",
    "all_rooms_status",
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


def test_thermal_lookup_table_has_a_minimum_at_16c():
    result = call_tool("thermal_lookup_table")
    table = result["table"]
    assert table["16"] == 1.0
    assert min(table.values()) == 1.0


def test_set_temperature_updates_current_temperature(reset_temperature):
    call_tool("set_temperature", temp_c=19)
    result = call_tool("current_temperature")
    assert result["temp_c"] == 19
    assert result["power_mw"] == 1.6


def test_set_temperature_updates_sensor_data(reset_temperature):
    call_tool("set_temperature", temp_c=20)
    result = call_tool("sensor_data")
    assert result["temp_c"] == 20


def test_energy_optimizer_recommends_the_lookup_table_minimum(reset_temperature):
    call_tool("set_temperature", temp_c=30)
    result = call_tool("energy_optimizer", request="minimise energy use")
    assert result["setpoint_c"] == 16.0
    assert result["expected_saving_pct"] > 0


def test_building_topology_lists_3_floors_and_9_rooms():
    result = call_tool("building_topology")
    assert result["floors"] == [1, 2, 3]
    assert len(result["all_rooms"]) == 9
    assert len(result["rooms_by_floor"]["1"]) == 3  # JSON round-trip turns int keys into strings


def test_set_temperature_with_room_persists_independently_of_building_wide(reset_temperature):
    call_tool("set_temperature", temp_c=21, room="Floor 1 Room 1")
    call_tool("set_temperature", temp_c=27)  # building-wide, no room
    room_reading = call_tool("current_temperature", room="Floor 1 Room 1")
    building_reading = call_tool("current_temperature")
    assert room_reading["temp_c"] == 21
    assert building_reading["temp_c"] == 27


def test_set_temperature_ignores_unknown_room(reset_temperature):
    result = call_tool("set_temperature", temp_c=25, room="Basement")
    assert "room" in result  # echoed back even though it wasn't a known room
    building_reading = call_tool("current_temperature")
    assert building_reading["temp_c"] == 25  # fell back to the building-wide thermostat


def test_bms_write_with_room_persists_under_that_room():
    result = call_tool("bms_write", target="hvac", parameter="setpoint_c", value=23, room="Floor 2 Room 2")
    assert result["ack"] is True
    assert result["written"]["room"] == "Floor 2 Room 2"
    from database.building.building_queries import get_room_temperature
    assert get_room_temperature("Floor 2 Room 2")["temperature"] == 23


def test_all_rooms_status_covers_every_known_room():
    result = call_tool("all_rooms_status")
    from database.building.topology import ROOM_NAMES
    assert {r["room_name"] for r in result["rooms"]} == set(ROOM_NAMES)


@pytest.mark.parametrize("tool_name", ["lux_sensor", "daylight", "access_events", "fire_alarm", "device_health"])
def test_mock_domain_tools_are_room_scoped_and_distinct(tool_name):
    a = call_tool(tool_name, room="Floor 1 Room 1")
    b = call_tool(tool_name, room="Floor 2 Room 2")
    assert a["room"] == "Floor 1 Room 1"
    assert b["room"] == "Floor 2 Room 2"
    assert a != b  # distinct rooms get distinct readings, not one shared constant


@pytest.mark.parametrize("tool_name", ["lux_sensor", "daylight", "access_events", "fire_alarm", "device_health"])
def test_mock_domain_tools_return_per_room_breakdown_when_building_wide(tool_name):
    result = call_tool(tool_name)
    assert "room" not in result
    from database.building.topology import ROOM_NAMES
    assert set(result["rooms"].keys()) == set(ROOM_NAMES)


def test_mock_domain_tools_are_stable_across_repeated_calls():
    first = call_tool("lux_sensor", room="Floor 3 Room 1")
    second = call_tool("lux_sensor", room="Floor 3 Room 1")
    assert first == second


def test_energy_optimizer_is_room_scoped(reset_temperature):
    call_tool("set_temperature", temp_c=21, room="Floor 1 Room 1")
    call_tool("set_temperature", temp_c=30)  # building-wide
    room_result = call_tool("energy_optimizer", room="Floor 1 Room 1")
    building_result = call_tool("energy_optimizer")
    assert room_result["room"] == "Floor 1 Room 1"
    assert room_result["current_setpoint_c"] == 21
    assert "room" not in building_result
    assert building_result["current_setpoint_c"] == 30


def test_modelica_sim_is_room_scoped(reset_temperature):
    call_tool("set_temperature", temp_c=19, room="Floor 2 Room 3")
    result = call_tool("modelica_sim", room="Floor 2 Room 3")
    assert result["room"] == "Floor 2 Room 3"

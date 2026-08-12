from unittest.mock import patch

from agents.lighting import lighting_agent


def test_lighting_agent_passes_room_to_tools():
    with patch("agents.lighting.chat", return_value="turn on the lights"):
        with patch("agents.lighting.call_tool", return_value={"lux": 200}) as mock_call_tool:
            lighting_agent({"user_request": "lights?", "target_room": "Floor 1 Room 1"})
    calls = {c.args[0]: c.kwargs for c in mock_call_tool.call_args_list}
    assert calls["lux_sensor"] == {"room": "Floor 1 Room 1"}
    assert calls["daylight"] == {"room": "Floor 1 Room 1"}


def test_lighting_agent_omits_room_when_building_wide():
    with patch("agents.lighting.chat", return_value="all good"):
        with patch("agents.lighting.call_tool", return_value={"rooms": {}}) as mock_call_tool:
            lighting_agent({"user_request": "lights?", "target_room": "building-wide"})
    calls = {c.args[0]: c.kwargs for c in mock_call_tool.call_args_list}
    assert calls["lux_sensor"] == {}
    assert calls["daylight"] == {}

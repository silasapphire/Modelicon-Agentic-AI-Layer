from unittest.mock import patch

from agents.monitor import monitor_agent


def test_monitor_agent_passes_room_to_tools():
    with patch("agents.monitor.chat", return_value="all healthy"):
        with patch("agents.monitor.call_tool", return_value={"offline_devices": 0}) as mock_call_tool:
            monitor_agent({"user_request": "any faults?", "target_room": "Floor 3 Room 2"})
    mock_call_tool.assert_called_once_with("device_health", room="Floor 3 Room 2")


def test_monitor_agent_omits_room_when_building_wide():
    with patch("agents.monitor.chat", return_value="all healthy"):
        with patch("agents.monitor.call_tool", return_value={"rooms": {}}) as mock_call_tool:
            monitor_agent({"user_request": "any faults anywhere?", "target_room": "building-wide"})
    mock_call_tool.assert_called_once_with("device_health")

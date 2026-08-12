from unittest.mock import patch

from agents.access import access_agent


def test_access_agent_passes_room_to_tools():
    with patch("agents.access.chat", return_value="all clear"):
        with patch("agents.access.call_tool", return_value={"active_badges": 3}) as mock_call_tool:
            access_agent({"user_request": "who's in the room?", "target_room": "Floor 2 Room 1"})
    mock_call_tool.assert_called_once_with("access_events", room="Floor 2 Room 1")


def test_access_agent_omits_room_when_building_wide():
    with patch("agents.access.chat", return_value="all clear"):
        with patch("agents.access.call_tool", return_value={"rooms": {}}) as mock_call_tool:
            access_agent({"user_request": "any unauthorized attempts?", "target_room": "building-wide"})
    mock_call_tool.assert_called_once_with("access_events")

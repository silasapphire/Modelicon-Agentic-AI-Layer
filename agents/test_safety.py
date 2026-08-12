from unittest.mock import patch

from agents.safety import safety_agent


def test_safety_flags_emergency_on_fire():
    with patch("agents.safety.chat", return_value="evacuate immediately"):
        with patch(
            "agents.safety.call_tool",
            return_value={"fire": True, "smoke": False, "gas_ppm": 12},
        ):
            result = safety_agent({"user_request": "status?"})
    assert result["emergency"] is True
    assert result["domain_outputs"]["safety"]["emergency"] is True


def test_safety_flags_emergency_on_high_gas_ppm():
    with patch("agents.safety.chat", return_value="ventilate"):
        with patch(
            "agents.safety.call_tool",
            return_value={"fire": False, "smoke": False, "gas_ppm": 500},
        ):
            result = safety_agent({"user_request": "status?"})
    assert result["emergency"] is True


def test_safety_no_emergency_when_readings_normal():
    with patch("agents.safety.chat", return_value="all clear"):
        with patch(
            "agents.safety.call_tool",
            return_value={"fire": False, "smoke": False, "gas_ppm": 12},
        ):
            result = safety_agent({"user_request": "status?"})
    assert "emergency" not in result
    assert result["domain_outputs"]["safety"]["emergency"] is False


def test_safety_agent_passes_room_to_tools():
    with patch("agents.safety.chat", return_value="all clear"):
        with patch(
            "agents.safety.call_tool",
            return_value={"fire": False, "smoke": False, "gas_ppm": 12},
        ) as mock_call_tool:
            safety_agent({"user_request": "any smoke?", "target_room": "Floor 1 Room 3"})
    mock_call_tool.assert_called_once_with("fire_alarm", room="Floor 1 Room 3")


def test_safety_agent_omits_room_when_building_wide():
    with patch("agents.safety.chat", return_value="all clear"):
        with patch(
            "agents.safety.call_tool",
            return_value={"fire": False, "smoke": False, "gas_ppm": 12},
        ) as mock_call_tool:
            safety_agent({"user_request": "any smoke anywhere?", "target_room": "building-wide"})
    mock_call_tool.assert_called_once_with("fire_alarm")

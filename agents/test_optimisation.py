from unittest.mock import patch

from agents.optimisation import optimization_agent


def test_optimization_agent_passes_room_to_tool():
    with patch("agents.optimisation.call_tool", return_value={"setpoint_c": 16.0, "expected_saving_pct": 40.0}) as mock_call_tool:
        optimization_agent({"user_request": "save energy", "target_room": "Floor 1 Room 2"})
    mock_call_tool.assert_called_once_with(
        "energy_optimizer", request="save energy", room="Floor 1 Room 2"
    )


def test_optimization_agent_passes_none_room_when_building_wide():
    with patch("agents.optimisation.call_tool", return_value={"setpoint_c": 16.0, "expected_saving_pct": 40.0}) as mock_call_tool:
        optimization_agent({"user_request": "save energy building-wide", "target_room": "building-wide"})
    mock_call_tool.assert_called_once_with(
        "energy_optimizer", request="save energy building-wide", room=None
    )

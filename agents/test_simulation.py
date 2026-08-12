from unittest.mock import patch

from agents.simulation import simulation_agent


def test_simulation_agent_passes_room_to_tool():
    with patch("agents.simulation.call_tool", return_value={"predicted_comfort_pmv": 0.1, "predicted_load_kw": 1.2}) as mock_call_tool:
        simulation_agent(
            {
                "user_request": "simulate the setpoint change",
                "target_room": "Floor 3 Room 1",
                "optimization_result": {"setpoint_c": 21.0},
            }
        )
    mock_call_tool.assert_called_once_with("modelica_sim", setpoint_c=21.0, room="Floor 3 Room 1")


def test_simulation_agent_passes_none_room_when_building_wide():
    with patch("agents.simulation.call_tool", return_value={"predicted_comfort_pmv": 0.1, "predicted_load_kw": 1.2}) as mock_call_tool:
        simulation_agent(
            {
                "user_request": "simulate building-wide",
                "target_room": "building-wide",
                "optimization_result": {"setpoint_c": 21.0},
            }
        )
    mock_call_tool.assert_called_once_with("modelica_sim", setpoint_c=21.0, room=None)

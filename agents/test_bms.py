from unittest.mock import patch

from agents.bms import bms_agent, bms_read_agent
from tools.mock_tools import call_tool


def test_bms_agent_skips_execution_when_rejected():
    state = {"human_decision": "rejected", "coordinated_plan": {"actions": [{"target": "hvac"}]}}
    result = bms_agent(state)
    assert result["execution_result"]["executed"] is False


def test_bms_agent_executes_all_actions():
    state = {
        "coordinated_plan": {
            "actions": [
                {"target": "hvac", "parameter": "setpoint_c", "value": 22},
                {"target": "lighting", "parameter": "lux", "value": 400},
            ]
        }
    }
    result = bms_agent(state)
    assert result["execution_result"]["executed"] is True
    assert len(result["execution_result"]["acks"]) == 2
    call_tool("set_temperature", temp_c=24.3)


def test_bms_agent_persists_setpoint_change_via_set_temperature():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "hvac", "parameter": "setpoint_c", "value": 19}]
        }
    }
    with patch("agents.bms.call_tool") as mock_call_tool:
        mock_call_tool.return_value = {"ack": True}
        bms_agent(state)
    called_names = [c.args[0] for c in mock_call_tool.call_args_list]
    assert called_names == ["bms_write", "set_temperature"]
    set_temp_call = mock_call_tool.call_args_list[1]
    assert set_temp_call.kwargs == {"temp_c": 19}


def test_bms_agent_does_not_set_temperature_for_non_thermal_actions():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "lighting", "parameter": "lux", "value": 400}]
        }
    }
    with patch("agents.bms.call_tool") as mock_call_tool:
        mock_call_tool.return_value = {"ack": True}
        bms_agent(state)
    called_names = [c.args[0] for c in mock_call_tool.call_args_list]
    assert called_names == ["bms_write"]


def test_bms_agent_handles_no_actions():
    result = bms_agent({"coordinated_plan": {"actions": []}})
    assert result["execution_result"]["acks"] == []


def test_bms_read_agent_writes_domain_output():
    with patch("agents.bms.chat", return_value="all systems nominal"):
        result = bms_read_agent({"user_request": "status check"})
    assert "bms" in result["domain_outputs"]
    assert result["domain_outputs"]["bms"]["recommendation"] == "all systems nominal"

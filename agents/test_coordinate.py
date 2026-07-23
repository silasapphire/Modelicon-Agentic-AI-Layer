from unittest.mock import patch

from agents.coordinate import coordination_agent


def test_coordination_builds_plan_and_summary():
    plan = {
        "actions": [{"target": "hvac", "parameter": "setpoint_c", "value": 24}],
        "risk": "low",
    }
    with patch("agents.coordinate.chat_json", return_value=plan):
        with patch("agents.coordinate.chat", return_value="Raise the setpoint to 24C."):
            result = coordination_agent({"user_request": "warm the east zone"})
    assert result["coordinated_plan"]["actions"] == plan["actions"]
    assert result["coordinated_plan"]["summary"] == "Raise the setpoint to 24C."
    assert result["final_response"] == "Raise the setpoint to 24C."


def test_coordination_falls_back_to_no_actions_on_bad_json():
    with patch("agents.coordinate.chat_json", return_value={"actions": [], "risk": "low"}):
        with patch("agents.coordinate.chat", return_value="No action needed."):
            result = coordination_agent({"user_request": "status?"})
    assert result["coordinated_plan"]["actions"] == []
    assert result["log"][0].startswith("coordinate: 0 action(s)")


def test_coordination_passes_intent_to_synthesizer():
    with patch("agents.coordinate.chat_json", return_value={"actions": [], "risk": "low"}) as mock_chat_json:
        with patch("agents.coordinate.chat", return_value="Here is the status."):
            coordination_agent({"user_request": "status?", "intent": "report"})
    _, kwargs = mock_chat_json.call_args
    assert "'intent': 'report'" in kwargs["user"]

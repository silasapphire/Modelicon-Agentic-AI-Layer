from unittest.mock import patch

from agents.analysis import analysis_agent


def test_analysis_reports_needs_optimization_true():
    with patch("agents.analysis.chat", return_value="load is trending up"):
        with patch("agents.analysis.chat_json", return_value={"needs_optimization": True}):
            result = analysis_agent({"user_request": "reduce energy use", "domain_outputs": {}})
    assert result["needs_optimization"] is True
    assert result["analysis_result"]["findings"] == "load is trending up"


def test_analysis_defaults_to_false_on_bad_json():
    with patch("agents.analysis.chat", return_value="all nominal"):
        with patch("agents.analysis.chat_json", return_value={}):
            result = analysis_agent({"user_request": "status?", "domain_outputs": {}})
    assert result["needs_optimization"] is False


def test_analysis_passes_retrieved_data_to_findings_call():
    state = {
        "user_request": "what is the temperature?",
        "domain_outputs": {},
        "retrieved_data": {"sensors": {"temp_c": 24.3}},
    }
    with patch("agents.analysis.chat", return_value="24.3C") as mock_chat:
        with patch("agents.analysis.chat_json", return_value={"needs_optimization": False}):
            analysis_agent(state)
    _, kwargs = mock_chat.call_args
    assert "24.3" in kwargs["user"]

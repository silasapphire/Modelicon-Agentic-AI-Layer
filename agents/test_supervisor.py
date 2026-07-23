from unittest.mock import patch

from agents.supervisor import supervisor_agent, DOMAINS


def test_supervisor_uses_fallback_on_bad_json():
    state = {"user_request": "diagnose the east zone", "revision_count": 0}
    with patch("agents.supervisor.chat_json", return_value={}):
        result = supervisor_agent(state)
    assert result["intent"] == "diagnose"
    assert set(result["active_domains"]).issubset(set(DOMAINS))
    assert result["emergency"] is False


def test_supervisor_forces_safety_only_on_emergency():
    state = {"user_request": "there is smoke in the server room", "revision_count": 0}
    plan = {
        "intent": "emergency",
        "data_required": True,
        "active_domains": ["thermal", "safety"],
        "emergency": True,
    }
    with patch("agents.supervisor.chat_json", return_value=plan):
        result = supervisor_agent(state)
    assert result["emergency"] is True
    assert result["active_domains"] == ["safety"]


def test_supervisor_filters_unknown_domains():
    state = {"user_request": "check everything", "revision_count": 0}
    plan = {
        "intent": "diagnose",
        "data_required": False,
        "active_domains": ["thermal", "not_a_domain"],
        "emergency": False,
    }
    with patch("agents.supervisor.chat_json", return_value=plan):
        result = supervisor_agent(state)
    assert result["active_domains"] == ["thermal"]
    assert result["data_required"] is False


def test_supervisor_defaults_to_all_domains_when_none_valid():
    state = {"user_request": "??", "revision_count": 0}
    plan = {
        "intent": "diagnose",
        "data_required": True,
        "active_domains": ["not_a_domain"],
        "emergency": False,
    }
    with patch("agents.supervisor.chat_json", return_value=plan):
        result = supervisor_agent(state)
    assert set(result["active_domains"]) == set(DOMAINS)


def test_supervisor_preserves_revision_count():
    state = {"user_request": "optimise the east zone", "revision_count": 2}
    with patch("agents.supervisor.chat_json", return_value={}):
        result = supervisor_agent(state)
    assert result["revision_count"] == 2

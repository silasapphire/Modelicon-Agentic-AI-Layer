from unittest.mock import patch

from agents.guardrail import guardrail_agent, human_review, MAX_REVISIONS


def test_pass_when_within_limits():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "hvac", "parameter": "setpoint_c", "value": 22}],
            "risk": "low",
        },
        "revision_count": 0,
    }
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "pass"
    assert result["revision_count"] == 0


def test_reject_when_value_outside_limits():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "hvac", "parameter": "setpoint_c", "value": 45}],
            "risk": "low",
        },
        "revision_count": 0,
    }
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "reject"
    assert "outside" in result["guardrail_feedback"]
    assert result["revision_count"] == 1


def test_reject_stops_after_max_revisions_and_escalates():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "hvac", "parameter": "setpoint_c", "value": 45}],
            "risk": "low",
        },
        "revision_count": MAX_REVISIONS,
    }
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "approval_needed"


def test_unknown_target_is_a_violation():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "elevator", "parameter": "speed", "value": 1}],
            "risk": "low",
        },
        "revision_count": 0,
    }
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "reject"
    assert "unknown target" in result["guardrail_feedback"]


def test_high_risk_needs_approval_even_without_violations():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "hvac", "parameter": "setpoint_c", "value": 22}],
            "risk": "high",
        },
        "revision_count": 0,
    }
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "approval_needed"


def test_emergency_needs_approval_even_with_no_actions():
    state = {"coordinated_plan": {"actions": [], "risk": "low"}, "emergency": True, "revision_count": 0}
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "approval_needed"


def test_empty_plan_passes():
    state = {"coordinated_plan": {}, "revision_count": 0}
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "pass"


def test_optimize_intent_forces_approval_even_at_low_risk():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "hvac", "parameter": "setpoint_c", "value": 22}],
            "risk": "low",
        },
        "intent": "optimize",
        "revision_count": 0,
    }
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "approval_needed"
    assert "approval" in result["guardrail_feedback"]


def test_optimize_intent_without_actions_passes():
    state = {
        "coordinated_plan": {"actions": [], "risk": "low"},
        "intent": "optimize",
        "revision_count": 0,
    }
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "pass"


def test_control_intent_within_limits_passes_without_approval():
    state = {
        "coordinated_plan": {
            "actions": [{"target": "hvac", "parameter": "setpoint_c", "value": 22}],
            "risk": "low",
        },
        "intent": "control",
        "revision_count": 0,
    }
    result = guardrail_agent(state)
    assert result["guardrail_status"] == "pass"


def test_human_review_approved():
    plan = {"summary": "raise setpoint", "actions": []}
    state = {"coordinated_plan": plan, "guardrail_feedback": ""}
    with patch("agents.guardrail.interrupt", return_value="yes"):
        result = human_review(state)
    assert result["human_decision"] == "approved"


def test_human_review_rejected():
    plan = {"summary": "raise setpoint", "actions": []}
    state = {"coordinated_plan": plan, "guardrail_feedback": ""}
    with patch("agents.guardrail.interrupt", return_value="no"):
        result = human_review(state)
    assert result["human_decision"] == "rejected"

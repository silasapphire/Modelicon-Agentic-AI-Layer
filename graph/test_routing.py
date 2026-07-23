from langgraph.types import Send

from graph.routing import (
    DOMAINS,
    fan_out,
    route_after_supervisor,
    route_after_domains,
    route_after_analysis,
    route_after_guardrail,
)


def test_fan_out_dispatches_active_domains():
    state = {"active_domains": ["thermal", "safety"]}
    sends = fan_out(state)
    assert all(isinstance(s, Send) for s in sends)
    assert [s.node for s in sends] == ["thermal", "safety"]


def test_fan_out_defaults_to_all_domains():
    sends = fan_out({})
    assert [s.node for s in sends] == DOMAINS


def test_route_after_supervisor_emergency_bypasses_query():
    state = {"emergency": True, "data_required": True, "active_domains": ["safety"]}
    result = route_after_supervisor(state)
    assert [s.node for s in result] == ["safety"]


def test_route_after_supervisor_goes_to_query_when_data_required():
    state = {"emergency": False, "data_required": True}
    assert route_after_supervisor(state) == "query"


def test_route_after_supervisor_fans_out_when_no_data_required():
    state = {"emergency": False, "data_required": False, "active_domains": ["thermal"]}
    result = route_after_supervisor(state)
    assert [s.node for s in result] == ["thermal"]


def test_route_after_domains_emergency_skips_analysis():
    assert route_after_domains({"emergency": True}) == "coordination"


def test_route_after_domains_normal_goes_to_analysis():
    assert route_after_domains({"emergency": False}) == "analysis"


def test_route_after_analysis_needs_optimization():
    assert route_after_analysis({"needs_optimization": True}) == "optimization"


def test_route_after_analysis_skips_optimization():
    assert route_after_analysis({"needs_optimization": False}) == "coordination"


def test_route_after_guardrail_reject_loops_back():
    state = {"guardrail_status": "reject", "active_domains": ["thermal"]}
    result = route_after_guardrail(state)
    assert [s.node for s in result] == ["thermal"]


def test_route_after_guardrail_approval_needed():
    assert route_after_guardrail({"guardrail_status": "approval_needed"}) == "human_review"


def test_route_after_guardrail_pass_goes_to_bms():
    assert route_after_guardrail({"guardrail_status": "pass"}) == "bms_agent"

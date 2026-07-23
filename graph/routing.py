from langgraph.types import Send

DOMAINS = ["thermal", "lighting", "access", "safety", "monitor", "bms"]


def fan_out(state):
    return [Send(name, state) for name in state.get("active_domains", DOMAINS)]


def route_after_supervisor(state):
    if state.get("emergency"):
        return fan_out(state)
    if state.get("data_required"):
        return "query"
    return fan_out(state)


def route_after_domains(state):
    return "coordination" if state.get("emergency") else "analysis"


def route_after_analysis(state):
    return "optimization" if state.get("needs_optimization") else "coordination"


def route_after_guardrail(state):
    status = state.get("guardrail_status")
    if status == "reject":
        return fan_out(state)
    if status == "approval_needed":
        return "human_review"
    return "bms_agent"

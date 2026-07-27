from langgraph.types import interrupt

from database.building.topology import ROOM_NAMES, BUILDING_WIDE

LIMITS = {
    "temperature": (16.0, 30.0),
    "setpoint_c": (16.0, 30.0),
    "lux": (0, 1000),
    "vfd_pct": (0, 100),
}
KNOWN_TARGETS = {"hvac", "lighting", "access", "ventilation", "bms"}
KNOWN_ROOMS = set(ROOM_NAMES) | {BUILDING_WIDE}
MAX_REVISIONS = 2


def guardrail_agent(state):
    plan = state.get("coordinated_plan", {})
    actions = plan.get("actions", [])
    revisions = state.get("revision_count", 0)
    violations = []

    for a in actions:
        target = str(a.get("target", "")).lower()
        param = str(a.get("parameter", "")).lower()
        value = a.get("value")
        room = a.get("room")

        if target and target not in KNOWN_TARGETS:
            violations.append(f"unknown target '{target}'")

        if room and room not in KNOWN_ROOMS:
            violations.append(f"unknown room '{room}'")

        if param in LIMITS and isinstance(value, (int, float)):
            lo, hi = LIMITS[param]
            if not (lo <= value <= hi):
                violations.append(f"{param}={value} outside [{lo},{hi}]")

    if violations and revisions < MAX_REVISIONS:
        status, feedback = "reject", "; ".join(violations)
    elif violations:
        status, feedback = "approval_needed", "; ".join(violations)
    elif state.get("emergency"):
        status, feedback = "approval_needed", "emergency action"
    elif plan.get("risk") == "high":
        status, feedback = "approval_needed", "high-risk action"
    elif state.get("intent") == "optimize" and actions:
        status, feedback = "approval_needed", "optimization recommendation requires operator approval"
    else:
        status, feedback = "pass", "within all limits"

    return {
        "guardrail_status": status,
        "guardrail_feedback": feedback,
        "revision_count": revisions + (1 if status == "reject" else 0),
        "log": [f"guardrail: {status} ({feedback})"],
    }


def human_review(state):
    plan = state.get("coordinated_plan", {})
    decision = interrupt(
        {
            "question": "Approve this control action?",
            "summary": plan.get("summary", ""),
            "actions": plan.get("actions", []),
            "feedback": state.get("guardrail_feedback", ""),
        }
    )
    approved = str(decision).lower() in ("approve", "approved", "yes", "y", "true")
    return {
        "human_decision": "approved" if approved else "rejected",
        "log": [f"human: {'approved' if approved else 'rejected'}"],
    }

from llm.ollama_client import chat_json
from database.building.topology import BUILDING_WIDE

DOMAINS = ["thermal", "lighting", "access", "safety", "monitor", "bms"]

_SYSTEM = (
    "You are the supervisor of a smart-building control system. "
    "The building is a single HVAC zone -- there is only one room, so "
    "every request applies to it; no per-room or per-floor scoping is "
    "needed. Classify the user request and plan the workflow.\n"
    "Fields to return:\n"
    ' intent: one of "diagnose", "optimize", "control", "report", "emergency"\n'
    " data_required: true if live/historical building data is needed\n"
    f" active_domains: subset of {DOMAINS} relevant to the request\n"
    " emergency: true only for fire/smoke/gas/security threats"
)


def supervisor_agent(state):
    req = state["user_request"]
    fallback = {
        "intent": "diagnose",
        "data_required": True,
        "active_domains": DOMAINS,
        "emergency": False,
    }

    plan = chat_json(_SYSTEM, req, fallback)

    domains = [d for d in plan.get("active_domains", DOMAINS) if d in DOMAINS]
    if not domains:
        domains = DOMAINS

    emergency = bool(plan.get("emergency", False))
    if emergency:
        domains = ["safety"]

    return {
        "intent": plan.get("intent", "diagnose"),
        "data_required": bool(plan.get("data_required", True)),
        "active_domains": domains,
        "emergency": emergency,
        # Single-zone building: there is nothing to disambiguate, so
        # target_room is always the whole (one-room) building. Kept in
        # state because guardrail/coordinate still key actions off it.
        "target_room": BUILDING_WIDE,
        "revision_count": state.get("revision_count", 0),
        "log": [
            f"supervisor: intent={plan.get('intent')} "
            f"data_required={plan.get('data_required')} "
            f"domains={domains} emergency={emergency}"
        ],
    }

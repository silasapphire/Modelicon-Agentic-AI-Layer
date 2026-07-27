from llm.groq_client import chat_json
from database.building.topology import ROOM_NAMES, BUILDING_WIDE

DOMAINS = ["thermal", "lighting", "access", "safety", "monitor", "bms"]

_SYSTEM = (
    "You are the supervisor of a smart-building control system. "
    "The building has 3 floors, 3 rooms each. The known rooms are: "
    f"{list(ROOM_NAMES)}.\n"
    "Classify the user request and plan the workflow.\n"
    "Fields to return:\n"
    ' intent: one of "diagnose", "optimize", "control", "report", "emergency"\n'
    " data_required: true if live/historical building data is needed\n"
    f" active_domains: subset of {DOMAINS} relevant to the request\n"
    " emergency: true only for fire/smoke/gas/security threats\n"
    " target_room: the exact room name from the list above if the request "
    f'names or clearly implies one specific room, otherwise "{BUILDING_WIDE}"'
)


def supervisor_agent(state):
    req = state["user_request"]
    fallback = {
        "intent": "diagnose",
        "data_required": True,
        "active_domains": DOMAINS,
        "emergency": False,
        "target_room": BUILDING_WIDE,
    }

    plan = chat_json(_SYSTEM, req, fallback)

    domains = [d for d in plan.get("active_domains", DOMAINS) if d in DOMAINS]
    if not domains:
        domains = DOMAINS

    emergency = bool(plan.get("emergency", False))
    if emergency:
        domains = ["safety"]

    target_room = plan.get("target_room", BUILDING_WIDE)
    if target_room not in ROOM_NAMES:
        target_room = BUILDING_WIDE

    return {
        "intent": plan.get("intent", "diagnose"),
        "data_required": bool(plan.get("data_required", True)),
        "active_domains": domains,
        "emergency": emergency,
        "target_room": target_room,
        "revision_count": state.get("revision_count", 0),
        "log": [
            f"supervisor: intent={plan.get('intent')} "
            f"data_required={plan.get('data_required')} "
            f"domains={domains} emergency={emergency} room={target_room}"
        ],
    }

"""
Supervisory Agent - the central orchestrator.

Classifies the user request, decides whether data retrieval is needed,
and picks which domain agents should run.

It writes routing hints into the shared BuildingState.
The LangGraph routing functions use these hints to decide where the
workflow goes next.
"""

from llm.groq_client import chat_json

# List of valid domain agents
DOMAINS = [
    "thermal",
    "lighting",
    "access",
    "safety",
    "monitor",
    "bms",
]

# System prompt given to the LLM
_SYSTEM = (
    "You are the supervisor of a smart-building control system.\n"
    "Your job is to understand the user's request and decide how the "
    "multi-agent workflow should proceed.\n\n"

    "Return ONLY a JSON object with these fields:\n"

    'intent: one of ["diagnose", "optimize", "control", "report", "emergency"]\n'
    "data_required: true if live or historical building data is required\n"
    f"active_domains: subset of {DOMAINS}\n"
    "emergency: true ONLY for fire, smoke, gas leak, or major security threats"
)


def supervisor_agent(state):
    """
    Reads:
        state["user_request"]

    Writes:
        intent
        data_required
        active_domains
        emergency
        revision_count
        log
    """

    # User's natural language request
    req = state["user_request"]

    # Safe defaults if the LLM returns invalid JSON
    fallback = {
        "intent": "diagnose",
        "data_required": True,
        "active_domains": DOMAINS,
        "emergency": False,
    }

    # Ask the LLM to classify the request
    plan = chat_json(
        system=_SYSTEM,
        user=req,
        fallback=fallback,
    )

    # Keep only valid domain names
    domains = [
        d
        for d in plan.get("active_domains", DOMAINS)
        if d in DOMAINS
    ]

    # If no valid domains remain, run all domains
    if not domains:
        domains = DOMAINS

    # Emergency flag
    emergency = bool(plan.get("emergency", False))

    # During emergencies, always force Safety Agent only
    if emergency:
        domains = ["safety"]

    # Return updates to BuildingState
    return {
        "intent": plan.get("intent", "diagnose"),

        "data_required": bool(
            plan.get("data_required", True)
        ),

        "active_domains": domains,

        "emergency": emergency,

        # Preserve current revision count
        "revision_count": state.get(
            "revision_count",
            0,
        ),

        # Append one log entry
        "log": [
            f"supervisor: "
            f"intent={plan.get('intent')} "
            f"data_required={plan.get('data_required')} "
            f"domains={domains} "
            f"emergency={emergency}"
        ],
    }
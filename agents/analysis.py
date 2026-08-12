from llm.ollama_client import chat, chat_json


def analysis_agent(state):
    outputs = state.get("domain_outputs", {})
    retrieved = state.get("retrieved_data", {})

    findings = chat(
        system=(
            "You are the analysis agent. Summarise the key findings, "
            "anomalies and likely root cause from the domain outputs and "
            "retrieved sensor data in 2-3 sentences. Cite specific numbers "
            "when they are available instead of speaking in generalities. "
            "If target_room is a specific room, focus on that room; if "
            "it is building-wide, use the all_rooms breakdown in retrieved "
            "data to compare rooms when the request calls for it (e.g. "
            "'which room ...')."
        ),
        user=(
            f"User request: {state['user_request']}\n"
            f"target_room: {state.get('target_room')}\n"
            f"Retrieved data: {retrieved}\n"
            f"Domain outputs: {outputs}"
        ),
    )

    decision = chat_json(
        system=(
            "Decide if this request needs numerical optimization and "
            "simulation before acting. Return true ONLY if the user "
            "explicitly asks to optimize, minimise/reduce energy or power "
            "usage, or find the most efficient setpoint. A plain status, "
            "current-value, or diagnostic question (e.g. 'what is the "
            "temperature', 'is everything ok', 'which room is hottest') "
            "must return false, even if the findings happen to mention "
            'efficiency or savings. Return {"needs_optimization": bool}.'
        ),
        user=f"Request: {state['user_request']}\nFindings: {findings}",
        fallback={"needs_optimization": False},
    )

    return {
        "analysis_result": {"findings": findings},
        "needs_optimization": bool(decision.get("needs_optimization", False)),
        "log": [f"analysis: needs_optimization={decision.get('needs_optimization')}"],
    }

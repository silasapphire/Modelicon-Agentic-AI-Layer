from llm.ollama_client import chat, chat_json


def analysis_agent(state):
    outputs = state.get("domain_outputs", {})
    retrieved = state.get("retrieved_data", {})
    request = state["user_request"]

    findings = chat(
        system=(
            "You are the analysis agent for a single-zone building (one "
            "room). Summarise the key findings, anomalies and likely "
            "root cause from the domain outputs and retrieved sensor "
            "data in 2-3 sentences. Cite specific numbers when they are "
            "available instead of speaking in generalities. Never "
            "calculate, estimate, or invent a number yourself -- every "
            "number you state must come verbatim from retrieved data or "
            "domain outputs."
        ),
        user=(
            f"User request: {request}\n"
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
            "temperature', 'is everything ok') must return false, even "
            "if the findings happen to mention efficiency or savings. "
            'Return {"needs_optimization": bool}.'
        ),
        user=f"Request: {request}\nFindings: {findings}",
        fallback={"needs_optimization": False},
    )

    return {
        "analysis_result": {"findings": findings},
        "needs_optimization": bool(decision.get("needs_optimization", False)),
        "log": [f"analysis: needs_optimization={decision.get('needs_optimization')}"],
    }

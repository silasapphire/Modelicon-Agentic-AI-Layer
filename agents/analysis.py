from llm.groq_client import chat, chat_json


def analysis_agent(state):
    outputs = state.get("domain_outputs", {})
    retrieved = state.get("retrieved_data", {})

    findings = chat(
        system=(
            "You are the analysis agent. Summarise the key findings, "
            "anomalies and likely root cause from the domain outputs and "
            "retrieved sensor data in 2-3 sentences. Cite specific numbers "
            "when they are available instead of speaking in generalities."
        ),
        user=(
            f"User request: {state['user_request']}\n"
            f"Retrieved data: {retrieved}\n"
            f"Domain outputs: {outputs}"
        ),
    )

    decision = chat_json(
        system=(
            "Decide if this request needs numerical optimization and "
            'simulation before acting. Return {"needs_optimization": bool}.'
        ),
        user=f"Request: {state['user_request']}\nFindings: {findings}",
        fallback={"needs_optimization": False},
    )

    return {
        "analysis_result": {"findings": findings},
        "needs_optimization": bool(decision.get("needs_optimization", False)),
        "log": [f"analysis: needs_optimization={decision.get('needs_optimization')}"],
    }

from llm.groq_client import chat, chat_json
from database.building.topology import BUILDING_WIDE


def coordination_agent(state):
    target_room = state.get("target_room", BUILDING_WIDE)
    context = {
        "request": state["user_request"],
        "intent": state.get("intent"),
        "target_room": target_room,
        "retrieved_data": state.get("retrieved_data", {}),
        "domains": state.get("domain_outputs", {}),
        "analysis": state.get("analysis_result", {}),
        "optimization": state.get("optimization_result", {}),
        "simulation": state.get("simulation_result", {}),
    }

    plan = chat_json(
        system=(
            "You are the synthesizer. Merge all agent outputs into ONE "
            "plan. Resolve conflicts. Only propose actions if the user is "
            "explicitly asking for a change, control action, or optimization "
            "(intent in control/optimize/emergency, or an optimization result "
            "is present). For purely informational requests (status checks, "
            "diagnostics, reports, questions) return an empty actions list "
            "-- the summary alone answers the user. Every action's target "
            "MUST be one of: hvac, lighting, access, ventilation, bms -- "
            "never a sensor or tool name. A temperature setpoint change "
            "always uses target 'hvac' and parameter 'setpoint_c'. Every "
            "action MUST also include 'room', set to context.target_room "
            f'verbatim (use "{BUILDING_WIDE}" only when target_room is '
            f'"{BUILDING_WIDE}"). Return '
            '{"actions": [{"target": str, "room": str, "parameter": str, "value": number}], '
            '"risk": "low"|"medium"|"high"}.'
        ),
        user=f"{context}",
        fallback={"actions": [], "risk": "low"},
    )

    summary = chat(
        system=(
            "Write a 2-3 sentence plain-English response to the user's "
            "original request, using the domain findings and the proposed "
            "plan below. If the plan has no actions, answer the request "
            "directly using the findings -- do not mention a 'plan' or "
            "that one is missing. If it has actions, summarise what will "
            "be done and why."
        ),
        user=f"Request: {context['request']}\nFindings: {context}\nPlan: {plan}",
    )
    plan["summary"] = summary

    return {
        "coordinated_plan": plan,
        "final_response": summary,
        "log": [
            f"coordinate: {len(plan.get('actions', []))} action(s), "
            f"risk={plan.get('risk')}"
        ],
    }

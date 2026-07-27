from llm.groq_client import chat
from tools.mock_tools import call_tool


def bms_read_agent(state):
    readings = {"device_health": call_tool("device_health")}
    recommendation = chat(
        system=(
            "You are the BMS agent, reporting current BMS equipment "
            "status (read-only). Given the readings and the user "
            "request, give a short status summary (1-2 sentences)."
        ),
        user=f"User request: {state['user_request']}\nReadings: {readings}",
    )
    return {
        "domain_outputs": {"bms": {"readings": readings, "recommendation": recommendation}},
        "log": [f"bms(read): {recommendation[:60]}"],
    }


def bms_agent(state):
    if state.get("human_decision") == "rejected":
        return {
            "execution_result": {"executed": False, "reason": "rejected by operator"},
            "log": ["bms: skipped (operator rejected)"],
        }

    results = []
    for a in state.get("coordinated_plan", {}).get("actions", []):
        results.append(call_tool("bms_write", **a))
        value = a.get("value")
        if str(a.get("parameter", "")).lower() == "setpoint_c" and isinstance(value, (int, float)):
            room = a.get("room")
            if room:
                call_tool("set_temperature", temp_c=value, room=room)
            else:
                call_tool("set_temperature", temp_c=value)

    return {
        "execution_result": {"executed": True, "acks": results},
        "log": [f"bms: executed {len(results)} action(s)"],
    }

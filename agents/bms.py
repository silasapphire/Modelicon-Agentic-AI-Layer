from llm.ollama_client import chat
from tools.mock_tools import call_tool
from database.building.topology import BUILDING_WIDE


def bms_read_agent(state):
    room = state.get("target_room")
    room = room if room and room != BUILDING_WIDE else None

    readings = {
        "room": room or BUILDING_WIDE,
        "device_health": call_tool("device_health", room=room) if room else call_tool("device_health"),
    }
    recommendation = chat(
        system=(
            "You are the BMS agent, reporting current BMS equipment "
            "status (read-only). Given the readings and the user "
            "request, give a short status summary (1-2 sentences). Name "
            "the room if one is set in readings; if readings contain a "
            "per-room breakdown instead, use it to identify which room "
            "has an issue."
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

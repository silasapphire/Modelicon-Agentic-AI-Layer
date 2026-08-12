from llm.ollama_client import chat
from tools.mock_tools import call_tool
from database.building.topology import BUILDING_WIDE


def monitor_agent(state):
    room = state.get("target_room")
    room = room if room and room != BUILDING_WIDE else None

    readings = {
        "room": room or BUILDING_WIDE,
        "device_health": call_tool("device_health", room=room) if room else call_tool("device_health"),
    }

    recommendation = chat(
        system=(
            "You are the monitor agent, expert in equipment health and "
            "device fault detection. Given the readings and the user "
            "request, give a short recommendation (1-2 sentences) and any "
            "proposed action. Name the room if one is set in readings; if "
            "readings contain a per-room breakdown instead, use it to "
            "identify which room has an issue."
        ),
        user=f"User request: {state['user_request']}\nReadings: {readings}",
    )

    return {
        "domain_outputs": {
            "monitor": {
                "readings": readings,
                "recommendation": recommendation,
            }
        },
        "log": [f"monitor: {recommendation[:60]}"],
    }
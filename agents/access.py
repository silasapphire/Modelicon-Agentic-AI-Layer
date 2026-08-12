from llm.ollama_client import chat
from tools.mock_tools import call_tool
from database.building.topology import BUILDING_WIDE


def access_agent(state):
    room = state.get("target_room")
    room = room if room and room != BUILDING_WIDE else None

    readings = {
        "room": room or BUILDING_WIDE,
        "access_events": call_tool("access_events", room=room) if room else call_tool("access_events"),
    }

    recommendation = chat(
        system=(
            "You are the access agent, expert in access control, "
            "occupancy and door management. Given the readings and the "
            "user request, give a short recommendation (1-2 sentences) "
            "and any proposed setpoint. Name the room if one is set in "
            "readings; if readings contain a per-room breakdown instead, "
            "use it to compare rooms."
        ),
        user=f"User request: {state['user_request']}\nReadings: {readings}",
    )

    return {
        "domain_outputs": {
            "access": {
                "readings": readings,
                "recommendation": recommendation,
            }
        },
        "log": [f"access: {recommendation[:60]}"],
    }
from llm.ollama_client import chat
from tools.mock_tools import call_tool
from database.building.topology import BUILDING_WIDE


def safety_agent(state):
    room = state.get("target_room")
    room = room if room and room != BUILDING_WIDE else None

    readings = {
        "room": room or BUILDING_WIDE,
        "fire_alarm": call_tool("fire_alarm", room=room) if room else call_tool("fire_alarm"),
    }

    recommendation = chat(
        system=(
            "You are the safety agent, expert in fire, smoke, gas and "
            "security threat detection. Given the readings and the user "
            "request, give a short recommendation (1-2 sentences) and any "
            "proposed action. Name the room if one is set in readings; if "
            "readings contain a per-room breakdown instead, use it to "
            "identify which room needs attention."
        ),
        user=f"User request: {state['user_request']}\nReadings: {readings}",
    )

    fa = readings.get("fire_alarm", {})

    emergency = bool(
        fa.get("fire")
        or fa.get("smoke")
        or fa.get("gas_ppm", 0) > 300
    )

    update = {
        "domain_outputs": {
            "safety": {
                "readings": readings,
                "recommendation": recommendation,
                "emergency": emergency,
            }
        },
        "log": [f"safety: {recommendation[:60]}"],
    }

    if emergency:
        update["emergency"] = True

    return update
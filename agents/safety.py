from llm.groq_client import chat
from tools.mock_tools import call_tool


def safety_agent(state):
    readings = {
        "fire_alarm": call_tool("fire_alarm")
    }

    recommendation = chat(
        system=(
            "You are the safety agent, expert in fire, smoke, gas and "
            "security threat detection. Given the readings and the user "
            "request, give a short recommendation (1-2 sentences) and any "
            "proposed action."
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
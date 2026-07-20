from llm.groq_client import chat
from tools.mock_tools import call_tool


def monitor_agent(state):
    readings = {
        "device_health": call_tool("device_health")
    }

    recommendation = chat(
        system=(
            "You are the monitor agent, expert in equipment health and "
            "device fault detection. Given the readings and the user "
            "request, give a short recommendation (1-2 sentences) and any "
            "proposed action."
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
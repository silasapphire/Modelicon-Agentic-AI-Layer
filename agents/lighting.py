from llm.groq_client import chat
from tools.mock_tools import call_tool


def lighting_agent(state):
    readings = {
        "lux_sensor": call_tool("lux_sensor"),
        "daylight": call_tool("daylight"),
    }

    recommendation = chat(
        system=(
            "You are the lighting agent, expert in lighting levels and "
            "lighting energy efficiency. Given the readings and the user "
            "request, give a short recommendation (1-2 sentences) and any "
            "proposed setpoint."
        ),
        user=f"User request: {state['user_request']}\nReadings: {readings}",
    )

    return {
        "domain_outputs": {
            "lighting": {
                "readings": readings,
                "recommendation": recommendation,
            }
        },
        "log": [f"lighting: {recommendation[:60]}"],
    }
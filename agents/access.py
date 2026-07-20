from llm.groq_client import chat
from tools.mock_tools import call_tool


def access_agent(state):
    readings = {
        "access_events": call_tool("access_events")
    }

    recommendation = chat(
        system=(
            "You are the access agent, expert in access control, "
            "occupancy and door management. Given the readings and the "
            "user request, give a short recommendation (1-2 sentences) "
            "and any proposed setpoint."
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
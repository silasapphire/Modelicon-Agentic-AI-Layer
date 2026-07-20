from llm.groq_client import chat
from tools.mock_tools import call_tool


def thermal_agent(state):
    readings = {
        "hvac_twin": call_tool("hvac_twin"),
        "comfort_index": call_tool("comfort_index"),
    }

    recommendation = chat(
        system=(
            "You are the thermal agent, expert in HVAC, temperature, "
            "ventilation and thermal comfort. Given the readings and the "
            "user request, give a short recommendation (1-2 sentences) "
            "and any proposed setpoint."
        ),
        user=f"User request: {state['user_request']}\nReadings: {readings}",
    )

    return {
        "domain_outputs": {
            "thermal": {
                "readings": readings,
                "recommendation": recommendation,
            }
        },
        "log": [f"thermal: {recommendation[:60]}"],
    }
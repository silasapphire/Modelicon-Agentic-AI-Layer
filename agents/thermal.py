from llm.groq_client import chat
from tools.mock_tools import call_tool


def thermal_agent(state):
    current = call_tool("current_temperature")
    lookup = call_tool("thermal_lookup_table").get("table", {})

    best_setpoint_c = None
    best_power_mw = None
    if lookup:
        best_temp_str, best_power_mw = min(lookup.items(), key=lambda kv: kv[1])
        best_setpoint_c = float(best_temp_str)

    readings = {
        "current_temperature": current,
        "lookup_table_c_to_mw": lookup,
        "best_setpoint_c": best_setpoint_c,
        "best_setpoint_power_mw": best_power_mw,
    }

    recommendation = chat(
        system=(
            "You are the thermal agent, expert in HVAC, temperature and "
            "energy-efficient thermal comfort. You have a lookup table "
            "mapping each candidate temperature setpoint (in Celsius) to "
            "the power it draws (in mW); current_temperature is the "
            "building's live setpoint and its power draw; best_setpoint_c "
            "and best_setpoint_power_mw are the setpoint from that table "
            "that minimises power draw. Given the readings and the user "
            "request, answer directly: if asked for the current "
            "temperature, state it plainly; if asked for the most "
            "energy-efficient setpoint, recommend best_setpoint_c and cite "
            "its power draw versus the current one; if asked to change "
            "the temperature to a specific value, confirm that value. "
            "Keep it to 1-2 sentences and always use target 'hvac' and "
            "parameter 'setpoint_c' when a setpoint is involved."
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

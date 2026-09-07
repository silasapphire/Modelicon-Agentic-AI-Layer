from llm.ollama_client import chat
from tools.mock_tools import call_tool
from agents.topic_filter import filter_for_prompt


def thermal_agent(state):
    lookup = call_tool("thermal_lookup_table").get("table", {})
    best_setpoint_c = None
    best_power_kw = None
    if lookup:
        best_temp_str, best_power_kw = min(lookup.items(), key=lambda kv: kv[1])
        best_setpoint_c = float(best_temp_str)

    current = call_tool("current_temperature")
    readings = {
        "current_temperature": current,
        "lookup_table_c_to_kw": lookup,
        "best_setpoint_c": best_setpoint_c,
        "best_setpoint_power_kw": best_power_kw,
    }

    recommendation = chat(
        system=(
            "You are the thermal agent, expert in HVAC and temperature "
            "for a single-zone building (one room). current_temperature "
            "is the live reading for that zone -- state it plainly. If "
            "asked to change the temperature to a specific value, "
            "confirm that value and use target 'hvac' and parameter "
            "'setpoint_c'. Readings only ever include "
            "lookup_table_c_to_kw / best_setpoint_c / "
            "best_setpoint_power_kw when the user's request explicitly "
            "asked about energy, efficiency, power, or savings -- when "
            "present, you may discuss them; when absent, do not bring "
            "up energy, power, or efficiency at all. A plain "
            "temperature question gets a plain temperature answer, "
            "nothing more. Keep it to 1-2 sentences."
        ),
        user=(
            f"User request: {state['user_request']}\n"
            f"Readings: {filter_for_prompt(readings, state['user_request'])}"
        ),
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

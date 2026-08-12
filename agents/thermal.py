from llm.ollama_client import chat
from tools.mock_tools import call_tool
from database.building.topology import BUILDING_WIDE, rooms_for_scope


def thermal_agent(state):
    target = state.get("target_room")
    # A specific room / building-wide keeps the single-reading path below;
    # only a floor label (e.g. "Floor 1") expands to more than one room.
    scope_rooms = rooms_for_scope(target) if target and target != BUILDING_WIDE else ()

    lookup = call_tool("thermal_lookup_table").get("table", {})
    best_setpoint_c = None
    best_power_mw = None
    if lookup:
        best_temp_str, best_power_mw = min(lookup.items(), key=lambda kv: kv[1])
        best_setpoint_c = float(best_temp_str)

    if len(scope_rooms) > 1:
        per_room_temperature_c = {}
        for room_name in scope_rooms:
            reading = call_tool("current_temperature", room=room_name)
            per_room_temperature_c[room_name] = reading.get("temp_c")
        known_temps = [t for t in per_room_temperature_c.values() if t is not None]
        average_temperature_c = round(sum(known_temps) / len(known_temps), 2) if known_temps else None

        readings = {
            "scope": target,
            "per_room_temperature_c": per_room_temperature_c,
            "average_temperature_c": average_temperature_c,
            "lookup_table_c_to_mw": lookup,
            "best_setpoint_c": best_setpoint_c,
            "best_setpoint_power_mw": best_power_mw,
        }
    else:
        room = scope_rooms[0] if scope_rooms else None
        current = call_tool("current_temperature", room=room) if room else call_tool("current_temperature")
        readings = {
            "room": room or BUILDING_WIDE,
            "current_temperature": current,
            "lookup_table_c_to_mw": lookup,
            "best_setpoint_c": best_setpoint_c,
            "best_setpoint_power_mw": best_power_mw,
        }

    recommendation = chat(
        system=(
            "You are the thermal agent, expert in HVAC and temperature. "
            "You have a lookup table mapping each candidate temperature "
            "setpoint (in Celsius) to the power it draws (in mW). If "
            "readings has 'per_room_temperature_c', the request covers a "
            "whole floor: report average_temperature_c AND list every "
            "room's temperature from per_room_temperature_c -- do not "
            "just give the average alone. Otherwise current_temperature "
            "is the live setpoint and its power draw for the single room "
            "in readings (or the whole building if none is set) -- state "
            "it plainly, naming the room if one is set. If asked to "
            "change the temperature to a specific value, confirm that "
            "value and use target 'hvac' and parameter 'setpoint_c'. "
            "best_setpoint_c and best_setpoint_power_mw are the setpoint "
            "that minimises power draw -- these exist in every reading "
            "but you must IGNORE them and say nothing about energy "
            "efficiency, optimal setpoints, or power savings UNLESS the "
            "user's request explicitly asks about energy, efficiency, "
            "power, or savings. A plain temperature question gets a "
            "plain temperature answer, nothing more. Keep it to 1-2 "
            "sentences (up to 3 only if listing multiple rooms)."
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

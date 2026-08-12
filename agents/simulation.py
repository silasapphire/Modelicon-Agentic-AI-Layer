from tools.mock_tools import call_tool
from database.building.topology import BUILDING_WIDE


def simulation_agent(state):
    room = state.get("target_room")
    room = room if room and room != BUILDING_WIDE else None

    opt = state.get("optimization_result", {})
    result = call_tool("modelica_sim", setpoint_c=opt.get("setpoint_c"), room=room)
    return {
        "simulation_result": result,
        "log": [
            f"simulate: room={room or BUILDING_WIDE} "
            f"pmv={result.get('predicted_comfort_pmv')} "
            f"load={result.get('predicted_load_kw')}kW"
        ],
    }

from tools.mock_tools import call_tool
from database.building.topology import BUILDING_WIDE


def optimization_agent(state):
    room = state.get("target_room")
    room = room if room and room != BUILDING_WIDE else None

    result = call_tool("energy_optimizer", request=state["user_request"], room=room)
    return {
        "optimization_result": result,
        "log": [
            f"optimize: room={room or BUILDING_WIDE} "
            f"setpoint={result.get('setpoint_c')} "
            f"saving={result.get('expected_saving_pct')}%"
        ],
    }

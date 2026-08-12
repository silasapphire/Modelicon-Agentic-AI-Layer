from tools.mock_tools import call_tool
from database.building.topology import BUILDING_WIDE

def query_agent(state):
    room = state.get("target_room")
    room = room if room and room != BUILDING_WIDE else None

    data = {
        "topology": call_tool("building_topology"),
        "sensors": call_tool("sensor_data", room=room) if room else call_tool("sensor_data"),
        "all_rooms": call_tool("all_rooms_status"),
        "history": call_tool("timeseries_db"),
        "weather": call_tool("weather"),
    }

    return {
        "retrieved_data": data,
        "log": [
            f"query: fetched sensors{f' (room={room})' if room else ''}, "
            "all_rooms, history, weather, topology"
        ],
    }
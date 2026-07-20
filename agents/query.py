from tools.mock_tools import call_tool

def query_agent(state):

    data = {
        "sensors": call_tool("sensor_data"),
        "history": call_tool("timeseries_db"),
        "weather": call_tool("weather"),
    }

    return {
        "retrieved_data": data,
        "log": [
            "query: fetched sensors, history, weather"
        ],
    }
from tools.mock_tools import call_tool


def optimization_agent(state):
    result = call_tool("energy_optimizer", request=state["user_request"])
    return {
        "optimization_result": result,
        "log": [
            f"optimize: setpoint={result.get('setpoint_c')} "
            f"saving={result.get('expected_saving_pct')}%"
        ],
    }

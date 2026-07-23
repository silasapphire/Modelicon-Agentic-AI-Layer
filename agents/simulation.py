from tools.mock_tools import call_tool


def simulation_agent(state):
    opt = state.get("optimization_result", {})
    result = call_tool("modelica_sim", setpoint_c=opt.get("setpoint_c"))
    return {
        "simulation_result": result,
        "log": [
            f"simulate: pmv={result.get('predicted_comfort_pmv')} "
            f"load={result.get('predicted_load_kw')}kW"
        ],
    }

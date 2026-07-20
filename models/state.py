from typing import TypedDict


class BuildingState(TypedDict, total=False):

    # User input
    user_request: str

    # Supervisor
    intent: str
    data_required: bool
    active_domains: list[str]
    emergency: bool

    # Query Agent
    retrieved_data: dict

    # Domain Agents
    domain_outputs: dict

    # Analysis
    analysis_result: dict
    needs_optimization: bool
    needs_simulation: bool

    # Optimization
    optimization_result: dict

    # Simulation
    simulation_result: dict

    # Coordination
    coordinated_plan: dict

    # Guardrail
    guardrail_status: str
    guardrail_feedback: str

    # Human approval
    human_decision: str

    # BMS
    execution_result: dict

    # Final output
    final_response: str

    # Logs
    log: list[str]
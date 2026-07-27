from typing import Annotated, TypedDict
from operator import add


def merge_dict(left: dict, right: dict) -> dict:
    return {**(left or {}), **(right or {})}


class BuildingState(TypedDict, total=False):
    user_request: str

    intent: str
    data_required: bool
    active_domains: list
    emergency: bool
    target_room: str

    retrieved_data: dict

    domain_outputs: Annotated[dict, merge_dict]

    analysis_result: dict
    needs_optimization: bool
    optimization_result: dict
    simulation_result: dict
    coordinated_plan: dict

    guardrail_status: str
    guardrail_feedback: str
    revision_count: int
    human_decision: str

    execution_result: dict
    final_response: str

    log: Annotated[list, add]

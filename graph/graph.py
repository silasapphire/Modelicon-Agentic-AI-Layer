from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from models.state import BuildingState
from agents.guardrail import guardrail_agent, human_review
from agents.supervisor import supervisor_agent
from agents.query import query_agent
from agents.thermal import thermal_agent
from agents.lighting import lighting_agent
from agents.access import access_agent
from agents.safety import safety_agent
from agents.monitor import monitor_agent
from agents.bms import bms_read_agent, bms_agent
from agents.analysis import analysis_agent
from agents.optimisation import optimization_agent
from agents.simulation import simulation_agent
from agents.coordinate import coordination_agent
from graph.routing import (
    DOMAINS,
    fan_out,
    route_after_supervisor,
    route_after_domains,
    route_after_analysis,
    route_after_guardrail,
)

_DOMAIN_AGENTS = {
    "thermal": thermal_agent,
    "lighting": lighting_agent,
    "access": access_agent,
    "safety": safety_agent,
    "monitor": monitor_agent,
    "bms": bms_read_agent,
}


def build_graph():
    b = StateGraph(BuildingState)
    b.add_node("supervisor", supervisor_agent)
    b.add_node("query", query_agent)
    for name, fn in _DOMAIN_AGENTS.items():
        b.add_node(name, fn)
    b.add_node("analysis", analysis_agent)
    b.add_node("optimization", optimization_agent)
    b.add_node("simulation", simulation_agent)
    b.add_node("coordination", coordination_agent)
    b.add_node("guardrail", guardrail_agent)
    b.add_node("human_review", human_review)
    b.add_node("bms_agent", bms_agent)

    b.add_edge(START, "supervisor")
    b.add_conditional_edges("supervisor", route_after_supervisor, ["query"] + DOMAINS)
    b.add_conditional_edges("query", fan_out, DOMAINS)
    for name in DOMAINS:
        b.add_conditional_edges(name, route_after_domains, ["analysis", "coordination"])
    b.add_conditional_edges("analysis", route_after_analysis, ["optimization", "coordination"])
    b.add_edge("optimization", "simulation")
    b.add_edge("simulation", "coordination")
    b.add_edge("coordination", "guardrail")
    b.add_conditional_edges(
        "guardrail", route_after_guardrail, DOMAINS + ["human_review", "bms_agent"]
    )
    b.add_edge("human_review", "bms_agent")
    b.add_edge("bms_agent", END)

    return b.compile(checkpointer=MemorySaver())

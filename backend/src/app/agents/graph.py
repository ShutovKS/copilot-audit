from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
import os

from src.app.domain.state import AgentState
from src.app.domain.enums import ProcessingStatus
from src.app.agents.nodes import analyst_node, coder_node, reviewer_node, batch_node


def route_after_analyst(state: AgentState) -> str:
    if state.get("status") == ProcessingStatus.COMPLETED:
        return "end"
    if state.get("scenarios") and len(state["scenarios"]) > 1:
        return "batch"
    return "coder"

def should_continue(state: AgentState) -> str:
    if state["status"] == ProcessingStatus.COMPLETED:
        return "end"
    if state.get("attempts", 0) >= 3:
        return "end"
    return "coder"


def create_workflow() -> StateGraph:
    """
    Constructs the StateGraph logic without compiling.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("analyst", analyst_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("batch", batch_node)

    workflow.set_entry_point("analyst")

    workflow.add_conditional_edges(
        "analyst",
        route_after_analyst,
        {
            "coder": "coder",
            "batch": "batch",
            "end": END
        }
    )
    
    workflow.add_edge("coder", "reviewer")
    workflow.add_edge("batch", END)
    
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "coder": "coder",
            "end": END
        }
    )
    return workflow

def compile_graph(checkpointer: BaseCheckpointSaver = None):
    """
    Compiles the graph with an optional checkpointer.
    """
    workflow = create_workflow()
    return workflow.compile(checkpointer=checkpointer)

from langgraph.graph import StateGraph, END

from src.app.domain.state import AgentState
from src.app.domain.enums import ProcessingStatus
from src.app.agents.nodes import analyst_node, coder_node, reviewer_node, batch_node


def route_after_analyst(state: AgentState) -> str:
    """
    Decides whether to go to single Coder or Batch Processor.
    """
    if state.get("scenarios") and len(state["scenarios"]) > 1:
        return "batch"
    return "coder"

def should_continue(state: AgentState) -> str:
    """
    Decides the next node based on the Reviewer's verdict.
    """
    if state["status"] == ProcessingStatus.COMPLETED:
        return "end"
    
    if state.get("attempts", 0) >= 3:
        # Fail safe to prevent infinite loops
        # In a real app, we might want to tag this as FAILED status
        return "end"
        
    return "coder"


def build_graph():
    """
    Constructs the Multi-Agent Workflow.
    """
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("batch", batch_node)

    # Set Entry Point
    workflow.set_entry_point("analyst")

    # Define Edges
    workflow.add_conditional_edges(
        "analyst",
        route_after_analyst,
        {
            "coder": "coder",
            "batch": "batch"
        }
    )
    
    workflow.add_edge("coder", "reviewer")
    workflow.add_edge("batch", END)
    
    # Conditional Edge from Reviewer
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "coder": "coder",
            "end": END
        }
    )

    return workflow.compile()

# Singleton instance
agent_graph = build_graph()

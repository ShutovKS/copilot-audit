from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
import os

from src.app.domain.state import AgentState
from src.app.domain.enums import ProcessingStatus
from src.app.agents.nodes import analyst_node, coder_node, reviewer_node, batch_node
from src.app.core.config import get_settings

settings = get_settings()

# Connection string for PostgresSaver (must use psycopg3 format)
DB_URI = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Global pool for checkpointer
connection_pool = AsyncConnectionPool(conninfo=DB_URI, max_size=20)
checkpointer = AsyncPostgresSaver(connection_pool)


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


def build_graph():
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

    # Compile with checkpointer for persistence
    return workflow.compile(checkpointer=checkpointer)

agent_graph = build_graph()

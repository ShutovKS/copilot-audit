from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from src.app.agents.nodes import analyst_node, batch_node, coder_node, final_output_node, reviewer_node, router_node
from src.app.domain.enums import ProcessingStatus
from src.app.domain.state import AgentState


def route_after_router(state: AgentState) -> str:
	"""Routes from the initial router to the correct starting workflow."""
	task_type = state.get("task_type", "ui_test_gen")
	if task_type == "debug_request":
		return "coder"  # Go directly to the coder/debugger
	return "analyst"  # Proceed with standard analysis


def route_after_analyst(state: AgentState) -> str:
	if state.get("status") == ProcessingStatus.COMPLETED:
		return "final_output"
	if state.get("status") == ProcessingStatus.WAITING_FOR_INPUT:
		return END
	if state.get("scenarios") and len(state["scenarios"]) > 1:
		return "batch"
	return "coder"


def should_continue(state: AgentState) -> str:
	if state["status"] == ProcessingStatus.COMPLETED:
		return "final_output"
	if state.get("attempts", 0) >= 3:
		return "end"
	return "coder"


def create_workflow() -> StateGraph:
	"""
	Constructs the StateGraph logic without compiling.
	"""
	workflow = StateGraph(AgentState)

	workflow.add_node("router", router_node)
	workflow.add_node("analyst", analyst_node)
	workflow.add_node("coder", coder_node)
	workflow.add_node("reviewer", reviewer_node)
	workflow.add_node("batch", batch_node)
	workflow.add_node("final_output", final_output_node)

	workflow.set_entry_point("router")

	workflow.add_conditional_edges(
		"router",
		route_after_router,
		{
			"analyst": "analyst",
			"coder": "coder"
		}
	)

	workflow.add_conditional_edges(
		"analyst",
		route_after_analyst,
		{
			"coder": "coder",
			"batch": "batch",
			"final_output": "final_output",
			END: END
		}
	)

	workflow.add_edge("coder", "reviewer")
	workflow.add_edge("batch", "final_output")
	workflow.add_edge("final_output", END)

	workflow.add_conditional_edges(
		"reviewer",
		should_continue,
		{
			"coder": "coder",
			"final_output": "final_output",
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

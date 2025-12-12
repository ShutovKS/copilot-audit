import functools

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from src.app.agents.nodes import (
	analyst_node,
	batch_node,
	debugger_node,
	feature_coder_node,
	final_output_node,
	human_approval_node,
	repo_explorer_node,
	reviewer_node,
	router_node,
)
from src.app.domain.enums import ProcessingStatus
from src.app.domain.state import AgentState


def route_after_router(state: AgentState) -> str:
	"""Routes from the initial router to the correct starting workflow."""
	task_type = state.get("task_type", "ui_test_gen")
	if task_type == "debug_request":
		return "debugger"  # Go directly to the debugger
	return "analyst"  # Proceed with standard analysis


def route_after_analyst(state: AgentState) -> str:
	if state.get("status") == ProcessingStatus.COMPLETED:
		return "final_output"
	# If analyst asked clarifying questions, stop the workflow and wait.
	if state.get("status") == ProcessingStatus.WAITING_FOR_INPUT:
		return END
	# Always require human approval before any generation step.
	return "human_approval"


def route_to_coder(state: AgentState) -> str:
	"""Route after approval to the correct coder type (feature vs. repo explorer) or batch."""
	if state.get("status") == ProcessingStatus.COMPLETED:
		return "final_output"
	if state.get("scenarios") and len(state["scenarios"]) > 1:
		return "batch"
	# New routing based on context
	if state.get("repo_path"):
		return "repo_explorer"
	return "feature_coder"


def route_after_reviewer(state: AgentState) -> str:
	"""Determines the next step after the reviewer node."""
	# If validation passed, the reviewer sets status to COMPLETED.
	if state["status"] == ProcessingStatus.COMPLETED:
		return "final_output"
	# If validation failed, reviewer sets status to FIXING. Check attempts.
	if state.get("attempts", 0) >= 3:
		# TODO: Add a "give_up" node to inform the user
		return END
	# Proceed to the debugger to fix the code
	return "debugger"


def create_workflow(embedding_function=None) -> StateGraph:
	"""
	Constructs the StateGraph logic without compiling.
	"""
	workflow = StateGraph(AgentState)

	# Bind the embedding function to each node that needs it
	workflow.add_node("router", router_node)
	workflow.add_node("analyst", functools.partial(analyst_node, embedding_function=embedding_function))
	workflow.add_node("human_approval", human_approval_node)
	workflow.add_node("feature_coder", feature_coder_node)
	workflow.add_node("repo_explorer", repo_explorer_node)
	workflow.add_node("debugger", debugger_node)
	workflow.add_node("reviewer", functools.partial(reviewer_node, embedding_function=embedding_function))
	workflow.add_node("batch", batch_node)
	workflow.add_node("final_output", final_output_node)

	workflow.set_entry_point("router")

	# Main flow
	workflow.add_conditional_edges("router", route_after_router, {"analyst": "analyst", "debugger": "debugger"})
	workflow.add_conditional_edges("analyst", route_after_analyst, {"human_approval": "human_approval", "final_output": "final_output", END: END})

	# Generation flow
	workflow.add_conditional_edges(
		"human_approval",
		route_to_coder,
		{
			"feature_coder": "feature_coder",
			"repo_explorer": "repo_explorer",
			"batch": "batch",
			"final_output": "final_output",
		}
	)

	# All code generation paths lead to the reviewer
	workflow.add_edge("feature_coder", "reviewer")
	workflow.add_edge("repo_explorer", "reviewer")
	workflow.add_edge("debugger", "reviewer")

	# Reviewer loop
	workflow.add_conditional_edges(
		"reviewer",
		route_after_reviewer,
		{
			"debugger": "debugger",
			"final_output": "final_output",
			END: END
		}
	)

	# End paths
	workflow.add_edge("batch", "final_output")
	workflow.add_edge("final_output", END)

	return workflow


def compile_graph(checkpointer: BaseCheckpointSaver = None, embedding_function=None):
    """
    Compiles the graph with an optional checkpointer.
    """
    workflow = create_workflow(embedding_function)
    # HITL: stop right after Analyst has produced the plan, before we enter the approval gate.
    # We intentionally DO NOT interrupt before coder nodes because that would also pause debug runs.
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])

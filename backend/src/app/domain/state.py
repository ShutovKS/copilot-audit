import operator
from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from src.app.domain.enums import ProcessingStatus, TestType


class AgentState(TypedDict):
	"""
	Core Data Contract for the Multi-Agent System.
	Maintains the complete context of the generation lifecycle.
	"""

	messages: Annotated[list[BaseMessage], add_messages]

	user_request: str
	model_name: str

	# Router / workflow metadata (optional at runtime)
	task_type: NotRequired[str]
	repo_path: NotRequired[str | None]
	run_id: NotRequired[int | None]

	# Learning memory / auto-fix bookkeeping
	was_fixing: NotRequired[bool]
	last_fix_old_code_path: NotRequired[str | None]
	last_fix_error: NotRequired[str | None]

	status: ProcessingStatus
	test_type: TestType | None
	attempts: int

	# Paths to large data artifacts stored externally
	test_plan_path: NotRequired[str | None]
	technical_context_path: NotRequired[str | None]
	generated_code_path: NotRequired[str | None]
	batch_results_path: NotRequired[str | None]
	log_path: NotRequired[str | None]

	scenarios: NotRequired[list[str] | None]  # Kept for now, assuming it's not excessively large
	validation_error: NotRequired[str | None]

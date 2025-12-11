import operator
from typing import Annotated, TypedDict

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

	status: ProcessingStatus
	test_type: TestType | None
	attempts: int

	test_plan: list[str]
	technical_context: str | None
	generated_code: str

	scenarios: list[str] | None
	batch_results: list[str] | None

	validation_error: str | None

	logs: Annotated[list[str], operator.add]

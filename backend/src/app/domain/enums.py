from enum import StrEnum, auto


class TestType(StrEnum):
	"""
	Defines the strategy for test generation.
	UI: Playwright + Page Object Model.
	API: Pytest + Requests + Pydantic.
	"""
	UI = auto()
	API = auto()


class ProcessingStatus(StrEnum):
	"""
	Current status of the agent workflow execution.
	"""
	IDLE = auto()
	ANALYZING = auto()
	GENERATING = auto()
	VALIDATING = auto()
	FIXING = auto()
	COMPLETED = auto()
	FAILED = auto()

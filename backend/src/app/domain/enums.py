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
	WAITING_FOR_INPUT = auto()
	COMPLETED = auto()
	FAILED = auto()


class ExecutionStatus(StrEnum):
	"""
	Status of the actual test execution in the container.
	"""
	PENDING = auto()  # Task is waiting in the queue
	RUNNING = auto()  # Task is being executed by a worker
	SUCCESS = auto()  # Test execution finished with no errors
	FAILURE = auto()  # Test execution failed

import operator
from typing import Annotated, TypedDict, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from src.app.domain.enums import ProcessingStatus, TestType


class AgentState(TypedDict):
    """
    Core Data Contract for the Multi-Agent System.
    Maintains the complete context of the generation lifecycle.
    """
    
    # Context & History (LangGraph Memory Requirement)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Input Data
    user_request: str
    
    # Workflow Control
    status: ProcessingStatus
    test_type: Optional[TestType]
    attempts: int
    
    # Artifacts
    test_plan: List[str]
    generated_code: str
    
    # Validation Loop Data
    validation_error: Optional[str]
    
    # Observability (Accumulated logs for Frontend)
    logs: Annotated[List[str], operator.add]

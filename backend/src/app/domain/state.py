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
    
    messages: Annotated[List[BaseMessage], add_messages]
    
    user_request: str
    model_name: str

    status: ProcessingStatus
    test_type: Optional[TestType]
    attempts: int
    
    test_plan: List[str]
    generated_code: str
    
    scenarios: Optional[List[str]]
    batch_results: Optional[List[str]]
    
    validation_error: Optional[str]
    
    logs: Annotated[List[str], operator.add]

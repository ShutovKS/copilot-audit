from typing import List, Optional
from pydantic import BaseModel
from src.app.domain.enums import ProcessingStatus, TestType

class TestGenerationRequest(BaseModel):
    user_request: str

class TestGenerationResponse(BaseModel):
    status: ProcessingStatus
    test_type: Optional[TestType] = None
    generated_code: Optional[str] = None
    test_plan: List[str] = []
    logs: List[str] = []
    error: Optional[str] = None

from fastapi import APIRouter, HTTPException
from src.app.api.models import TestGenerationRequest, TestGenerationResponse
from src.app.agents.graph import agent_graph
from src.app.domain.enums import ProcessingStatus

router = APIRouter()

@router.post("/generate", response_model=TestGenerationResponse)
async def generate_test(request: TestGenerationRequest):
    """
    Triggers the Multi-Agent Workflow to generate a test case.
    """
    # Initialize with all required keys to avoid KeyErrors in reducers
    initial_state = {
        "user_request": request.user_request,
        "messages": [],
        "attempts": 0,
        "logs": ["System: Workflow started."],
        "status": ProcessingStatus.IDLE,
        "test_type": None,
        "test_plan": [],
        "generated_code": "",
        "validation_error": None
    }
    
    try:
        # Run the graph
        # For MVP we await the result (Synchronous HTTP)
        # In Prod, this should be a Background Task with WebSocket updates
        result = await agent_graph.ainvoke(initial_state)
        
        return TestGenerationResponse(
            status=result["status"],
            test_type=result.get("test_type"),
            generated_code=result.get("generated_code"),
            test_plan=result.get("test_plan", []),
            logs=result.get("logs", []),
            error=result.get("validation_error") if result["status"] != ProcessingStatus.COMPLETED else None
        )
        
    except Exception as e:
        # Log the full error in a real app
        # In debug mode we return the string, in prod we might want to hide it
        raise HTTPException(status_code=500, detail=str(e))

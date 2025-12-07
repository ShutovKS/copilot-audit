import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from src.app.api.models import TestGenerationRequest
from src.app.agents.graph import agent_graph
from src.app.domain.enums import ProcessingStatus

router = APIRouter()

async def event_generator(request: TestGenerationRequest) -> AsyncGenerator[str, None]:
    """
    Generates SSE events from the LangGraph execution.
    """
    initial_state = {
        "user_request": request.user_request,
        "messages": [],
        "attempts": 0,
        "logs": ["System: Workflow initialized."],
        "status": ProcessingStatus.IDLE,
        "test_type": None,
        "test_plan": [],
        "generated_code": "",
        "validation_error": None
    }

    try:
        # Use .astream to get state updates as nodes finish
        async for output in agent_graph.astream(initial_state):
            # 'output' is a dict like {'analyst': {'logs': [...], ...}}
            for node_name, state_update in output.items():
                # Send logs if present
                if "logs" in state_update:
                    # LangGraph reducer appends logs, but here we get the delta or full list depending on config.
                    # For simplicity, we assume the last log is the new one or we send the specific log message.
                    # Since our reducer is operator.add, we might get the full list in some versions,
                    # but typically .astream returns the node's output.
                    
                    # Let's extract the NEW logs. 
                    # In our node implementation, we return "logs": ["Msg"].
                    # So state_update['logs'] is a list of new messages.
                    for log_msg in state_update["logs"]:
                        data = json.dumps({"type": "log", "content": log_msg})
                        yield f"data: {data}\n\n"
                
                # If code is generated, send it
                if "generated_code" in state_update and state_update["generated_code"]:
                    data = json.dumps({"type": "code", "content": state_update["generated_code"]})
                    yield f"data: {data}\n\n"
                
                # If status changed
                if "status" in state_update:
                    data = json.dumps({"type": "status", "content": state_update["status"]})
                    yield f"data: {data}\n\n"
                
                # Small delay to ensure frontend renders animation (UX polish)
                await asyncio.sleep(0.1)

        # Final success message
        yield f"data: {json.dumps({'type': 'finish', 'content': 'done'})}\n\n"

    except Exception as e:
        err_data = json.dumps({"type": "error", "content": str(e)})
        yield f"data: {err_data}\n\n"

@router.post("/generate")
async def generate_test_stream(request: TestGenerationRequest):
    """
    SSE Endpoint: Streams logs, status updates, and code generation.
    """
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream"
    )

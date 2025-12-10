import json
import asyncio
import logging
from typing import AsyncGenerator, List, Optional
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.app.core.database import AsyncSessionLocal
from src.app.services.history import HistoryService
from src.app.domain.enums import ProcessingStatus

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessageRequest(BaseModel):
    message: str
    model_name: Optional[str] = None
    run_id: Optional[int] = None  # If None, creates new run

async def chat_event_generator(request_body: ChatMessageRequest, session_id: str, app_state) -> AsyncGenerator[str, None]:
    agent_graph = app_state.agent_graph
    
    async with AsyncSessionLocal() as db:
        history_service = HistoryService(db)
        
        # 1. Initialize or Load Run
        if request_body.run_id:
            run = await history_service.get_by_id(request_body.run_id, session_id)
            if not run:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Chat session not found'})}\n\n"
                return
            run_id = run.id
            logger.info(f"Continuing chat run {run_id}")
        else:
            run = await history_service.create_run(request_body.message, session_id)
            run_id = run.id
            logger.info(f"Created new chat run {run_id}")
            # Send the new Run ID to frontend immediately
            yield f"data: {json.dumps({'type': 'meta', 'run_id': run_id})}\n\n"

        # 2. Prepare LangGraph Config (Persistence)
        config = {"configurable": {"thread_id": str(run_id)}}
        
        # 3. Update State with User Message
        # CRITICAL FIX: Reset 'attempts' and 'validation_error' to ensure fresh start for Auto-Fix
        input_state = {
            "messages": [HumanMessage(content=request_body.message)],
            "user_request": request_body.message, 
            "model_name": request_body.model_name or "Qwen/Qwen2.5-Coder-32B-Instruct",
            "status": ProcessingStatus.ANALYZING,
            "attempts": 0,
            "validation_error": None
        }

        final_code = ""
        
        try:
            # 4. Stream Graph Execution
            async for output in agent_graph.astream(input_state, config=config):
                for node_name, state_update in output.items():
                    
                    # Handle Logs
                    if "logs" in state_update:
                        for log_msg in state_update["logs"]:
                            data = json.dumps({"type": "log", "content": log_msg})
                            yield f"data: {data}\n\n"
                    
                    # Handle Plan Updates
                    if "test_plan" in state_update and state_update["test_plan"]:
                        plan_str = "\n".join(state_update["test_plan"])
                        data = json.dumps({"type": "plan", "content": plan_str})
                        yield f"data: {data}\n\n"

                    # Handle Code Updates
                    if "generated_code" in state_update and state_update["generated_code"]:
                        final_code = state_update["generated_code"]
                        data = json.dumps({"type": "code", "content": final_code})
                        yield f"data: {data}\n\n"

                    # Handle Status
                    if "status" in state_update:
                        data = json.dumps({"type": "status", "content": state_update["status"]})
                        yield f"data: {data}\n\n"

                    await asyncio.sleep(0.05)

            # 5. Finish
            yield f"data: {json.dumps({'type': 'finish', 'content': 'done'})}\n\n"
            
            # 6. Save Snapshot (Code only for now, full history is in LangGraph checkpoint)
            if final_code:
                await history_service.update_run(run_id=run_id, code=final_code, status=ProcessingStatus.COMPLETED)

        except Exception as e:
            logger.error(f"Chat Error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

@router.post("/message")
async def chat_message(
    request: Request, 
    body: ChatMessageRequest,
    x_session_id: str = Header(..., alias="X-Session-ID")
):
    return StreamingResponse(
        chat_event_generator(body, x_session_id, request.app.state),
        media_type="text/event-stream"
    )

import json
import asyncio
import logging
import httpx
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage

from src.app.api.models import TestGenerationRequest
from src.app.domain.enums import ProcessingStatus
from src.app.core.database import AsyncSessionLocal
from src.app.services.history import HistoryService
from src.app.services.llm_factory import CloudRuLLMService

logger = logging.getLogger(__name__)

router = APIRouter()

async def event_generator(request_body: TestGenerationRequest, app_state) -> AsyncGenerator[str, None]:
    # Get compiled graph from app state
    agent_graph = app_state.agent_graph
    
    async with AsyncSessionLocal() as db:
        logger.info(f"Starting generation for request: {request_body.user_request[:50]}...")
        history_service = HistoryService(db)
        
        run_record = await history_service.create_run(request_body.user_request)
        run_id = run_record.id
        logger.info(f"Run ID created: {run_id}")
        
        # Use run_id as thread_id for persistence
        config = {"configurable": {"thread_id": str(run_id)}}
        
        initial_state = {
            "user_request": request_body.user_request,
            "model_name": request_body.model_name or "Qwen/Qwen2.5-Coder-32B-Instruct",
            "messages": [],
            "attempts": 0,
            "logs": [f"System: Workflow initialized. Run ID: {run_id}"],
            "status": ProcessingStatus.IDLE,
            "test_type": None,
            "test_plan": [],
            "generated_code": "",
            "validation_error": None
        }

        final_code = ""
        final_status = ProcessingStatus.FAILED
        final_type = None

        try:
            logger.info("Starting agent graph stream...")
            async for output in agent_graph.astream(initial_state, config=config):
                logger.debug(f"Graph output received: {output.keys()}")
                for node_name, state_update in output.items():
                    if "logs" in state_update:
                        for log_msg in state_update["logs"]:
                            data = json.dumps({"type": "log", "content": log_msg})
                            yield f"data: {data}\n\n"
                    
                    if "test_plan" in state_update and state_update["test_plan"]:
                        plan_str = "\n".join(state_update["test_plan"])
                        data = json.dumps({"type": "plan", "content": plan_str})
                        yield f"data: {data}\n\n"

                    if "generated_code" in state_update and state_update["generated_code"]:
                        final_code = state_update["generated_code"]
                        data = json.dumps({"type": "code", "content": final_code})
                        yield f"data: {data}\n\n"
                    
                    if "status" in state_update:
                        final_status = state_update["status"]
                        data = json.dumps({"type": "status", "content": final_status})
                        yield f"data: {data}\n\n"
                    
                    if "test_type" in state_update and state_update["test_type"]:
                        final_type = state_update["test_type"]

                    await asyncio.sleep(0.1)

            logger.info(f"Agent graph finished with status: {final_status}")
            
            # Correctly handle final status
            if final_status == ProcessingStatus.COMPLETED:
                yield f"data: {json.dumps({'type': 'finish', 'content': 'done'})}\n\n"
            else:
                # Consider it an error if not completed successfully (e.g. max attempts reached)
                yield f"data: {json.dumps({'type': 'error', 'content': 'Failed to generate valid code after maximum attempts.'})}\n\n"
            
            await history_service.update_run(
                run_id=run_id,
                code=final_code,
                status=final_status,
                test_type=final_type
            )

        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            err_msg = str(e)
            err_data = json.dumps({"type": "error", "content": err_msg})
            yield f"data: {err_data}\n\n"
            
            await history_service.update_run(
                run_id=run_id,
                status=ProcessingStatus.FAILED
            )

@router.post("/generate")
async def generate_test_stream(request: Request, body: TestGenerationRequest):
    return StreamingResponse(
        event_generator(body, request.app.state),
        media_type="text/event-stream"
    )

class EnhanceRequest(BaseModel):
    prompt: str

@router.post("/enhance")
async def enhance_prompt(request: EnhanceRequest):
    llm_service = CloudRuLLMService()
    llm = llm_service.get_model()
    
    system_prompt = """
    You are a QA Expert Prompt Engineer.
    Rewrite the user's request to be more structured, detailed, and suitable for an automated test generator.
    Add explicit steps, expected results, and edge cases if missing.
    Keep it concise but professional.
    Output ONLY the improved prompt text.
    """
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=request.prompt)
        ])
        return {"enhanced_prompt": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_models():
    """
    Proxy to Cloud.ru to fetch available models.
    """
    settings = get_settings()
    url = f"{settings.CLOUD_RU_BASE_URL}/models"
    headers = {"Authorization": f"Bearer {settings.CLOUD_RU_API_KEY.get_secret_value()}"}
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

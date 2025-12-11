import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.app.api.models import TestGenerationRequest
from src.app.core.config import get_settings
from src.app.core.database import AsyncSessionLocal
from src.app.domain.enums import ProcessingStatus
from src.app.services.history import HistoryService
from src.app.services.llm_factory import CloudRuLLMService

logger = logging.getLogger(__name__)

router = APIRouter()


async def event_generator(request_body: TestGenerationRequest, session_id: str, app_state) -> AsyncGenerator[str, None]:
	agent_graph = app_state.agent_graph

	async with AsyncSessionLocal() as db:
		logger.info(f"Starting generation for user {session_id[:6]}...")
		history_service = HistoryService(db)

		run_record = await history_service.create_run(request_body.user_request, session_id)
		run_id = run_record.id

		config = {"configurable": {"thread_id": str(run_id)}}

		initial_state = {
			"run_id": run_id,
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
		final_plan_str = ""
		final_status = ProcessingStatus.FAILED
		final_type = None

		try:
			async for output in agent_graph.astream(initial_state, config=config):
				for _node_name, state_update in output.items():
					if "logs" in state_update:
						for log_msg in state_update["logs"]:
							data = json.dumps({"type": "log", "content": log_msg})
							yield f"data: {data}\n\n"

					if "test_plan" in state_update and state_update["test_plan"]:
						plan_str = "\n".join(state_update["test_plan"])
						final_plan_str = plan_str
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

			if final_status == ProcessingStatus.COMPLETED:
				yield f"data: {json.dumps({'type': 'finish', 'content': 'done'})}\n\n"
			else:
				yield f"data: {json.dumps({'type': 'error', 'content': 'Failed to generate valid code.'})}\n\n"

			hypothesis_match = re.search(r"# HYPOTHESIS: (.*)", final_code)
			hypothesis = hypothesis_match.group(1).strip() if hypothesis_match else None

			await history_service.update_run(
				run_id=run_id,
				code=final_code,
				status=final_status,
				test_type=final_type,
				test_plan=final_plan_str,
				hypothesis=hypothesis
			)

		except Exception as e:
			logger.error(f"Generation failed: {e}", exc_info=True)
			err_data = json.dumps({"type": "error", "content": str(e)})
			yield f"data: {err_data}\n\n"

			await history_service.update_run(
				run_id=run_id,
				status=ProcessingStatus.FAILED
			)


@router.post("/generate")
async def generate_test_stream(
		request: Request,
		body: TestGenerationRequest,
		x_session_id: str = Header(..., alias="X-Session-ID")
):
	return StreamingResponse(
		event_generator(body, x_session_id, request.app.state),
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
		raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/models")
async def list_models():
	settings = get_settings()
	url = f"{settings.CLOUD_RU_BASE_URL}/models"
	headers = {"Authorization": f"Bearer {settings.CLOUD_RU_API_KEY.get_secret_value()}"}

	try:
		async with httpx.AsyncClient() as client:
			resp = await client.get(url, headers=headers, timeout=10)
			resp.raise_for_status()
			return resp.json()
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e)) from e

import logging
import shutil
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Header, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from src.app.api.models import ChatMessageRequest, ApprovalRequest
from src.app.core.config import get_settings
from src.app.core.database import AsyncSessionLocal
from src.app.domain.enums import ProcessingStatus
from src.app.services.history import HistoryService
from src.app.services.streaming_service import StreamingService, _state_next_contains, _maybe_await


logger = logging.getLogger(__name__)

router = APIRouter()


async def chat_event_generator(
	request_body: ChatMessageRequest, session_id: str, app_state: any
) -> AsyncGenerator[str, None]:
	"""
	Main entry point for starting or continuing a chat.
	Delegates all streaming and business logic to StreamingService.
	"""
	async with AsyncSessionLocal() as db:
		history_service = HistoryService(db)
		streaming_service = StreamingService(
			agent_graph=app_state.agent_graph,
			history_service=history_service,
			app_state=app_state,
		)
		async for event in streaming_service.stream_graph_events(request_body, session_id):
			yield event


@router.post("/message")
async def chat_message(
	request: Request,
	body: ChatMessageRequest,
	x_session_id: str = Header(..., alias="X-Session-ID"),
):
	"""Handles a new user message and streams the response."""
	return StreamingResponse(
		chat_event_generator(body, x_session_id, request.app.state),
		media_type="text/event-stream",
	)


@router.post("/approve")
async def approve_step(
	request: Request,
	body: ApprovalRequest,
	x_session_id: str = Header(..., alias="X-Session-ID"),
):
	"""
	Resumes a paused LangGraph run after human approval, denial, or feedback.
	"""
	agent_graph = request.app.state.agent_graph
	config = {"configurable": {"thread_id": str(body.run_id)}}

	async with AsyncSessionLocal() as db:
		history_service = HistoryService(db)

		# Pre-flight checks before starting a stream
		run = await history_service.get_by_id(body.run_id, x_session_id)
		if not run:
			raise HTTPException(status_code=404, detail="Run not found")

		if not body.approved:
			await history_service.update_run(run_id=body.run_id, status=ProcessingStatus.FAILED)
			return JSONResponse(content={"status": "rejected"}, status_code=200)

		state_snapshot = await _maybe_await(
			agent_graph.aget_state(config) if hasattr(agent_graph, "aget_state") else agent_graph.get_state(config)
		)
		if not _state_next_contains(state_snapshot, "human_approval"):
			raise HTTPException(status_code=400, detail="No pending approval found for this run")

		# If all checks pass, create the streaming generator
		async def resume_generator():
			# Re-create the service inside the generator scope
			async with AsyncSessionLocal() as db_stream:
				history_service_stream = HistoryService(db_stream)
				streaming_service = StreamingService(
					agent_graph=agent_graph,
					history_service=history_service_stream,
					app_state=request.app.state,
				)
				try:
					async for event in streaming_service.resume_stream_events(body):
						yield event
				except Exception as e:
					logger.error(f"Failed to start resume stream: {e}", exc_info=True)
					yield f"data: {{\"type\": \"error\", \"content\": \"Failed to resume process.\"}}\n\n"

	return StreamingResponse(resume_generator(), media_type="text/event-stream")


@router.post("/reset")
async def chat_reset(x_session_id: str = Header(..., alias="X-Session-ID")):
	"""
	Resets the session state by deleting run artifacts.
	"""
	logger.info(f"Full Reset triggered for session {x_session_id}")
	settings = get_settings()

	# Clean up directories
	temp_dir_path = settings.TEMP_DIR
	reports_dir_path = settings.REPORTS_DIR

	if temp_dir_path.exists() and temp_dir_path.is_dir():
		shutil.rmtree(temp_dir_path)
		logger.info(f"🧹 Removed temp dir: {temp_dir_path}")

	if reports_dir_path.exists() and reports_dir_path.is_dir():
		shutil.rmtree(reports_dir_path)
		logger.info(f"🧹 Removed reports dir: {reports_dir_path}")

	storage_path = settings.STORAGE_PATH
	if storage_path.exists() and storage_path.is_dir():
		shutil.rmtree(storage_path)
		logger.info(f"🧹 Removed storage dir: {storage_path}")

	return {"status": "ok"}


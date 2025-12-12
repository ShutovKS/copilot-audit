import asyncio
import json
import logging
from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.core.config import get_settings
from src.app.core.database import get_db
from src.app.domain.models import TestRun
from src.app.services.tools.trace_inspector import TraceInspector
from src.app.tasks import run_test_task

logger = logging.getLogger(__name__)
router = APIRouter()


class ExecutionResponse(BaseModel):
	run_id: int
	status: str
	message: str


class DebugContextResponse(BaseModel):
	summary: str
	original_error: str
	dom_snapshot: str
	network_errors: list[str]
	console_logs: list[str]
	hypothesis: str | None


@router.post("/{run_id}/run", response_model=ExecutionResponse)
async def run_test(
		run_id: int,
		db: Annotated[AsyncSession, Depends(get_db)],
		x_session_id: str = Header(..., alias="X-Session-ID")
):
	result = await db.execute(
		select(TestRun).where(TestRun.id == run_id, TestRun.session_id == x_session_id)
	)
	run = result.scalars().first()

	if not run or not run.generated_code:
		raise HTTPException(status_code=404, detail="Test run not found or no code generated")

	# Отправляем задачу в Celery
	run_test_task.delay(run_id, run.generated_code)

	# Обновляем статус в БД
	run.execution_status = "PENDING"
	await db.commit()

	return ExecutionResponse(
		run_id=run.id,
		status="queued",
		message="Task execution started in background"
	)


async def log_stream_generator(run_id: int):
	"""
	Подписывается на Redis канал и стримит логи клиенту.
	"""
	settings = get_settings()
	redis_client = redis.from_url(settings.CELERY_BROKER_URL, encoding="utf-8", decode_responses=True)
	pubsub = redis_client.pubsub()
	channel = f"run:{run_id}:logs"

	await pubsub.subscribe(channel)

	try:
		async for message in pubsub.listen():
			if message['type'] == 'message':
				data = message['data']
				if data == "---EOF---":
					break
				yield f"data: {json.dumps({'content': data})}\n\n"
	finally:
		await pubsub.unsubscribe(channel)
		await redis_client.aclose()


@router.get("/{run_id}/logs")
async def stream_test_logs(
		run_id: int,
		x_session_id: str = Header(..., alias="X-Session-ID")
):
	return StreamingResponse(
		log_stream_generator(run_id),
		media_type="text/event-stream"
	)


@router.get("/{run_id}/debug-context", response_model=DebugContextResponse)
async def get_debug_context(
		run_id: int,
		db: Annotated[AsyncSession, Depends(get_db)],
		x_session_id: str = Header(..., alias="X-Session-ID")
):
	result = await db.execute(
		select(TestRun).where(TestRun.id == run_id, TestRun.session_id == x_session_id)
	)
	run = result.scalars().first()

	if not run:
		raise HTTPException(status_code=404, detail="Test run not found")

	# Разрешаем запрос контекста, даже если статус не FAILURE (для дебага)
	inspector = TraceInspector()
	context = inspector.get_failure_context(run.id, run.execution_logs or "")

	if not context:
		# Если контекста нет, возвращаем пустую заглушку, чтобы фронт не падал
		return DebugContextResponse(
			summary="No trace data available.",
			original_error=run.execution_logs or "No logs available.",
			dom_snapshot="",
			network_errors=[],
			console_logs=[],
			hypothesis=run.hypothesis
		)

	return DebugContextResponse(
		summary=context.get("summary", "N/A"),
		original_error=context.get("original_error", ""),
		dom_snapshot=context.get("dom_snapshot", "DOM snapshot not found."),
		network_errors=context.get("network_errors", []),
		console_logs=context.get("console_logs", []),
		hypothesis=run.hypothesis
	)

from typing import Annotated  # Added import for Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.core.database import get_db
from src.app.domain.models import TestRun
from src.app.services.executor import TestExecutorService
from src.app.services.tools.trace_inspector import TraceInspector

router = APIRouter()


class ExecutionResponse(BaseModel):
	run_id: int
	success: bool
	logs: str
	report_url: str | None


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

	executor = TestExecutorService()
	success, logs, report_url = await executor.execute_test(run.id, run.generated_code)

	run.execution_status = "SUCCESS" if success else "FAILURE"
	run.execution_logs = logs
	run.report_url = report_url

	await db.commit()
	await db.refresh(run)

	return ExecutionResponse(
		run_id=run.id,
		success=success,
		logs=logs,
		report_url=report_url
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

	if run.execution_status != "FAILURE" or not run.execution_logs:
		raise HTTPException(status_code=400, detail="Debug context is only available for failed runs with logs")

	inspector = TraceInspector()
	# The 'original_error' for the inspector is the execution log
	context = inspector.get_failure_context(run.id, run.execution_logs)

	if not context:
		raise HTTPException(status_code=404,
												detail="Failed to retrieve trace file context. The trace file might be missing or corrupted.")

	return DebugContextResponse(
		summary=context.get("summary", "N/A"),
		original_error=context.get("original_error", ""),
		dom_snapshot=context.get("dom_snapshot", "DOM snapshot not found."),
		network_errors=context.get("network_errors", []),
		console_logs=context.get("console_logs", []),
		hypothesis=run.hypothesis  # Will be added in the next step
	)

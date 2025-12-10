from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from src.app.core.database import get_db
from src.app.domain.models import TestRun
from src.app.services.executor import TestExecutorService

router = APIRouter()

class ExecutionResponse(BaseModel):
    run_id: int
    success: bool
    logs: str
    report_url: str | None

@router.post("/{run_id}/run", response_model=ExecutionResponse)
async def run_test(
    run_id: int,
    db: AsyncSession = Depends(get_db),
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
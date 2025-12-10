from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from src.app.core.database import get_db
from src.app.services.history import HistoryService

router = APIRouter()

class TestRunSchema(BaseModel):
    id: int
    user_request: str
    test_type: str | None
    status: str
    generated_code: str | None
    test_plan: str | None
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[TestRunSchema])
async def get_history(
    db: AsyncSession = Depends(get_db), 
    x_session_id: str = Header(..., alias="X-Session-ID")
):
    service = HistoryService(db)
    return await service.get_all(x_session_id)

@router.get("/{run_id}", response_model=TestRunSchema)
async def get_run(
    run_id: int, 
    db: AsyncSession = Depends(get_db),
    x_session_id: str = Header(..., alias="X-Session-ID")
):
    service = HistoryService(db)
    run = await service.get_by_id(run_id, x_session_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or access denied")
    return run

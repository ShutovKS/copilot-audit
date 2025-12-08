from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.domain.models import TestRun

class HistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_run(self, user_request: str) -> TestRun:
        run = TestRun(user_request=user_request, status="PROCESSING")
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def update_run(self, run_id: int, code: str = None, status: str = None, test_type: str = None):
        result = await self.db.execute(select(TestRun).where(TestRun.id == run_id))
        run = result.scalars().first()
        if run:
            if code: run.generated_code = code
            if status: run.status = status
            if test_type: run.test_type = test_type
            await self.db.commit()
            await self.db.refresh(run)
        return run

    async def get_all(self, limit: int = 10) -> List[TestRun]:
        result = await self.db.execute(select(TestRun).order_by(TestRun.created_at.desc()).limit(limit))
        return result.scalars().all()

    async def get_by_id(self, run_id: int) -> Optional[TestRun]:
        result = await self.db.execute(select(TestRun).where(TestRun.id == run_id))
        return result.scalars().first()

from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.domain.models import TestRun


class HistoryService:
	def __init__(self, db: AsyncSession, connection_pool: AsyncConnectionPool = None):
		self.db = db
		self.connection_pool = connection_pool

	async def create_run(self, user_request: str, session_id: str) -> TestRun:
		run = TestRun(
			user_request=user_request,
			session_id=session_id,
			status="PROCESSING"
		)
		self.db.add(run)
		await self.db.commit()
		await self.db.refresh(run)
		return run

	async def update_run(self, run_id: int, code: str = None, status: str = None, test_type: str = None,
											 test_plan: str = None, hypothesis: str = None):
		result = await self.db.execute(select(TestRun).where(TestRun.id == run_id))
		run = result.scalars().first()
		if run:
			if code:
				run.generated_code = code
			if status:
				run.status = status
			if test_type:
				run.test_type = test_type
			if test_plan:
				run.test_plan = test_plan
			if hypothesis:
				run.hypothesis = hypothesis
			await self.db.commit()
			await self.db.refresh(run)
		return run

	async def get_all(self, session_id: str, limit: int = 20) -> list[TestRun]:
		result = await self.db.execute(
			select(TestRun)
			.where(TestRun.session_id == session_id)
			.order_by(TestRun.created_at.desc())
			.limit(limit)
		)
		return result.scalars().all()

	async def get_by_id(self, run_id: int, session_id: str) -> TestRun | None:
		result = await self.db.execute(
			select(TestRun)
			.where(TestRun.id == run_id, TestRun.session_id == session_id)
		)
		return result.scalars().first()

	async def get_run_details(self, run_id: int, session_id: str) -> dict[str, Any] | None:
		run = await self.get_by_id(run_id, session_id)
		if not run:
			return None

		if not self.connection_pool:
			return {"run": run, "messages": []}

		checkpointer = AsyncPostgresSaver(self.connection_pool)
		config = {"configurable": {"thread_id": str(run_id)}}

		try:
			checkpoint = await checkpointer.aget(config)
			messages = checkpoint['channel_values'][
				'messages'] if checkpoint and 'channel_values' in checkpoint and 'messages' in checkpoint[
				'channel_values'] else []
		except Exception:
			messages = []

		return {"run": run, "messages": messages}

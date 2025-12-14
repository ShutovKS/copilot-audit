import logging
from typing import Any, Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.domain.models import TestRun

logger = logging.getLogger(__name__)


class HistoryService:
	def __init__(self, db: AsyncSession):
		self.db = db

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

	async def update_run(self, run_id: int, code_path: Optional[str] = None, status: Optional[str] = None,
											 test_type: Optional[str] = None, test_plan_path: Optional[str] = None,
											 hypothesis: Optional[str] = None):
		result = await self.db.execute(select(TestRun).where(TestRun.id == run_id))
		run = result.scalars().first()
		if run:
			if code_path is not None:
				run.generated_code_path = code_path
			if status is not None:
				run.status = status
			if test_type is not None:
				run.test_type = test_type
			if test_plan_path is not None:
				run.test_plan_path = test_plan_path
			if hypothesis is not None:
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

	async def get_run_details(self, run_id: int, session_id: str, connection_pool: AsyncConnectionPool | None) -> dict[str, Any] | None:
		run = await self.get_by_id(run_id, session_id)
		if not run:
			return None

		if not connection_pool:
			# If connection_pool is not available, we can't get checkpoint messages.
			# This is a valid scenario if the checkpoint backend is disabled.
			return {"run": run, "messages": []}

		checkpointer = AsyncPostgresSaver(connection_pool)
		config = {"configurable": {"thread_id": str(run_id)}}

		messages = []
		checkpoint_plan: str | None = None
		checkpoint_code: str | None = None
		try:
			checkpoint = await checkpointer.aget(config)
			channel_values = checkpoint.get("channel_values", {}) if checkpoint else {}
			messages = channel_values.get("messages", []) or []

			# For checkpoint_plan and checkpoint_code, we now expect paths
			plan_path_val = channel_values.get("test_plan_path")
			if plan_path_val and isinstance(plan_path_val, str):
				# Need to import storage_service here or pass it in
				from src.app.services.storage import storage_service
				checkpoint_plan = storage_service.load(plan_path_val)

			code_path_val = channel_values.get("generated_code_path")
			if code_path_val and isinstance(code_path_val, str):
				from src.app.services.storage import storage_service
				checkpoint_code = storage_service.load(code_path_val)

		except Exception as e:
			logger.error(f"Error loading checkpoint for run_id {run_id}: {e}", exc_info=True)
			messages = []

		return {
			"run": run,
			"messages": messages,
			"checkpoint_test_plan": checkpoint_plan,
			"checkpoint_generated_code": checkpoint_code,
		}

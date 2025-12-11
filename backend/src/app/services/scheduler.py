import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from langgraph.graph import StateGraph
from sqlalchemy import func
from sqlalchemy.future import select

from src.app.core.database import AsyncSessionLocal
from src.app.domain.enums import ProcessingStatus
from src.app.domain.models import TestRun
from src.app.services.executor import TestExecutorService
from src.app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def trigger_auto_fix(agent_graph: StateGraph, failed_run: TestRun, logs: str):
	"""
	Constructs an initial state for an auto-fix run and invokes the agent graph.
	"""
	logger.info(f"⚙️ [Auto-Fix] Triggering for failed run #{failed_run.id}.")

	config = {"configurable": {"thread_id": f"autofix-{failed_run.id}"}}

	initial_state = {
		"run_id": None,
		"user_request": f"[AUTO-FIX]\nOriginal Request: {failed_run.user_request}\n\nExecution Log:\n{logs}",
		"generated_code": failed_run.generated_code,
		"model_name": "Qwen/Qwen3-Coder-480B-A35B-Instruct",
		"messages": [], "attempts": 0, "logs": [], "status": ProcessingStatus.IDLE,
		"test_type": failed_run.test_type, "test_plan": [failed_run.test_plan], "validation_error": None
	}

	final_state = await agent_graph.ainvoke(initial_state, config=config)
	logger.info(f"✅ [Auto-Fix] Graph execution for run #{failed_run.id} completed.")

	if final_state.get("status") == ProcessingStatus.COMPLETED:
		logger.info(f"✅ [Auto-Fix] Successfully repaired test for run #{failed_run.id}. Creating notification.")
		try:
			async with AsyncSessionLocal() as db:
				notification_service = NotificationService()
				await notification_service.create_notification(
					db=db,
					session_id=failed_run.session_id,
					message=f"Test for '{failed_run.user_request[:40]}...' was automatically repaired.",
					related_run_id=failed_run.id
				)
		except Exception as e:
			logger.error(f"❌ [Auto-Fix] Failed to create notification: {e}")


async def run_health_checks(agent_graph: StateGraph):
	"""
	Scheduled job to re-run previously successful tests to check their 'health'.
	"""
	logger.info("🩺 [Scheduler] Starting periodic health check of existing tests...")

	executor = TestExecutorService()

	async with AsyncSessionLocal() as db:
		subquery = (
			select(TestRun.user_request, func.max(TestRun.id).label("max_id"))
			.where(TestRun.execution_status == 'SUCCESS')
			.group_by(TestRun.user_request)
			.subquery()
		)
		result = await db.execute(select(TestRun).join(subquery, TestRun.id == subquery.c.max_id))
		latest_successful_runs = result.scalars().all()

		if not latest_successful_runs:
			logger.info("🩺 [Scheduler] No successful tests to check.")
			return

		logger.info(f"🩺 [Scheduler] Found {len(latest_successful_runs)} unique tests to check.")

		for run in latest_successful_runs:
			logger.info(f"🩺 [Scheduler] Health checking test for run #{run.id}...")
			try:
				success, logs, _ = await executor.execute_test(run_id=run.id, code=run.generated_code)

				if not success:
					logger.warning(f"❌ [Scheduler] Health check FAILED for test from run #{run.id}. Triggering auto-fix.")
					# Trigger the auto-fix workflow
					await trigger_auto_fix(agent_graph, run, logs)
				else:
					logger.info(f"✅ [Scheduler] Health check PASSED for test from run #{run.id}.")

			except Exception as e:
				logger.error(f"❌ [Scheduler] An error occurred during health check for run #{run.id}: {e}", exc_info=True)


class SchedulerService:
	def __init__(self):
		self.scheduler = AsyncIOScheduler(timezone="UTC")
		self.agent_graph = None

	def start(self, agent_graph: StateGraph):
		self.agent_graph = agent_graph
		logger.info("Starting scheduler...")
		self.scheduler.add_job(
			run_health_checks,
			'interval',
			hours=6,
			id='test_health_check',
			args=[self.agent_graph]
		)
		self.scheduler.start()
		logger.info("✅ Scheduler started. Health checks will run every 6 hours.")

	def shutdown(self):
		logger.info("Shutting down scheduler...")
		self.scheduler.shutdown()

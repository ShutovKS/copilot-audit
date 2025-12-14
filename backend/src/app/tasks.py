import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis

from src.app.core.celery_app import celery_app
from src.app.core.config import get_settings
from src.app.domain.models import TestRun
from src.app.domain.enums import ExecutionStatus
from src.app.services.executor import TestExecutorService
from src.app.services.storage import storage_service


logger = logging.getLogger(__name__)

async def _run_task_logic(run_id: int, generated_code_path: str):
    """
    Fully isolated async logic that manages its own resources.
    """

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    redis_client = redis.from_url(settings.CELERY_BROKER_URL, encoding="utf-8", decode_responses=True)
    
    log_channel = f"run:{run_id}:logs"
    executor = TestExecutorService()

    try:
        # --- START ---
        await redis_client.publish(log_channel, "--- Test execution started (Worker) ---")
        
        # Update DB status
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(TestRun).where(TestRun.id == run_id))
            run = result.scalars().first()
            if run:
                run.execution_status = ExecutionStatus.RUNNING
                await session.commit()

        # Load the code from the path
        code = storage_service.load(generated_code_path)

        # --- EXECUTE (Blocking Docker call wrapped in executor) ---
        success, raw_logs, report_url = await executor.execute_test(run_id, code)
        
        # Publish Logs to Redis (Chunked if too large)
        if raw_logs:
            # Save raw logs to file
            execution_logs_path = storage_service.save(raw_logs, run_id, "log")

            # Send logs in chunks to avoid Redis message size limits
            # Only send a summary or relevant parts to Redis, not the entire raw_logs
            summary_logs = raw_logs[:1000] + ("\n... (truncated)" if len(raw_logs) > 1000 else "")
            await redis_client.publish(log_channel, summary_logs)
        else:
            execution_logs_path = None


        # --- FINISH ---
        final_status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE
        await redis_client.publish(log_channel, f"--- Test execution finished: {final_status.value} ---")

        # Update DB result
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(TestRun).where(TestRun.id == run_id))
            run = result.scalars().first()
            if run:
                run.execution_status = final_status
                run.execution_logs_path = execution_logs_path
                run.report_url = report_url
                await session.commit()

        return {"success": success, "run_id": run_id}

    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        error_log_path = storage_service.save(str(e), run_id, "log")
        await redis_client.publish(log_channel, f"Error: {str(e)}")
        # Update DB error
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(TestRun).where(TestRun.id == run_id))
            run = result.scalars().first()
            if run:
                run.execution_status = ExecutionStatus.FAILURE
                run.execution_logs_path = error_log_path
                await session.commit()
        raise e
    finally:
        # --- CLEANUP ---
        await redis_client.publish(log_channel, "---EOF---")
        await redis_client.aclose()
        await engine.dispose()


@celery_app.task(bind=True)
def run_test_task(self, run_id: int, generated_code_path: str):
    # Creates a fresh event loop for this task execution
    return asyncio.run(_run_task_logic(run_id, generated_code_path))

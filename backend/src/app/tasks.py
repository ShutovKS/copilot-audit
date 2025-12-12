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


logger = logging.getLogger(__name__)

async def _run_task_logic(run_id: int, code: str):
    """
    Fully isolated async logic that manages its own resources.
    """

    
    # Database operations
    # The engine and SessionLocal will be initialized globally once per worker process.
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

        # --- EXECUTE (Blocking Docker call wrapped in executor) ---
        # executor.execute_test internally uses run_in_executor to avoid blocking this loop
        success, logs, report_url = await executor.execute_test(run_id, code)
        
        # Publish Logs to Redis (Chunked if too large)
        if logs:
            # Send logs in chunks to avoid Redis message size limits
            chunk_size = 4000
            for i in range(0, len(logs), chunk_size):
                await redis_client.publish(log_channel, logs[i:i+chunk_size])

        # --- FINISH ---
        final_status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILURE
        await redis_client.publish(log_channel, f"--- Test execution finished: {final_status.value} ---")

        # Update DB result
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(TestRun).where(TestRun.id == run_id))
            run = result.scalars().first()
            if run:
                run.execution_status = final_status
                run.execution_logs = logs
                run.report_url = report_url
                await session.commit()

        return {"success": success, "run_id": run_id}

    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        await redis_client.publish(log_channel, f"Error: {str(e)}")
        # Update DB error
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(TestRun).where(TestRun.id == run_id))
            run = result.scalars().first()
            if run:
                run.execution_status = ExecutionStatus.FAILURE
                run.execution_logs = str(e)
                await session.commit()
        raise e
    finally:
        # --- CLEANUP ---
        await redis_client.publish(log_channel, "---EOF---")
        await redis_client.aclose()
        await engine.dispose()


@celery_app.task(bind=True)
def run_test_task(self, run_id: int, code: str):
    # Creates a fresh event loop for this task execution
    return asyncio.run(_run_task_logic(run_id, code))

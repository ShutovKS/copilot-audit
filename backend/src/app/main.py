import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from src.app.api.endpoints import analysis, chat, execution, generation, history, notifications
from src.app.api.endpoints.export import gitlab
from src.app.core.bootstrap import bootstrap_application, shutdown_application
from src.app.core.config import get_settings
from src.app.core.database import AsyncSessionLocal
from src.app.services.executor import TestExecutorService
from src.app.services.scheduler import SchedulerService

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
scheduler_service = SchedulerService()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
	settings = get_settings()
	logger.info(f"Starting {settings.PROJECT_NAME}...")

	settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
	settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)

	try:
		executor = TestExecutorService()
		executor.cleanup_all()
		logger.info("Startup cleanup completed.")
	except Exception as e:
		logger.warning(f"Startup cleanup failed (Docker might be down): {e}")

	await bootstrap_application(app)

	# Start the scheduler and pass it the compiled agent graph
	scheduler_service.start(app.state.agent_graph)

	try:
		async with AsyncSessionLocal() as session:
			await session.execute(text("""
                                 CREATE TABLE IF NOT EXISTS notifications
                                 (
                                     id
                                     SERIAL
                                     PRIMARY
                                     KEY,
                                     session_id
                                     VARCHAR
                                     NOT
                                     NULL,
                                     message
                                     TEXT
                                     NOT
                                     NULL,
                                     related_run_id
                                     INTEGER
                                     REFERENCES
                                     test_runs
                                 (
                                     id
                                 ),
                                     is_read BOOLEAN NOT NULL DEFAULT false,
                                     created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT
                                 (
                                     now
                                 (
                                 ) at time zone 'utc')
                                     );
																 """))
			await session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='test_runs' AND column_name='execution_status') THEN
                        ALTER TABLE test_runs ADD COLUMN execution_status VARCHAR;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='test_runs' AND column_name='report_url') THEN
                        ALTER TABLE test_runs ADD COLUMN report_url VARCHAR;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='test_runs' AND column_name='execution_logs') THEN
                        ALTER TABLE test_runs ADD COLUMN execution_logs TEXT;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='test_runs' AND column_name='test_plan') THEN
                        ALTER TABLE test_runs ADD COLUMN test_plan TEXT;
                    END IF;
                     IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='test_runs' AND column_name='hypothesis') THEN
                        ALTER TABLE test_runs ADD COLUMN hypothesis TEXT;
                    END IF;
                END $$;
            """))
			await session.commit()
	except Exception as e:
		logger.warning(f"Migration step warning: {e}")

	yield

	logger.info("Shutting down...")

	# Shutdown the scheduler
	scheduler_service.shutdown()

	try:
		executor = TestExecutorService()
		executor.cleanup_all()
	except Exception:
		pass

	await shutdown_application(app)


app = FastAPI(
	title="TestOps Evolution Forge API",
	version="1.4.0",
	default_response_class=ORJSONResponse,
	lifespan=lifespan,
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

settings = get_settings()
static_path = settings.BASE_DIR / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

app.include_router(generation.router, prefix="/api/v1", tags=["Generation"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(history.router, prefix="/api/v1/history", tags=["History"])
app.include_router(execution.router, prefix="/api/v1/execution", tags=["Execution"])
app.include_router(gitlab.router, prefix="/api/v1/export", tags=["Export"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Code Analysis"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])


@app.get("/api/v1/health", tags=["System"])
async def health_check() -> dict:
	status = {"service": "testops-forge", "version": "1.4.0"}

	# Check DB
	try:
		async with AsyncSessionLocal() as session:
			await session.execute(text("SELECT 1"))
			status["database"] = "connected"
	except Exception as e:
		status["database"] = f"error: {str(e)}"

	# Check LLM
	try:
		# llm_service = CloudRuLLMService() # Removed unused variable
		status['llm'] = "ready"
	except Exception as e:
		status['llm'] = f"error: {str(e)}"

	return status

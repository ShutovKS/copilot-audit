import logging

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import text

from src.app.agents.graph import compile_graph
from src.app.core.config import get_settings
from src.app.core.database import AsyncSessionLocal, init_db

logger = logging.getLogger(__name__)


async def bootstrap_application(app):
	"""
	Performs all startup tasks:
	1. Initialize DB tables (SQLAlchemy)
	2. Run manual migrations (Hackathon fixes)
	3. Setup LangGraph persistence
	4. Compile Agent Graph
	"""
	settings = get_settings()

	await init_db()

	try:
		async with AsyncSessionLocal() as session:
			logger.info("Checking DB schema for session_id...")
			await session.execute(text(
				"ALTER TABLE test_runs ADD COLUMN IF NOT EXISTS session_id VARCHAR DEFAULT 'default' NOT NULL;"
			))
			await session.commit()
			logger.info("Schema updated (session_id added).")
	except Exception as e:
		logger.warning(f"Migration step warning: {e}")

	DB_URI = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

	try:
		logger.info("Running LangGraph migrations...")
		async with await psycopg.AsyncConnection.connect(DB_URI, autocommit=True) as conn:
			temp_saver = AsyncPostgresSaver(conn)
			await temp_saver.setup()
		logger.info("LangGraph migrations completed.")
	except Exception as e:
		logger.error(f"Failed to run LangGraph migrations: {e}")

	connection_pool = AsyncConnectionPool(conninfo=DB_URI, max_size=20, open=False)
	await connection_pool.open()

	checkpointer = AsyncPostgresSaver(connection_pool)
	app.state.agent_graph = compile_graph(checkpointer)
	app.state.connection_pool = connection_pool

	logger.info("Agent Graph compiled and ready.")


async def shutdown_application(app):
	"""
	Cleanup tasks on shutdown.
	"""
	if hasattr(app.state, "connection_pool"):
		logger.info("Closing LangGraph Postgres Pool...")
		await app.state.connection_pool.close()

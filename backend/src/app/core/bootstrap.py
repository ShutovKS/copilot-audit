import logging

import psycopg
from chromadb.utils import embedding_functions
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import text

from src.app.agents.graph import compile_graph
from src.app.core.config import get_settings
from src.app.core.database import AsyncSessionLocal, init_db
from src.app.services.llm_factory import CloudRuLLMService

logger = logging.getLogger(__name__)


async def preload_models(app):
    """
    Downloads and caches all required models at startup.
    """
    try:
        logger.info("Pre-loading all-MiniLM-L6-v2 embedding model...")
        app.state.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        logger.info("✅ Embedding model is ready.")
    except Exception as e:
        logger.error(f"Failed to preload embedding model: {e}", exc_info=True)

    try:
        logger.info("Pre-loading LLM and Tokenizer...")
        llm_service = CloudRuLLMService()
        await llm_service.check_connection()
        logger.info("✅ LLM and Tokenizer are ready.")
    except Exception as e:
        logger.error(f"Fatal: Failed to preload LLM: {e}", exc_info=True)
        # Potentially raise to abort startup
        raise e

async def bootstrap_application(app):
    """
    Performs all startup tasks:
    1. Initialize DB tables (SQLAlchemy)
    2. Run manual migrations (Hackathon fixes)
    3. Setup LangGraph persistence
    4. Compile Agent Graph
    5. Pre-load ML models
    """
    settings = get_settings()

    # Run model preloading first
    await preload_models(app)

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
    app.state.agent_graph = compile_graph(checkpointer, app.state.embedding_function)
    app.state.connection_pool = connection_pool

    logger.info("Agent Graph compiled and ready.")


async def shutdown_application(app):
	"""
	Cleanup tasks on shutdown.
	"""
	if hasattr(app.state, "connection_pool"):
		logger.info("Closing LangGraph Postgres Pool...")
		await app.state.connection_pool.close()

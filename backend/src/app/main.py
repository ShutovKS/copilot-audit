from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
import psycopg
import sys
from psycopg_pool import AsyncConnectionPool

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.app.core.config import get_settings
from src.app.core.database import init_db, AsyncSessionLocal
from src.app.api.endpoints import generation, history
from src.app.api.endpoints.export import gitlab
from src.app.services.llm_factory import CloudRuLLMService
from src.app.agents.graph import compile_graph

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    
    # 1. Init SQL DB (SQLAlchemy)
    await init_db()
    
    # 2. Init LangGraph Persistence
    DB_URI = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    # Run Migrations
    try:
        logger.info("Running LangGraph migrations...")
        async with await psycopg.AsyncConnection.connect(DB_URI, autocommit=True) as conn:
            temp_saver = AsyncPostgresSaver(conn)
            await temp_saver.setup()
        logger.info("LangGraph migrations completed.")
    except Exception as e:
        logger.error(f"Failed to run LangGraph migrations: {e}")

    # Create Pool and Compile Graph
    connection_pool = AsyncConnectionPool(conninfo=DB_URI, max_size=20, open=False)
    await connection_pool.open()
    
    checkpointer = AsyncPostgresSaver(connection_pool)
    app.state.agent_graph = compile_graph(checkpointer)
    app.state.connection_pool = connection_pool
    
    logger.info("Agent Graph compiled and ready.")
    
    yield
    
    # Cleanup
    logger.info("Closing LangGraph Postgres Pool...")
    await app.state.connection_pool.close()
    logger.info("Shutting down...")


app = FastAPI(
    title="TestOps Evolution Forge API",
    version="1.1.0",
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

app.include_router(generation.router, prefix="/api/v1", tags=["Generation"])
app.include_router(history.router, prefix="/api/v1/history", tags=["History"])
app.include_router(gitlab.router, prefix="/api/v1/export", tags=["Export"])


@app.get("/api/v1/health", tags=["System"])
async def health_check() -> dict:
    status = {
        "service": "testops-forge",
        "version": "1.1.0",
        "database": "unknown",
        "llm": "unknown"
    }
    
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {str(e)}"

    try:
        llm_service = CloudRuLLMService()
        if llm_service.get_model():
            status["llm"] = "ready"
    except Exception as e:
        status["llm"] = f"error: {str(e)}"
        
    return status

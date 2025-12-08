from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.app.core.config import get_settings
from src.app.core.database import init_db, AsyncSessionLocal
from src.app.api.endpoints import generation, history
from src.app.api.endpoints.export import gitlab
from src.app.services.llm_factory import CloudRuLLMService

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    await init_db()
    yield
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
    """
    Deep Health Check: DB + LLM Connection
    """
    status = {
        "service": "testops-forge",
        "version": "1.1.0",
        "database": "unknown",
        "llm": "unknown"
    }
    
    # 1. Check DB
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {str(e)}"

    # 2. Check LLM (Ping)
    # We don't make a real call to save tokens, just check initialization
    try:
        llm_service = CloudRuLLMService()
        if llm_service.get_model():
            status["llm"] = "ready"
    except Exception as e:
        status["llm"] = f"error: {str(e)}"
        
    return status

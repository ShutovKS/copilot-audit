from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.app.core.config import get_settings
from src.app.api.endpoints import generation
from src.app.api.endpoints.export import gitlab


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    get_settings()
    yield


app = FastAPI(
    title="TestOps Evolution Forge API",
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# Configured for Development (Allow All)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generation.router, prefix="/api/v1", tags=["Generation"])
app.include_router(gitlab.router, prefix="/api/v1/export", tags=["Export"])


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "testops-forge"}

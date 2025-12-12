import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	ENVIRONMENT: Literal["dev", "prod", "test"] = "dev"
	PROJECT_NAME: str = "TestOps Evolution Forge"

	CLOUD_RU_API_KEY: SecretStr
	CLOUD_RU_BASE_URL: str = "https://foundation-models.api.cloud.ru/v1"
	MODEL_NAME: str = "Qwen/Qwen3-Coder-480B-A35B-Instruct"

	DATABASE_URL: str = "postgresql+asyncpg://testops:testops@localhost:5432/testops"

	CHROMA_HOST: str = "localhost"
	CHROMA_PORT: int = 8001
 
	CELERY_BROKER_URL: str = "redis://redis:6379/0"
	CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

	# Playwright Remote Browser (via Playwright Browser Server)
	# When enabled, the runner container will CONNECT to a remote browser over WebSocket.
	PLAYWRIGHT_REMOTE_ENABLED: bool = False
	PLAYWRIGHT_BROWSER: str = "chromium"

	BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
	REPORTS_DIR: Path = BASE_DIR / "static" / "reports"

	# Use /app/temp_execution when in Docker, fallback to system temp for local dev
	TEMP_DIR: Path = Path("/app/temp_execution") if Path("/app/temp_execution").exists() else Path(tempfile.gettempdir()) / "testops_execution"

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=True,
		extra="ignore"
	)


@lru_cache
def get_settings() -> Settings:
	return Settings()

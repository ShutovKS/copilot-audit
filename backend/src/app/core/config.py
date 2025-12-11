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

	BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
	REPORTS_DIR: Path = BASE_DIR / "static" / "reports"

	TEMP_DIR: Path = Path(tempfile.gettempdir()) / "testops_execution"

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=True,
		extra="ignore"
	)


@lru_cache
def get_settings() -> Settings:
	return Settings()

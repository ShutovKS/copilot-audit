from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Configuration.
    Validates environment variables on startup.
    """
    ENVIRONMENT: Literal["dev", "prod", "test"] = "dev"
    PROJECT_NAME: str = "TestOps Evolution Forge"

    CLOUD_RU_API_KEY: SecretStr
    CLOUD_RU_BASE_URL: str = "https://api.evolution.cloud.ru/v1"
    MODEL_NAME: str = "Qwen2.5-Coder"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
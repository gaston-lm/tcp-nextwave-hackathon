"""Typed runtime configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://control_tower:control_tower_dev@localhost:5432/control_tower"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-luna"
    arize_space_id: str | None = None
    arize_api_key: SecretStr | None = None
    arize_project_name: str | None = None
    arize_collector_endpoint: str = "https://otlp.arize.com/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()

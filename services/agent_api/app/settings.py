"""Typed runtime configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ROOT / "data" / ".env", REPOSITORY_ROOT / "services" / "agent_api" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "control_tower_database"
    postgres_user: str = "postgres"
    postgres_password: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-luna"
    arize_space_id: str | None = None
    arize_api_key: SecretStr | None = None
    arize_project_name: str | None = None
    arize_collector_endpoint: str = "https://otlp.arize.com/v1"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.postgres_password is None:
            raise ValueError("POSTGRES_PASSWORD is not configured in data/.env")
        return (
            f"postgresql://{quote(self.postgres_user)}:"
            f"{quote(self.postgres_password.get_secret_value())}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

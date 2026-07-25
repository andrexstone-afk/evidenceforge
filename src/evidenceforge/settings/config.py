"""Typed environment-backed application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from ``EVIDENCEFORGE_*`` variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EVIDENCEFORGE_",
        extra="ignore",
        frozen=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    service_name: str = "evidenceforge"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "sqlite:///./evidenceforge.db"
    llm_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    openai_model: str = "gpt-5.6-sol"
    openai_reasoning_enabled: bool = True
    openai_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"
    ncbi_email: str | None = None
    ncbi_api_key: SecretStr | None = Field(default=None, repr=False)
    request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    request_retries: int = Field(default=2, ge=0, le=5)

    @field_validator("database_url")
    @classmethod
    def validate_sqlite_database_url(cls, value: str) -> str:
        """Keep the MVP persistence boundary limited to local SQLite URLs."""

        if not value.startswith("sqlite:///"):
            raise ValueError("database_url must use sqlite:/// during the MVP")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-level immutable settings instance."""

    return Settings()

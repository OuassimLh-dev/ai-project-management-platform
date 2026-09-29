from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_name: str = "AI Project Management Platform"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(repr=False)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        try:
            url = make_url(value)
        except ArgumentError:
            raise ValueError("DATABASE_URL must be a PostgreSQL URL") from None
        if url.drivername not in {"postgresql", "postgresql+psycopg"} or not url.host or not url.database:
            raise ValueError("DATABASE_URL must use PostgreSQL with a host and database name")
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/") or any(c in value for c in " ?#"):
            raise ValueError("API_V1_PREFIX must start with / and have no trailing /, spaces, query or fragment")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

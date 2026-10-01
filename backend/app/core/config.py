from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
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
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)

    cors_allowed_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, values: list[str]) -> list[str]:
        for origin in values:
            try:
                url = urlsplit(origin)
                valid = (url.scheme in {"http", "https"} and url.hostname and not url.username
                         and not url.password and not url.path and not url.query and not url.fragment
                         and "*" not in origin and not any(c.isspace() for c in origin))
                _ = url.port
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
        return values

    ai_provider: str = "none"
    ai_model: str = Field(default="", max_length=180)
    openai_api_key: SecretStr | None = None
    ai_timeout_seconds: float = Field(default=30, gt=0, le=120, allow_inf_nan=False)

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

"""Application-wide configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'duescope.db').as_posix()}"


class Settings(BaseSettings):
    app_name: str = "DueScope API"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False

    api_public_url: str = "http://127.0.0.1:8001"
    public_app_url: str = "http://localhost:3000"
    frontend_origins: str = "http://localhost:3000"

    database_url: str = DEFAULT_SQLITE_DATABASE_URL

    # Required for production session signing and provider-token encryption.
    # Development/test may omit them while the authentication layer is not enabled.
    app_session_secret: str | None = None
    token_encryption_key: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]

    @field_validator("frontend_origins")
    @classmethod
    def validate_frontend_origins(cls, value: str) -> str:
        origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("FRONTEND_ORIGINS must contain at least one origin.")
        return ",".join(origins)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            if not self.app_session_secret or len(self.app_session_secret) < 32:
                raise ValueError(
                    "APP_SESSION_SECRET must be set to at least 32 characters in production."
                )
            if not self.token_encryption_key:
                raise ValueError(
                    "TOKEN_ENCRYPTION_KEY must be set in production."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

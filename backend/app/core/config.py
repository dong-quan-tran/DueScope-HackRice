"""Application-wide configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

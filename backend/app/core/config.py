"""Application configuration loaded from environment variables.

All settings have defaults suitable for local development.
Production deployments MUST override secrets via environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────
    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "ProjectFlow"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── Server ───────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_workers: int = 1

    # ── Database ─────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://projectflow:projectflow@localhost:5432/projectflow"
    )
    database_sync_url: str = Field(
        default="postgresql+psycopg2://projectflow:projectflow@localhost:5432/projectflow"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("database_sync_url", mode="before")
    @classmethod
    def normalize_database_sync_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # Test database (overridden when running tests)
    test_database_url: str = Field(
        default="postgresql+asyncpg://projectflow:projectflow@localhost:5432/projectflow_test"
    )
    test_database_sync_url: str = Field(
        default="postgresql+psycopg2://projectflow:projectflow@localhost:5432/projectflow_test"
    )

    # ── JWT Authentication ───────────────────────────────────
    jwt_secret_key: str = Field(
        default="dev-jwt-secret-key-projectflow-change-in-production-min-32-chars"
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60 * 24)  # 24 hours

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: list[str] | str = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: list[str] | str) -> list[str] | str:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                import contextlib
                import json

                with contextlib.suppress(Exception):
                    loaded = json.loads(v_stripped)
                    if isinstance(loaded, list):
                        return [str(origin).strip() for origin in loaded]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Internal ─────────────────────────────────────────────
    internal_api_key: str = Field(default="change-me-in-production")

    # ── Derived helpers ──────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton.

    Uses lru_cache so environment is read once per process lifetime.
    Tests can override via environment variables or by patching this function.
    """
    return Settings()

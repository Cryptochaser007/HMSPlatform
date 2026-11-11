"""
Application configuration using Pydantic BaseSettings.
Loads values from environment variables and .env file.
"""

import json
from functools import lru_cache
from typing import Any, List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "HMS Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://hms:hms_secret@localhost:5432/hms_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any) -> str:
        """Ensure DATABASE_URL uses the asyncpg driver prefix."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Authentication / JWT ─────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_64"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # ── Field-level encryption (Fernet) ──────────────────────────────────
    ENCRYPTION_KEY: str = "CHANGE_ME_GENERATE_WITH_Fernet.generate_key"

    # ── ABDM Integration ─────────────────────────────────────────────────
    ABDM_BASE_URL: str = "https://dev.abdm.gov.in/gateway"
    ABDM_CLIENT_ID: str = ""
    ABDM_CLIENT_SECRET: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Accept comma-separated string, JSON list, or python list for CORS origins."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return []

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (reads .env once)."""
    return Settings()

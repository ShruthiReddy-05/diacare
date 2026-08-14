import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


def _resolve_env_files():
    """Load .env first, then .env.local overrides (later files take precedence)."""
    base = Path(__file__).resolve().parent
    files = []
    if (base / ".env").exists():
        files.append(str(base / ".env"))
    if (base / ".env.local").exists():
        files.append(str(base / ".env.local"))
    return tuple(files) if files else (".env",)


class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./diafit.db")
    # Sarvam is used strictly for speech recognition (ASR) and speech delivery (TTS).
    # No LLM is ever used to author, alter, or improvise clinical content -- that is
    # produced exclusively by the deterministic decision engine in services/*_engine.py.
    SARVAM_API_KEY: str = Field(default="")
    SARVAM_BASE_URL: str = Field(default="https://api.sarvam.ai")
    VAPID_PRIVATE_KEY: str = Field(default="")
    VAPID_PUBLIC_KEY: str = Field(default="")
    VAPID_CLAIM_EMAIL: str = Field(default="admin@diafit.app")

    @field_validator("DATABASE_URL")
    @classmethod
    def _use_async_postgres_driver(cls, v: str) -> str:
        # Render/Heroku-style connection strings come as postgres:// or
        # postgresql://, but SQLAlchemy's async engine needs the asyncpg
        # driver spelled out explicitly.
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

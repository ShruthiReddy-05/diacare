import os, random
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


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
    TOGETHER_API_KEY: str = Field(default="")
    LLM_MODEL: str = Field(default="meta-llama/Llama-3.3-70B-Instruct-Turbo")
    LLM_TEMPERATURE: float = Field(default=0.1)
    LLM_MAX_TOKENS: int = Field(default=2048)
    SARVAM_API_KEY: str = Field(default="")
    SARVAM_BASE_URL: str = Field(default="https://api.sarvam.ai")
    VAPID_PRIVATE_KEY: str = Field(default="")
    VAPID_PUBLIC_KEY: str = Field(default="")
    VAPID_CLAIM_EMAIL: str = Field(default="admin@diafit.app")

    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_llm_model(self) -> str:
        models = [m.strip() for m in self.LLM_MODEL.split(",") if m.strip()]
        return random.choice(models)


settings = Settings()

"""DySub configuration loaded from environment and .env files."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global DySub settings.

    Reads from (in precedence order):
    1. Environment variables (prefix: DYSUB_)
    2. ~/.config/dysub/.env
    3. ./.env (current working directory)
    """

    model_config = SettingsConfigDict(
        env_prefix="DYSUB_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    asr_api_key: str = ""
    asr_base_url: str | None = None
    default_language: str = "zh"
    default_format: str = "srt"

    @classmethod
    def load(cls) -> Settings:
        """Load settings, checking multiple .env file locations."""
        env_files = [
            str(Path.home() / ".config" / "dysub" / ".env"),
            ".env",
        ]
        # Filter to existing files so pydantic-settings doesn't warn
        existing = [f for f in env_files if Path(f).exists()]
        return cls(_env_file=existing or None)

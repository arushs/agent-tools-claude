"""Configuration for the appointment booking demo."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Google Calendar
    google_credentials_path: str = "credentials.json"
    google_token_path: str = "token.json"
    google_calendar_id: str = "primary"

    # Claude settings
    claude_model: str = "claude-sonnet-4-20250514"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

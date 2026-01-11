"""Configuration for the appointment booking demo."""

from __future__ import annotations

from functools import lru_cache

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys (required - no defaults, must be set via environment)
    anthropic_api_key: str
    openai_api_key: str

    @field_validator("anthropic_api_key", "openai_api_key")
    @classmethod
    def validate_api_key_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """Validate that API keys are not empty strings."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must be set and non-empty")
        return v

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

    # WebSocket authentication
    # If set, clients must provide this token to connect to WebSocket endpoints
    # If empty, authentication is disabled (backwards compatible)
    websocket_auth_token: str = ""

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_http_per_minute: int = 60
    rate_limit_http_burst: int = 10
    rate_limit_ws_per_minute: int = 30
    rate_limit_ws_burst: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Settings are loaded from environment variables by pydantic-settings.
    """
    return Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env

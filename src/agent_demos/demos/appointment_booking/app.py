"""FastAPI application factory for the appointment booking demo."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from agent_demos.demos.appointment_booking.config import Settings, get_settings
from agent_demos.demos.appointment_booking.error_handlers import register_error_handlers
from agent_demos.demos.appointment_booking.rate_limit import (
    RateLimitConfig,
    RateLimiter,
    RateLimitMiddleware,
)
from agent_demos.demos.appointment_booking.routes import appointments, calendar, health
from agent_demos.demos.appointment_booking.services.chat_service import ChatService
from agent_demos.demos.appointment_booking.services.notification import NotificationService
from agent_demos.demos.appointment_booking.services.voice_service import VoiceService
from agent_demos.demos.appointment_booking.websocket.chat import chat_router
from agent_demos.demos.appointment_booking.websocket.manager import ConnectionManager
from agent_demos.demos.appointment_booking.websocket.voice import voice_router

if TYPE_CHECKING:
    from agent_demos.scheduling.agent import SchedulingAgent


def validate_startup_credentials(settings: Settings) -> None:
    """Validate all required credentials are present at startup.

    Raises:
        RuntimeError: If any required credentials are missing or invalid.
    """
    errors: list[str] = []

    # Check required API key
    if not settings.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY environment variable is required")

    # Warn if OpenAI key is missing (only needed for voice features)
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set - voice features (STT/TTS) will be disabled")

    # Warn if Google credentials file is missing (needed for calendar features)
    credentials_path = Path(settings.google_credentials_path)
    if not credentials_path.exists():
        logger.warning(
            "Google credentials file not found: %s - calendar features will be disabled",
            settings.google_credentials_path,
        )

    if errors:
        error_msg = "Startup validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info("All required credentials validated successfully")


class AppState:
    """Application state container for dependency injection."""

    def __init__(self, settings: Settings, rate_limiter: RateLimiter | None = None) -> None:
        self.settings = settings
        self.connection_manager = ConnectionManager()
        self.notification_service = NotificationService(self.connection_manager)
        self.rate_limiter = rate_limiter or RateLimiter(
            RateLimitConfig(
                http_requests_per_minute=settings.rate_limit_http_per_minute,
                http_burst_limit=settings.rate_limit_http_burst,
                ws_messages_per_minute=settings.rate_limit_ws_per_minute,
                ws_burst_limit=settings.rate_limit_ws_burst,
                enabled=settings.rate_limit_enabled,
            )
        )
        self._scheduling_agent: SchedulingAgent | None = None
        self._chat_service: ChatService | None = None
        self._voice_service: VoiceService | None = None

    @property
    def scheduling_agent(self) -> SchedulingAgent:
        """Lazy-initialize the scheduling agent."""
        if self._scheduling_agent is None:
            from agent_demos.scheduling.agent import SchedulingAgent

            self._scheduling_agent = SchedulingAgent(
                credentials_path=self.settings.google_credentials_path,
                token_path=self.settings.google_token_path,
                calendar_id=self.settings.google_calendar_id,
                api_key=self.settings.anthropic_api_key or None,
                model=self.settings.claude_model,
            )
        return self._scheduling_agent

    @property
    def chat_service(self) -> ChatService:
        """Lazy-initialize the chat service."""
        if self._chat_service is None:
            self._chat_service = ChatService(
                scheduling_agent=self.scheduling_agent,
                notification_service=self.notification_service,
            )
        return self._chat_service

    @property
    def voice_service(self) -> VoiceService:
        """Lazy-initialize the voice service."""
        if self._voice_service is None:
            self._voice_service = VoiceService(
                scheduling_agent=self.scheduling_agent,
                notification_service=self.notification_service,
                openai_api_key=self.settings.openai_api_key or None,
            )
        return self._voice_service


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override for testing.

    Returns:
        Configured FastAPI application.
    """
    settings = settings or get_settings()

    # Create rate limiter before app for middleware
    rate_limiter = RateLimiter(
        RateLimitConfig(
            http_requests_per_minute=settings.rate_limit_http_per_minute,
            http_burst_limit=settings.rate_limit_http_burst,
            ws_messages_per_minute=settings.rate_limit_ws_per_minute,
            ws_burst_limit=settings.rate_limit_ws_burst,
            enabled=settings.rate_limit_enabled,
        )
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan manager."""
        # Startup: Validate credentials and initialize application state
        validate_startup_credentials(settings)
        app.state.app_state = AppState(settings, rate_limiter)
        logger.info("Application started successfully")
        yield
        # Shutdown: Clean up resources
        await app.state.app_state.connection_manager.disconnect_all()
        logger.info("Application shutdown complete")

    app = FastAPI(
        title="Appointment Booking Demo",
        description="AI-powered appointment scheduling with Claude",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=rate_limiter,
    )

    # Register error handlers
    register_error_handlers(app)

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(appointments.router, prefix="/api", tags=["Appointments"])
    app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
    app.include_router(chat_router, prefix="/ws", tags=["WebSocket"])
    app.include_router(voice_router, prefix="/ws", tags=["WebSocket"])

    return app


# Default app instance for uvicorn
# Uses lazy initialization to avoid import-time settings validation
# This allows tests to import the module without having env vars set
_default_app: FastAPI | None = None


def get_app() -> FastAPI:
    """Get the default FastAPI application instance (lazy initialization).

    This function is used by uvicorn when running the server.
    Usage: uvicorn agent_demos.demos.appointment_booking.app:get_app --factory
    """
    global _default_app
    if _default_app is None:
        _default_app = create_app()
    return _default_app


def __getattr__(name: str) -> FastAPI:
    """Lazy initialization for module-level app attribute."""
    if name == "app":
        return get_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

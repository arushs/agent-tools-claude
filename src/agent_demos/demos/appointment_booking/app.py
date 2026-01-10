"""FastAPI application factory for the appointment booking demo."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_demos.demos.appointment_booking.config import Settings, get_settings
from agent_demos.demos.appointment_booking.routes import appointments, calendar, health
from agent_demos.demos.appointment_booking.services.chat_service import ChatService
from agent_demos.demos.appointment_booking.services.notification import NotificationService
from agent_demos.demos.appointment_booking.services.voice_service import VoiceService
from agent_demos.demos.appointment_booking.websocket.chat import chat_router
from agent_demos.demos.appointment_booking.websocket.manager import ConnectionManager
from agent_demos.demos.appointment_booking.websocket.voice import voice_router

if TYPE_CHECKING:
    from agent_demos.scheduling.agent import SchedulingAgent


class AppState:
    """Application state container for dependency injection."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.connection_manager = ConnectionManager()
        self.notification_service = NotificationService(self.connection_manager)
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

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan manager."""
        # Startup: Initialize application state
        app.state.app_state = AppState(settings)
        yield
        # Shutdown: Clean up resources
        await app.state.app_state.connection_manager.disconnect_all()

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

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(appointments.router, prefix="/api", tags=["Appointments"])
    app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
    app.include_router(chat_router, prefix="/ws", tags=["WebSocket"])
    app.include_router(voice_router, prefix="/ws", tags=["WebSocket"])

    return app


# Default app instance for uvicorn
app = create_app()

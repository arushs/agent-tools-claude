"""Pytest fixtures and mock implementations for the test suite."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from agent_demos.demos.appointment_booking.app import AppState, create_app
from agent_demos.demos.appointment_booking.config import Settings
from agent_demos.demos.appointment_booking.services.chat_service import ChatService
from agent_demos.demos.appointment_booking.services.notification import NotificationService
from agent_demos.demos.appointment_booking.services.voice_service import VoiceService
from agent_demos.demos.appointment_booking.websocket.manager import ConnectionManager


# =============================================================================
# Mock Implementations
# =============================================================================


class MockClaudeClient:
    """Mock implementation of ClaudeClient for testing."""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 4096
    MAX_TOOL_ITERATIONS = 10

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> None:
        """Initialize mock client."""
        self._api_key = api_key or "test-api-key"
        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        self._responses: list[str] = []
        self._call_count = 0

    def set_responses(self, responses: list[str]) -> None:
        """Set the responses to return."""
        self._responses = responses
        self._call_count = 0

    def create_message(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> MagicMock:
        """Mock create_message that returns preset responses."""
        response = MagicMock()
        if self._responses and self._call_count < len(self._responses):
            text = self._responses[self._call_count]
            self._call_count += 1
        else:
            text = "I can help you with that."

        text_block = MagicMock()
        text_block.text = text
        text_block.__class__.__name__ = "TextBlock"
        response.content = [text_block]
        response.stop_reason = "end_turn"
        return response

    async def create_message_async(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> MagicMock:
        """Async version of create_message."""
        return self.create_message(messages, system, tools, **kwargs)

    def process_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor: Any,
        system: str | None = None,
        max_iterations: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Mock tool processing."""
        if self._responses and self._call_count < len(self._responses):
            text = self._responses[self._call_count]
            self._call_count += 1
        else:
            text = "I can help you with that."

        conversation = list(messages)
        conversation.append({"role": "assistant", "content": text})
        return text, conversation

    async def process_with_tools_async(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor: Any,
        system: str | None = None,
        max_iterations: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Async version of process_with_tools."""
        return self.process_with_tools(
            messages, tools, tool_executor, system, max_iterations, **kwargs
        )

    def simple_chat(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Mock simple chat."""
        if self._responses and self._call_count < len(self._responses):
            text = self._responses[self._call_count]
            self._call_count += 1
            return text
        return "I can help you with that."

    async def simple_chat_async(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Async version of simple_chat."""
        return self.simple_chat(prompt, system, **kwargs)


class MockEvent:
    """Mock Google Calendar Event."""

    def __init__(
        self,
        id: str,
        title: str,
        start: datetime,
        end: datetime,
        attendees: list[str] | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> None:
        """Initialize mock event."""
        self.id = id
        self.title = title
        self.start = start
        self.end = end
        self.attendees = attendees or []
        self.description = description
        self.location = location

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "attendees": self.attendees,
            "description": self.description,
            "location": self.location,
        }


class MockTimeSlot:
    """Mock time slot."""

    def __init__(self, start: datetime, end: datetime) -> None:
        """Initialize mock time slot."""
        self.start = start
        self.end = end

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


class MockGoogleCalendarClient:
    """Mock implementation of GoogleCalendarClient for testing."""

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None,
        calendar_id: str = "primary",
    ) -> None:
        """Initialize mock calendar client."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.calendar_id = calendar_id
        self._events: dict[str, MockEvent] = {}
        self._event_counter = 0

    def list_events(
        self,
        start: datetime,
        end: datetime,
        max_results: int = 100,
    ) -> list[MockEvent]:
        """List events in date range."""
        result = []
        for event in self._events.values():
            if start <= event.start <= end or start <= event.end <= end:
                result.append(event)
        return result[:max_results]

    def get_event(self, event_id: str) -> MockEvent | None:
        """Get event by ID."""
        return self._events.get(event_id)

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        attendees: list[str] | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> MockEvent:
        """Create a new event."""
        self._event_counter += 1
        event_id = f"test-event-{self._event_counter}"
        event = MockEvent(
            id=event_id,
            title=title,
            start=start,
            end=end,
            attendees=attendees,
            description=description,
            location=location,
        )
        self._events[event_id] = event
        return event

    def cancel_event(self, event_id: str) -> bool:
        """Cancel an event."""
        if event_id in self._events:
            del self._events[event_id]
            return True
        return False

    def get_availability(
        self,
        start: datetime,
        end: datetime,
        slot_duration_minutes: int = 30,
    ) -> list[MockTimeSlot]:
        """Get available time slots."""
        # Return some mock available slots
        slots = []
        current = start
        while current < end:
            slot_end = current + timedelta(minutes=slot_duration_minutes)
            # Check if slot overlaps with any event
            is_free = True
            for event in self._events.values():
                if current < event.end and slot_end > event.start:
                    is_free = False
                    break
            if is_free:
                slots.append(MockTimeSlot(current, slot_end))
            current = slot_end
        return slots[:10]  # Limit for testing


class MockSchedulingAgent:
    """Mock implementation of SchedulingAgent for testing."""

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None,
        calendar_id: str = "primary",
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize mock agent."""
        self._calendar = MockGoogleCalendarClient(
            credentials_path=credentials_path,
            token_path=token_path,
            calendar_id=calendar_id,
        )
        self._claude = MockClaudeClient(api_key=api_key, model=model)
        self._response_text = "I can help you with that."

    @property
    def calendar(self) -> MockGoogleCalendarClient:
        """Get calendar client."""
        return self._calendar

    @property
    def tools(self) -> list[dict[str, Any]]:
        """Get tool definitions."""
        return []

    def set_response(self, response: str) -> None:
        """Set the response to return from chat methods."""
        self._response_text = response

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> str:
        """Process a message."""
        return self._response_text

    def chat_with_history(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Process a message with history."""
        conversation = list(history) if history else []
        conversation.append({"role": "user", "content": message})
        conversation.append({"role": "assistant", "content": self._response_text})
        return self._response_text, conversation

    async def chat_async(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> str:
        """Async version of chat."""
        return self._response_text

    async def chat_with_history_async(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Async version of chat_with_history."""
        return self.chat_with_history(message, history, system_prompt)


class MockWebSTT:
    """Mock implementation of WebSTT for testing."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize mock STT."""
        self._api_key = api_key
        self._transcription = "Hello, I would like to book an appointment."

    def set_transcription(self, text: str) -> None:
        """Set the transcription to return."""
        self._transcription = text

    def transcribe_base64(
        self,
        audio_base64: str,
        mime_type: str = "audio/webm",
        language: str | None = None,
    ) -> str:
        """Transcribe audio."""
        return self._transcription

    async def transcribe_base64_async(
        self,
        audio_base64: str,
        mime_type: str = "audio/webm",
        language: str | None = None,
    ) -> str:
        """Async version of transcribe_base64."""
        return self._transcription


class MockWebTTS:
    """Mock implementation of WebTTS for testing."""

    DEFAULT_WEB_FORMAT = "mp3"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        voice: str = "alloy",
    ) -> None:
        """Initialize mock TTS."""
        self._api_key = api_key
        self._voice = voice
        self._audio_base64 = "SGVsbG8gV29ybGQ="  # "Hello World" in base64

    def set_audio_response(self, audio_base64: str) -> None:
        """Set the audio response to return."""
        self._audio_base64 = audio_base64

    def synthesize_base64(
        self,
        text: str,
        voice: str | None = None,
        response_format: str | None = None,
        speed: float = 1.0,
    ) -> tuple[str, str]:
        """Synthesize audio."""
        return self._audio_base64, "audio/mpeg"

    async def synthesize_base64_async(
        self,
        text: str,
        voice: str | None = None,
        response_format: str | None = None,
        speed: float = 1.0,
    ) -> tuple[str, str]:
        """Async version of synthesize_base64."""
        return self._audio_base64, "audio/mpeg"

    @property
    def available_voices(self) -> list[str]:
        """Get available voices."""
        return ["alloy", "echo", "fable", "nova", "onyx", "shimmer"]


# =============================================================================
# Test Settings
# =============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        anthropic_api_key="test-anthropic-key",
        openai_api_key="test-openai-key",
        google_credentials_path="/tmp/test-credentials.json",
        google_token_path="/tmp/test-token.json",
        google_calendar_id="primary",
        cors_origins=["http://localhost:5173"],
        host="127.0.0.1",
        port=8000,
    )


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_claude() -> MockClaudeClient:
    """Create a mock Claude client."""
    return MockClaudeClient()


@pytest.fixture
def mock_calendar() -> MockGoogleCalendarClient:
    """Create a mock Google Calendar client."""
    return MockGoogleCalendarClient()


@pytest.fixture
def mock_scheduling_agent() -> MockSchedulingAgent:
    """Create a mock scheduling agent."""
    return MockSchedulingAgent()


@pytest.fixture
def mock_stt() -> MockWebSTT:
    """Create a mock STT client."""
    return MockWebSTT()


@pytest.fixture
def mock_tts() -> MockWebTTS:
    """Create a mock TTS client."""
    return MockWebTTS()


# =============================================================================
# Service Fixtures
# =============================================================================


@pytest.fixture
def connection_manager() -> ConnectionManager:
    """Create a connection manager."""
    return ConnectionManager()


@pytest.fixture
def notification_service(connection_manager: ConnectionManager) -> NotificationService:
    """Create a notification service."""
    return NotificationService(connection_manager)


@pytest.fixture
def chat_service(
    mock_scheduling_agent: MockSchedulingAgent,
    notification_service: NotificationService,
) -> ChatService:
    """Create a chat service with mocked dependencies."""
    return ChatService(
        scheduling_agent=mock_scheduling_agent,  # type: ignore
        notification_service=notification_service,
    )


@pytest.fixture
def voice_service(
    mock_scheduling_agent: MockSchedulingAgent,
    notification_service: NotificationService,
    mock_stt: MockWebSTT,
    mock_tts: MockWebTTS,
) -> VoiceService:
    """Create a voice service with mocked dependencies."""
    service = VoiceService(
        scheduling_agent=mock_scheduling_agent,  # type: ignore
        notification_service=notification_service,
        openai_api_key="test-key",
    )
    # Replace the STT and TTS with mocks
    service._stt = mock_stt  # type: ignore
    service._tts = mock_tts  # type: ignore
    return service


# =============================================================================
# App Fixtures
# =============================================================================


@pytest.fixture
def mock_app_state(
    test_settings: Settings,
    mock_scheduling_agent: MockSchedulingAgent,
    mock_stt: MockWebSTT,
    mock_tts: MockWebTTS,
) -> AppState:
    """Create a mock app state for testing."""
    app_state = AppState(test_settings)
    # Inject mock scheduling agent
    app_state._scheduling_agent = mock_scheduling_agent  # type: ignore

    # Create services with mocks
    app_state._chat_service = ChatService(
        scheduling_agent=mock_scheduling_agent,  # type: ignore
        notification_service=app_state.notification_service,
    )

    voice_service = VoiceService(
        scheduling_agent=mock_scheduling_agent,  # type: ignore
        notification_service=app_state.notification_service,
        openai_api_key="test-key",
    )
    voice_service._stt = mock_stt  # type: ignore
    voice_service._tts = mock_tts  # type: ignore
    app_state._voice_service = voice_service

    return app_state


@pytest.fixture
def app(mock_app_state: AppState, test_settings: Settings) -> FastAPI:
    """Create a test FastAPI application with mocked dependencies."""
    # Patch validate_startup_credentials to skip file existence checks in tests
    with patch(
        "agent_demos.demos.appointment_booking.app.validate_startup_credentials"
    ):
        test_app = create_app(test_settings)
        # Override the app state
        test_app.state.app_state = mock_app_state
        yield test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_event() -> MockEvent:
    """Create a sample event for testing."""
    now = datetime.utcnow()
    return MockEvent(
        id="test-event-1",
        title="Test Meeting",
        start=now + timedelta(hours=1),
        end=now + timedelta(hours=2),
        attendees=["test@example.com"],
        description="Test description",
        location="Test location",
    )


@pytest.fixture
def sample_events(sample_event: MockEvent) -> list[MockEvent]:
    """Create multiple sample events for testing."""
    now = datetime.utcnow()
    return [
        sample_event,
        MockEvent(
            id="test-event-2",
            title="Team Standup",
            start=now + timedelta(days=1),
            end=now + timedelta(days=1, minutes=30),
            attendees=["team@example.com"],
        ),
        MockEvent(
            id="test-event-3",
            title="Project Review",
            start=now + timedelta(days=2),
            end=now + timedelta(days=2, hours=1),
            attendees=["manager@example.com", "developer@example.com"],
        ),
    ]


@pytest.fixture
def sample_audio_base64() -> str:
    """Create sample base64 audio data."""
    # This is mock base64 audio data
    return "SGVsbG8sIHRoaXMgaXMgYSB0ZXN0IGF1ZGlvIGZpbGU="


# =============================================================================
# Utility Functions
# =============================================================================


def create_tool_result_history(success: bool = True) -> list[dict[str, Any]]:
    """Create a mock conversation history with tool results."""
    return [
        {"role": "user", "content": "Book a meeting for tomorrow at 2pm"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I'll book that meeting for you."},
                {
                    "type": "tool_use",
                    "id": "tool-123",
                    "name": "book_appointment",
                    "input": {"title": "Meeting", "start_time": "2025-01-11T14:00:00"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tool-123",
                    "content": json.dumps({"success": success}),
                },
            ],
        },
        {"role": "assistant", "content": "I've booked the meeting for tomorrow at 2pm."},
    ]

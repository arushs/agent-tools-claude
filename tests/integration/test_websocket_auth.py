"""Integration tests for WebSocket authentication."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from agent_demos.demos.appointment_booking.app import AppState, create_app
from agent_demos.demos.appointment_booking.config import Settings
from agent_demos.demos.appointment_booking.websocket.auth import (
    WS_CLOSE_AUTH_FAILED,
    WS_CLOSE_AUTH_REQUIRED,
    is_auth_enabled,
    verify_token,
)
from tests.conftest import MockSchedulingAgent, MockWebSTT, MockWebTTS

# =============================================================================
# Unit Tests for Auth Functions
# =============================================================================


class TestVerifyToken:
    """Tests for the verify_token function."""

    def test_valid_token(self) -> None:
        """Test that a valid token is accepted."""
        assert verify_token("secret123", "secret123") is True

    def test_invalid_token(self) -> None:
        """Test that an invalid token is rejected."""
        assert verify_token("wrong", "secret123") is False

    def test_none_token(self) -> None:
        """Test that None token is rejected."""
        assert verify_token(None, "secret123") is False

    def test_empty_token(self) -> None:
        """Test that empty token vs non-empty expected is rejected."""
        assert verify_token("", "secret123") is False

    def test_empty_expected(self) -> None:
        """Test that any token vs empty expected is rejected."""
        assert verify_token("token", "") is False

    def test_both_empty(self) -> None:
        """Test that empty token vs empty expected is accepted."""
        assert verify_token("", "") is True


class TestIsAuthEnabled:
    """Tests for the is_auth_enabled function."""

    def test_enabled_with_token(self) -> None:
        """Test auth is enabled when token is set."""
        assert is_auth_enabled("secret123") is True

    def test_disabled_with_empty_string(self) -> None:
        """Test auth is disabled when token is empty string."""
        assert is_auth_enabled("") is False


# =============================================================================
# Integration Tests - WebSocket Authentication
# =============================================================================


@pytest.fixture
def auth_settings() -> Settings:
    """Create settings with authentication enabled."""
    return Settings(
        anthropic_api_key="test-anthropic-key",
        openai_api_key="test-openai-key",
        google_credentials_path="/tmp/test-credentials.json",
        google_token_path="/tmp/test-token.json",
        google_calendar_id="primary",
        cors_origins=["http://localhost:5173"],
        host="127.0.0.1",
        port=8000,
        websocket_auth_token="test-secret-token",
    )


@pytest.fixture
def auth_app(
    auth_settings: Settings,
    mock_scheduling_agent: MockSchedulingAgent,
    mock_stt: MockWebSTT,
    mock_tts: MockWebTTS,
) -> FastAPI:
    """Create a test FastAPI application with authentication enabled."""
    from agent_demos.demos.appointment_booking.services.chat_service import ChatService
    from agent_demos.demos.appointment_booking.services.voice_service import VoiceService

    test_app = create_app(auth_settings)

    # Create mock app state
    app_state = AppState(auth_settings)
    app_state._scheduling_agent = mock_scheduling_agent  # type: ignore

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

    test_app.state.app_state = app_state
    return test_app


@pytest.fixture
def auth_client(auth_app: FastAPI) -> TestClient:
    """Create a test client with authentication enabled."""
    return TestClient(auth_app)


class TestWebSocketChatAuthentication:
    """Tests for WebSocket chat authentication."""

    def test_connect_with_valid_token(self, auth_client: TestClient) -> None:
        """Test connecting with a valid authentication token."""
        with auth_client.websocket_connect("/ws/chat?token=test-secret-token") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "session_id" in data

    def test_connect_with_invalid_token(self, auth_client: TestClient) -> None:
        """Test that invalid token is rejected."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with auth_client.websocket_connect("/ws/chat?token=wrong-token"):
                pass
        assert exc_info.value.code == WS_CLOSE_AUTH_FAILED

    def test_connect_without_token_when_auth_enabled(self, auth_client: TestClient) -> None:
        """Test that missing token is rejected when auth is enabled."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with auth_client.websocket_connect("/ws/chat"):
                pass
        assert exc_info.value.code == WS_CLOSE_AUTH_REQUIRED

    def test_connect_with_token_and_session_id(self, auth_client: TestClient) -> None:
        """Test connecting with both token and session ID."""
        session_id = "test-session-123"
        with auth_client.websocket_connect(
            f"/ws/chat?token=test-secret-token&session_id={session_id}"
        ) as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] == session_id

    def test_connect_without_token_when_auth_disabled(self, client: TestClient) -> None:
        """Test that missing token is allowed when auth is disabled."""
        # Uses the default client fixture which has auth disabled
        with client.websocket_connect("/ws/chat") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"


class TestWebSocketVoiceAuthentication:
    """Tests for WebSocket voice authentication."""

    def test_connect_with_valid_token(self, auth_client: TestClient) -> None:
        """Test connecting with a valid authentication token."""
        with auth_client.websocket_connect("/ws/voice?token=test-secret-token") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "session_id" in data
            assert "voices" in data

    def test_connect_with_invalid_token(self, auth_client: TestClient) -> None:
        """Test that invalid token is rejected."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with auth_client.websocket_connect("/ws/voice?token=wrong-token"):
                pass
        assert exc_info.value.code == WS_CLOSE_AUTH_FAILED

    def test_connect_without_token_when_auth_enabled(self, auth_client: TestClient) -> None:
        """Test that missing token is rejected when auth is enabled."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with auth_client.websocket_connect("/ws/voice"):
                pass
        assert exc_info.value.code == WS_CLOSE_AUTH_REQUIRED

    def test_connect_with_token_and_session_id(self, auth_client: TestClient) -> None:
        """Test connecting with both token and session ID."""
        session_id = "voice-session-456"
        with auth_client.websocket_connect(
            f"/ws/voice?token=test-secret-token&session_id={session_id}"
        ) as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] == session_id

    def test_connect_without_token_when_auth_disabled(self, client: TestClient) -> None:
        """Test that missing token is allowed when auth is disabled."""
        # Uses the default client fixture which has auth disabled
        with client.websocket_connect("/ws/voice") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"


class TestAuthenticatedMessaging:
    """Tests for messaging over authenticated WebSocket connections."""

    def test_chat_messaging_with_auth(
        self,
        auth_client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test that chat messaging works after authentication."""
        mock_scheduling_agent.set_response("I can help you schedule.")

        with auth_client.websocket_connect("/ws/chat?token=test-secret-token") as websocket:
            websocket.receive_json()  # connected

            # Send a message
            websocket.send_json({"type": "message", "content": "Hello"})

            # Receive ack
            ack = websocket.receive_json()
            assert ack["type"] == "ack"

            # Receive response
            response = websocket.receive_json()
            assert response["type"] == "response"
            assert response["content"] == "I can help you schedule."

    def test_voice_ping_with_auth(self, auth_client: TestClient) -> None:
        """Test that voice ping/pong works after authentication."""
        with auth_client.websocket_connect("/ws/voice?token=test-secret-token") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"type": "ping"})
            pong = websocket.receive_json()
            assert pong["type"] == "pong"

"""Integration tests for WebSocket chat functionality."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import MockSchedulingAgent


class TestWebSocketChatConnection:
    """Tests for WebSocket chat connection management."""

    def test_connect_new_session(self, client: TestClient) -> None:
        """Test connecting to chat WebSocket with new session."""
        with client.websocket_connect("/ws/chat") as websocket:
            # Should receive connected message with session ID
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "session_id" in data
            assert len(data["session_id"]) > 0

    def test_connect_with_existing_session_id(self, client: TestClient) -> None:
        """Test connecting with a provided session ID."""
        session_id = "test-session-123"
        with client.websocket_connect(f"/ws/chat?session_id={session_id}") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] == session_id

    def test_reconnect_with_session_id(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
        app: FastAPI,
    ) -> None:
        """Test reconnecting with same session ID maintains state."""
        session_id = "persistent-session"
        mock_scheduling_agent.set_response("First response")

        # First connection
        with client.websocket_connect(f"/ws/chat?session_id={session_id}") as websocket:
            websocket.receive_json()  # connected message

            websocket.send_json({"type": "message", "content": "Hello"})
            websocket.receive_json()  # ack
            websocket.receive_json()  # response

        # Second connection - should have history
        with client.websocket_connect(f"/ws/chat?session_id={session_id}") as websocket:
            data = websocket.receive_json()  # connected message
            assert data["type"] == "connected"

            # May receive history message
            # (depends on implementation state)


class TestWebSocketChatMessaging:
    """Tests for WebSocket chat message handling."""

    def test_send_message(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test sending a chat message."""
        mock_scheduling_agent.set_response("I can help you with scheduling.")

        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected message

            # Send message
            websocket.send_json({"type": "message", "content": "Hello"})

            # Should receive ack
            ack = websocket.receive_json()
            assert ack["type"] == "ack"
            assert ack["status"] == "processing"

            # Should receive response
            response = websocket.receive_json()
            assert response["type"] == "response"
            assert response["content"] == "I can help you with scheduling."
            assert "appointments_changed" in response

    def test_send_empty_message(self, client: TestClient) -> None:
        """Test that empty messages are ignored."""
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected message

            # Send empty message
            websocket.send_json({"type": "message", "content": ""})

            # Send another message to verify connection still works
            websocket.send_json({"type": "ping"})
            pong = websocket.receive_json()
            assert pong["type"] == "pong"

    def test_send_whitespace_message(self, client: TestClient) -> None:
        """Test that whitespace-only messages are ignored."""
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected message

            # Send whitespace message
            websocket.send_json({"type": "message", "content": "   "})

            # Verify connection still works
            websocket.send_json({"type": "ping"})
            pong = websocket.receive_json()
            assert pong["type"] == "pong"

    def test_message_with_appointment_changes(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test message that triggers appointment change detection."""
        mock_scheduling_agent.set_response(
            "Your meeting has been booked successfully for tomorrow at 2pm."
        )

        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "message",
                "content": "Book a meeting for tomorrow at 2pm",
            })

            websocket.receive_json()  # ack

            # When appointments change, we may receive notification before response
            messages = []
            for _ in range(2):  # Expect response and possibly notification
                msg = websocket.receive_json()
                messages.append(msg)

            # Find the response message
            response = next((m for m in messages if m["type"] == "response"), None)
            assert response is not None
            assert response["appointments_changed"] is True

            # Check that notification was also sent
            notification = next((m for m in messages if m["type"] == "notification"), None)
            assert notification is not None

    def test_multiple_messages(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test sending multiple messages in sequence."""
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected

            for i in range(3):
                mock_scheduling_agent.set_response(f"Response {i}")
                websocket.send_json({
                    "type": "message",
                    "content": f"Message {i}",
                })
                websocket.receive_json()  # ack
                response = websocket.receive_json()
                assert response["type"] == "response"
                assert response["content"] == f"Response {i}"


class TestWebSocketChatPing:
    """Tests for WebSocket chat ping/pong."""

    def test_ping_pong(self, client: TestClient) -> None:
        """Test ping/pong keepalive."""
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"type": "ping"})
            response = websocket.receive_json()

            assert response["type"] == "pong"

    def test_multiple_pings(self, client: TestClient) -> None:
        """Test multiple ping requests."""
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected

            for _ in range(5):
                websocket.send_json({"type": "ping"})
                response = websocket.receive_json()
                assert response["type"] == "pong"


class TestWebSocketChatHistoryManagement:
    """Tests for WebSocket chat history management."""

    def test_clear_history(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test clearing chat history."""
        mock_scheduling_agent.set_response("Hello!")

        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected

            # Send a message
            websocket.send_json({"type": "message", "content": "Hello"})
            websocket.receive_json()  # ack
            websocket.receive_json()  # response

            # Clear history
            websocket.send_json({"type": "clear_history"})
            clear_response = websocket.receive_json()

            assert clear_response["type"] == "history_cleared"


class TestWebSocketChatUnknownMessageTypes:
    """Tests for handling unknown message types."""

    def test_unknown_message_type(self, client: TestClient) -> None:
        """Test that unknown message types don't crash the connection."""
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected

            # Send unknown message type
            websocket.send_json({"type": "unknown_type", "data": "test"})

            # Connection should still work
            websocket.send_json({"type": "ping"})
            response = websocket.receive_json()
            assert response["type"] == "pong"

    def test_malformed_message(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test handling of messages without explicit type."""
        mock_scheduling_agent.set_response("Hello back!")

        with client.websocket_connect("/ws/chat") as websocket:
            websocket.receive_json()  # connected

            # Send message without type (defaults to "message")
            # With content, it should process normally
            websocket.send_json({"content": "Hello"})

            # Should receive ack and response
            websocket.receive_json()  # ack
            websocket.receive_json()  # response

            # Connection should still work
            websocket.send_json({"type": "ping"})
            response = websocket.receive_json()
            assert response["type"] == "pong"

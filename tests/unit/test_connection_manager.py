"""Unit tests for ConnectionManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_demos.demos.appointment_booking.websocket.manager import ConnectionManager


class TestConnectionManagerInit:
    """Tests for ConnectionManager initialization."""

    def test_init(self) -> None:
        """Test manager initialization."""
        manager = ConnectionManager()
        assert manager._connections == {}
        assert manager._session_history == {}
        assert manager.active_connections == 0


class TestConnect:
    """Tests for connect method."""

    @pytest.mark.asyncio
    async def test_connect_new_session(self) -> None:
        """Test connecting with new session."""
        manager = ConnectionManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        session_id = await manager.connect(websocket)

        assert len(session_id) > 0
        assert session_id in manager._connections
        assert session_id in manager._session_history
        websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_session_id(self) -> None:
        """Test connecting with provided session ID."""
        manager = ConnectionManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        session_id = await manager.connect(websocket, "test-session")

        assert session_id == "test-session"
        assert "test-session" in manager._connections

    @pytest.mark.asyncio
    async def test_connect_preserves_history(self) -> None:
        """Test that reconnecting preserves history."""
        manager = ConnectionManager()
        websocket1 = MagicMock()
        websocket1.accept = AsyncMock()

        # First connection
        session_id = await manager.connect(websocket1, "test-session")
        manager.add_to_history(session_id, {"role": "user", "content": "Hi"})

        # Disconnect
        manager.disconnect(session_id)

        # Reconnect
        websocket2 = MagicMock()
        websocket2.accept = AsyncMock()
        await manager.connect(websocket2, "test-session")

        # History should be preserved
        history = manager.get_history("test-session")
        assert len(history) == 1


class TestDisconnect:
    """Tests for disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnecting a session."""
        manager = ConnectionManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        session_id = await manager.connect(websocket, "test-session")
        manager.disconnect(session_id)

        assert session_id not in manager._connections
        assert manager.active_connections == 0

    def test_disconnect_nonexistent(self) -> None:
        """Test disconnecting non-existent session doesn't raise."""
        manager = ConnectionManager()
        manager.disconnect("nonexistent")  # Should not raise


class TestDisconnectAll:
    """Tests for disconnect_all method."""

    @pytest.mark.asyncio
    async def test_disconnect_all(self) -> None:
        """Test disconnecting all sessions."""
        manager = ConnectionManager()

        # Connect multiple
        for i in range(3):
            ws = MagicMock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            await manager.connect(ws, f"session-{i}")

        await manager.disconnect_all()

        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_disconnect_all_handles_errors(self) -> None:
        """Test disconnect_all handles close errors gracefully."""
        manager = ConnectionManager()

        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock(side_effect=Exception("Close failed"))
        await manager.connect(ws, "test-session")

        # Should not raise
        await manager.disconnect_all()


class TestHistory:
    """Tests for history management."""

    def test_get_history_empty(self) -> None:
        """Test getting history for non-existent session."""
        manager = ConnectionManager()
        history = manager.get_history("nonexistent")
        assert history == []

    @pytest.mark.asyncio
    async def test_add_to_history(self) -> None:
        """Test adding to history."""
        manager = ConnectionManager()
        ws = MagicMock()
        ws.accept = AsyncMock()
        await manager.connect(ws, "test-session")

        manager.add_to_history("test-session", {"role": "user", "content": "Hi"})
        manager.add_to_history("test-session", {"role": "assistant", "content": "Hello"})

        history = manager.get_history("test-session")
        assert len(history) == 2

    def test_add_to_history_new_session(self) -> None:
        """Test adding to history for new session creates it."""
        manager = ConnectionManager()
        manager.add_to_history("new-session", {"role": "user", "content": "Hi"})

        history = manager.get_history("new-session")
        assert len(history) == 1

    def test_clear_history(self) -> None:
        """Test clearing history."""
        manager = ConnectionManager()
        manager.add_to_history("test-session", {"role": "user", "content": "Hi"})
        manager.clear_history("test-session")

        history = manager.get_history("test-session")
        assert history == []


class TestSendMessage:
    """Tests for send_message method."""

    @pytest.mark.asyncio
    async def test_send_message_success(self) -> None:
        """Test sending message to connected client."""
        manager = ConnectionManager()
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        await manager.connect(ws, "test-session")
        result = await manager.send_message("test-session", {"type": "test"})

        assert result is True
        ws.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_message_not_found(self) -> None:
        """Test sending message to non-existent session."""
        manager = ConnectionManager()
        result = await manager.send_message("nonexistent", {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_error_disconnects(self) -> None:
        """Test that send errors disconnect the client."""
        manager = ConnectionManager()
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock(side_effect=Exception("Send failed"))

        await manager.connect(ws, "test-session")
        result = await manager.send_message("test-session", {"type": "test"})

        assert result is False
        assert manager.active_connections == 0


class TestBroadcast:
    """Tests for broadcast method."""

    @pytest.mark.asyncio
    async def test_broadcast(self) -> None:
        """Test broadcasting to all clients."""
        manager = ConnectionManager()

        websockets = []
        for i in range(3):
            ws = MagicMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await manager.connect(ws, f"session-{i}")
            websockets.append(ws)

        await manager.broadcast({"type": "notification"})

        for ws in websockets:
            ws.send_json.assert_called_once_with({"type": "notification"})

    @pytest.mark.asyncio
    async def test_broadcast_handles_errors(self) -> None:
        """Test broadcast handles individual client errors."""
        manager = ConnectionManager()

        # Good client
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        await manager.connect(ws1, "session-1")

        # Bad client
        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock(side_effect=Exception("Send failed"))
        await manager.connect(ws2, "session-2")

        await manager.broadcast({"type": "notification"})

        # Good client should have received message
        ws1.send_json.assert_called_once()
        # Bad client should be disconnected
        assert "session-2" not in manager._connections
        assert manager.active_connections == 1


class TestActiveConnections:
    """Tests for active_connections property."""

    @pytest.mark.asyncio
    async def test_active_connections(self) -> None:
        """Test active connections count."""
        manager = ConnectionManager()
        assert manager.active_connections == 0

        for i in range(5):
            ws = MagicMock()
            ws.accept = AsyncMock()
            await manager.connect(ws, f"session-{i}")
            assert manager.active_connections == i + 1

        manager.disconnect("session-0")
        assert manager.active_connections == 4

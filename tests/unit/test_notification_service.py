"""Unit tests for NotificationService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_demos.demos.appointment_booking.services.notification import NotificationService
from agent_demos.demos.appointment_booking.websocket.manager import ConnectionManager


class TestNotificationServiceInit:
    """Tests for NotificationService initialization."""

    def test_init(self) -> None:
        """Test service initialization."""
        manager = ConnectionManager()
        service = NotificationService(manager)
        assert service._manager == manager


class TestBroadcast:
    """Tests for broadcast method."""

    @pytest.mark.asyncio
    async def test_broadcast(self) -> None:
        """Test broadcasting a notification."""
        manager = MagicMock()
        manager.broadcast = AsyncMock()

        service = NotificationService(manager)
        await service.broadcast("test_event", {"key": "value"})

        manager.broadcast.assert_called_once_with({
            "type": "notification",
            "event": "test_event",
            "data": {"key": "value"},
        })


class TestBroadcastAppointmentCreated:
    """Tests for broadcast_appointment_created method."""

    @pytest.mark.asyncio
    async def test_broadcast_appointment_created(self) -> None:
        """Test broadcasting appointment created event."""
        manager = MagicMock()
        manager.broadcast = AsyncMock()

        service = NotificationService(manager)
        appointment = {"id": "123", "title": "Test Meeting"}
        await service.broadcast_appointment_created(appointment)

        manager.broadcast.assert_called_once_with({
            "type": "notification",
            "event": "appointment_created",
            "data": {"id": "123", "title": "Test Meeting"},
        })


class TestBroadcastAppointmentCancelled:
    """Tests for broadcast_appointment_cancelled method."""

    @pytest.mark.asyncio
    async def test_broadcast_appointment_cancelled(self) -> None:
        """Test broadcasting appointment cancelled event."""
        manager = MagicMock()
        manager.broadcast = AsyncMock()

        service = NotificationService(manager)
        await service.broadcast_appointment_cancelled({"id": "123"})

        manager.broadcast.assert_called_once_with({
            "type": "notification",
            "event": "appointment_cancelled",
            "data": {"id": "123"},
        })


class TestBroadcastAppointmentUpdated:
    """Tests for broadcast_appointment_updated method."""

    @pytest.mark.asyncio
    async def test_broadcast_appointment_updated(self) -> None:
        """Test broadcasting appointment updated event."""
        manager = MagicMock()
        manager.broadcast = AsyncMock()

        service = NotificationService(manager)
        appointment = {"id": "123", "title": "Updated Meeting"}
        await service.broadcast_appointment_updated(appointment)

        manager.broadcast.assert_called_once_with({
            "type": "notification",
            "event": "appointment_updated",
            "data": {"id": "123", "title": "Updated Meeting"},
        })


class TestNotifySession:
    """Tests for notify_session method."""

    @pytest.mark.asyncio
    async def test_notify_session_success(self) -> None:
        """Test notifying a specific session."""
        manager = MagicMock()
        manager.send_message = AsyncMock(return_value=True)

        service = NotificationService(manager)
        result = await service.notify_session(
            "session-123",
            "custom_event",
            {"message": "Hello"},
        )

        assert result is True
        manager.send_message.assert_called_once_with(
            "session-123",
            {
                "type": "notification",
                "event": "custom_event",
                "data": {"message": "Hello"},
            },
        )

    @pytest.mark.asyncio
    async def test_notify_session_not_found(self) -> None:
        """Test notifying non-existent session."""
        manager = MagicMock()
        manager.send_message = AsyncMock(return_value=False)

        service = NotificationService(manager)
        result = await service.notify_session(
            "nonexistent",
            "test_event",
            {},
        )

        assert result is False

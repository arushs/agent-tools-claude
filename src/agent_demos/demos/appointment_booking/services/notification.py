"""Notification service for real-time updates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.websocket.manager import ConnectionManager


class NotificationService:
    """Service for broadcasting real-time notifications."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """Initialize the notification service.

        Args:
            connection_manager: WebSocket connection manager.
        """
        self._manager = connection_manager

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        """Broadcast a notification to all connected clients.

        Args:
            event: Event type name.
            data: Event data payload.
        """
        await self._manager.broadcast({
            "type": "notification",
            "event": event,
            "data": data,
        })

    async def broadcast_appointment_created(self, appointment: dict[str, Any]) -> None:
        """Broadcast that an appointment was created.

        Args:
            appointment: The created appointment data.
        """
        await self.broadcast("appointment_created", appointment)

    async def broadcast_appointment_cancelled(self, data: dict[str, Any]) -> None:
        """Broadcast that an appointment was cancelled.

        Args:
            data: Data containing at least the appointment ID.
        """
        await self.broadcast("appointment_cancelled", data)

    async def broadcast_appointment_updated(self, appointment: dict[str, Any]) -> None:
        """Broadcast that an appointment was updated.

        Args:
            appointment: The updated appointment data.
        """
        await self.broadcast("appointment_updated", appointment)

    async def notify_session(
        self,
        session_id: str,
        event: str,
        data: dict[str, Any],
    ) -> bool:
        """Send a notification to a specific session.

        Args:
            session_id: Target session ID.
            event: Event type name.
            data: Event data payload.

        Returns:
            True if notification was sent successfully.
        """
        return await self._manager.send_message(session_id, {
            "type": "notification",
            "event": event,
            "data": data,
        })

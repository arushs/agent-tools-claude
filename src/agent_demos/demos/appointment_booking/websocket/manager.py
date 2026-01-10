"""WebSocket connection manager."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self._connections: dict[str, WebSocket] = {}
        self._session_history: dict[str, list[dict[str, Any]]] = {}

    async def connect(self, websocket: WebSocket, session_id: str | None = None) -> str:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            session_id: Optional session ID for reconnection.

        Returns:
            The session ID for this connection.
        """
        await websocket.accept()
        session_id = session_id or str(uuid.uuid4())
        self._connections[session_id] = websocket

        if session_id not in self._session_history:
            self._session_history[session_id] = []

        return session_id

    def disconnect(self, session_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            session_id: The session ID to disconnect.
        """
        self._connections.pop(session_id, None)

    async def disconnect_all(self) -> None:
        """Disconnect all WebSocket connections."""
        for session_id in list(self._connections.keys()):
            try:
                websocket = self._connections.pop(session_id, None)
                if websocket:
                    await websocket.close()
            except Exception:
                pass

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get conversation history for a session.

        Args:
            session_id: The session ID.

        Returns:
            List of message history for the session.
        """
        return self._session_history.get(session_id, [])

    def add_to_history(self, session_id: str, message: dict[str, Any]) -> None:
        """Add a message to session history.

        Args:
            session_id: The session ID.
            message: The message to add.
        """
        if session_id not in self._session_history:
            self._session_history[session_id] = []
        self._session_history[session_id].append(message)

    def clear_history(self, session_id: str) -> None:
        """Clear conversation history for a session.

        Args:
            session_id: The session ID.
        """
        self._session_history[session_id] = []

    async def send_message(self, session_id: str, message: dict[str, Any]) -> bool:
        """Send a message to a specific connection.

        Args:
            session_id: The session ID.
            message: The message to send.

        Returns:
            True if message was sent, False if connection not found.
        """
        websocket = self._connections.get(session_id)
        if websocket:
            try:
                await websocket.send_json(message)
                return True
            except Exception:
                self.disconnect(session_id)
        return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast.
        """
        disconnected = []
        for session_id, websocket in self._connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(session_id)

        # Clean up disconnected clients
        for session_id in disconnected:
            self.disconnect(session_id)

    @property
    def active_connections(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

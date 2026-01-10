"""Chat service for orchestrating conversations with Claude."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.services.notification import (
        NotificationService,
    )
    from agent_demos.scheduling.agent import SchedulingAgent


class ChatService:
    """Service for handling chat conversations with scheduling capabilities."""

    def __init__(
        self,
        scheduling_agent: SchedulingAgent,
        notification_service: NotificationService,
    ) -> None:
        """Initialize the chat service.

        Args:
            scheduling_agent: The scheduling agent for calendar operations.
            notification_service: Service for broadcasting notifications.
        """
        self._agent = scheduling_agent
        self._notifications = notification_service
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def _detect_appointment_changes(
        self,
        response: str,
        history: list[dict[str, Any]],
    ) -> bool:
        """Detect if the conversation resulted in appointment changes.

        Looks at tool results in history for booking/cancellation operations.

        Args:
            response: The assistant's response.
            history: The conversation history.

        Returns:
            True if appointments were modified.
        """
        change_indicators = [
            "booked successfully",
            "has been canceled",
            "appointment created",
            "appointment cancelled",
            "scheduled for",
            "I've booked",
            "I've scheduled",
            "I've canceled",
            "I've cancelled",
        ]

        response_lower = response.lower()
        for indicator in change_indicators:
            if indicator in response_lower:
                return True

        # Also check tool results in history for direct confirmation
        for msg in history:
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            result_content = block.get("content", "")
                            if isinstance(result_content, str):
                                try:
                                    result_data = json.loads(result_content)
                                    if result_data.get("success"):
                                        return True
                                except (json.JSONDecodeError, TypeError):
                                    pass

        return False

    async def process_message(
        self,
        session_id: str,
        message: str,
    ) -> tuple[str, bool]:
        """Process a user message and return Claude's response.

        Args:
            session_id: The session ID for conversation tracking.
            message: The user's message.

        Returns:
            Tuple of (response text, whether appointments changed).
        """
        # Get or initialize session history
        history = self._sessions.get(session_id, [])

        # Process with the scheduling agent
        response, updated_history = await self._agent.chat_with_history_async(
            message=message,
            history=history,
        )

        # Store updated history
        self._sessions[session_id] = updated_history

        # Check if appointments were modified
        appointments_changed = self._detect_appointment_changes(response, updated_history)

        # If appointments changed, broadcast notification
        if appointments_changed:
            await self._notifications.broadcast("appointments_changed", {
                "session_id": session_id,
                "message": "Calendar updated",
            })

        return response, appointments_changed

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get conversation history for a session.

        Args:
            session_id: The session ID.

        Returns:
            List of messages in the conversation.
        """
        return self._sessions.get(session_id, [])

    def clear_history(self, session_id: str) -> None:
        """Clear conversation history for a session.

        Args:
            session_id: The session ID.
        """
        self._sessions.pop(session_id, None)

    def format_history_for_client(self, session_id: str) -> list[dict[str, str]]:
        """Format conversation history for client display.

        Simplifies the internal message format for UI rendering.

        Args:
            session_id: The session ID.

        Returns:
            List of simplified messages with role and content.
        """
        history = self._sessions.get(session_id, [])
        formatted: list[dict[str, str]] = []

        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Handle simple string content
            if isinstance(content, str) and content.strip():
                formatted.append({"role": role, "content": content})
            # Handle structured content (extract text blocks)
            elif isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                if text_parts:
                    formatted.append({"role": role, "content": " ".join(text_parts)})

        return formatted

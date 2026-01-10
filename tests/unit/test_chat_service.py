"""Unit tests for ChatService."""

from __future__ import annotations

import json
from typing import Any

import pytest

from agent_demos.demos.appointment_booking.services.chat_service import ChatService
from tests.conftest import MockSchedulingAgent, create_tool_result_history


class TestChatServiceInit:
    """Tests for ChatService initialization."""

    def test_init(
        self,
        mock_scheduling_agent: MockSchedulingAgent,
        notification_service: Any,
    ) -> None:
        """Test ChatService initialization."""
        service = ChatService(
            scheduling_agent=mock_scheduling_agent,  # type: ignore
            notification_service=notification_service,
        )
        assert service._agent == mock_scheduling_agent
        assert service._notifications == notification_service
        assert service._sessions == {}


class TestDetectAppointmentChanges:
    """Tests for _detect_appointment_changes method."""

    def test_detect_booked_successfully(self, chat_service: ChatService) -> None:
        """Test detection of 'booked successfully' in response."""
        result = chat_service._detect_appointment_changes(
            "Your meeting has been booked successfully.",
            [],
        )
        assert result is True

    def test_detect_has_been_canceled(self, chat_service: ChatService) -> None:
        """Test detection of 'has been canceled' in response."""
        result = chat_service._detect_appointment_changes(
            "Your appointment has been canceled.",
            [],
        )
        assert result is True

    def test_detect_scheduled_for(self, chat_service: ChatService) -> None:
        """Test detection of 'scheduled for' in response."""
        result = chat_service._detect_appointment_changes(
            "I've scheduled for tomorrow at 2pm.",
            [],
        )
        assert result is True

    def test_detect_appointment_created(self, chat_service: ChatService) -> None:
        """Test detection of 'appointment created' in response."""
        result = chat_service._detect_appointment_changes(
            "Your appointment created successfully.",
            [],
        )
        assert result is True

    def test_detect_appointment_cancelled(self, chat_service: ChatService) -> None:
        """Test detection of 'appointment cancelled' in response."""
        result = chat_service._detect_appointment_changes(
            "Your appointment cancelled per your request.",
            [],
        )
        assert result is True

    def test_detect_has_been_canceled_alt(self, chat_service: ChatService) -> None:
        """Test detection of 'has been canceled' in response."""
        result = chat_service._detect_appointment_changes(
            "The meeting has been canceled.",
            [],
        )
        assert result is True

    def test_no_changes_detected(self, chat_service: ChatService) -> None:
        """Test when no appointment changes are detected."""
        result = chat_service._detect_appointment_changes(
            "I can help you check your availability.",
            [],
        )
        assert result is False

    def test_case_insensitive(self, chat_service: ChatService) -> None:
        """Test that detection is case-insensitive."""
        result = chat_service._detect_appointment_changes(
            "YOUR MEETING HAS BEEN BOOKED SUCCESSFULLY!",
            [],
        )
        assert result is True

    def test_detect_from_tool_results_success(self, chat_service: ChatService) -> None:
        """Test detection from successful tool results in history."""
        history: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-123",
                        "content": json.dumps({"success": True}),
                    }
                ],
            }
        ]
        result = chat_service._detect_appointment_changes(
            "Let me know if you need anything else.",
            history,
        )
        assert result is True

    def test_detect_from_tool_results_failure(self, chat_service: ChatService) -> None:
        """Test no detection from failed tool results."""
        history: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-123",
                        "content": json.dumps({"success": False}),
                    }
                ],
            }
        ]
        result = chat_service._detect_appointment_changes(
            "There was an error.",
            history,
        )
        assert result is False

    def test_handle_invalid_json_in_tool_results(self, chat_service: ChatService) -> None:
        """Test handling of invalid JSON in tool results."""
        history: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-123",
                        "content": "not valid json",
                    }
                ],
            }
        ]
        result = chat_service._detect_appointment_changes(
            "Something happened.",
            history,
        )
        assert result is False

    def test_handle_non_list_content(self, chat_service: ChatService) -> None:
        """Test handling of non-list content in history."""
        history: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": "Just a string message",
            }
        ]
        result = chat_service._detect_appointment_changes(
            "Okay.",
            history,
        )
        assert result is False


class TestProcessMessage:
    """Tests for process_message method."""

    @pytest.mark.asyncio
    async def test_process_message_new_session(
        self,
        chat_service: ChatService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test processing message with new session."""
        mock_scheduling_agent.set_response("I can help you with scheduling.")

        response, changed = await chat_service.process_message(
            session_id="new-session",
            message="Hello, I need to book a meeting.",
        )

        assert response == "I can help you with scheduling."
        assert changed is False
        assert "new-session" in chat_service._sessions

    @pytest.mark.asyncio
    async def test_process_message_existing_session(
        self,
        chat_service: ChatService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test processing message with existing session."""
        # First message
        mock_scheduling_agent.set_response("Hello! How can I help?")
        await chat_service.process_message(
            session_id="existing-session",
            message="Hi",
        )

        # Second message
        mock_scheduling_agent.set_response("I'll check your calendar.")
        response, _ = await chat_service.process_message(
            session_id="existing-session",
            message="What's my schedule?",
        )

        assert response == "I'll check your calendar."
        # Session history should have messages
        history = chat_service._sessions.get("existing-session", [])
        assert len(history) > 0

    @pytest.mark.asyncio
    async def test_process_message_detects_booking(
        self,
        chat_service: ChatService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test that booking is detected in response."""
        mock_scheduling_agent.set_response(
            "Your meeting has been booked successfully for tomorrow at 2pm."
        )

        response, changed = await chat_service.process_message(
            session_id="test-session",
            message="Book a meeting for tomorrow at 2pm",
        )

        assert changed is True


class TestGetHistory:
    """Tests for get_history method."""

    def test_get_history_empty(self, chat_service: ChatService) -> None:
        """Test getting history for non-existent session."""
        history = chat_service.get_history("non-existent")
        assert history == []

    @pytest.mark.asyncio
    async def test_get_history_with_messages(
        self,
        chat_service: ChatService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test getting history after messages."""
        await chat_service.process_message(
            session_id="test-session",
            message="Hello",
        )

        history = chat_service.get_history("test-session")
        assert len(history) > 0


class TestClearHistory:
    """Tests for clear_history method."""

    @pytest.mark.asyncio
    async def test_clear_history(
        self,
        chat_service: ChatService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test clearing session history."""
        # Create some history
        await chat_service.process_message(
            session_id="test-session",
            message="Hello",
        )
        assert len(chat_service.get_history("test-session")) > 0

        # Clear it
        chat_service.clear_history("test-session")
        assert chat_service.get_history("test-session") == []

    def test_clear_non_existent_session(self, chat_service: ChatService) -> None:
        """Test clearing non-existent session doesn't raise error."""
        chat_service.clear_history("non-existent")  # Should not raise


class TestFormatHistoryForClient:
    """Tests for format_history_for_client method."""

    def test_format_empty_history(self, chat_service: ChatService) -> None:
        """Test formatting empty history."""
        formatted = chat_service.format_history_for_client("non-existent")
        assert formatted == []

    @pytest.mark.asyncio
    async def test_format_simple_history(
        self,
        chat_service: ChatService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test formatting simple string content history."""
        mock_scheduling_agent.set_response("Hello! How can I help?")
        await chat_service.process_message(
            session_id="test-session",
            message="Hi there",
        )

        formatted = chat_service.format_history_for_client("test-session")
        assert len(formatted) >= 1
        # Should have role and content
        for msg in formatted:
            assert "role" in msg
            assert "content" in msg

    def test_format_structured_content(self, chat_service: ChatService) -> None:
        """Test formatting structured content with text blocks."""
        # Manually add structured content to session
        chat_service._sessions["test-session"] = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Part 1"},
                    {"type": "text", "text": "Part 2"},
                ],
            }
        ]

        formatted = chat_service.format_history_for_client("test-session")
        assert len(formatted) == 1
        assert formatted[0]["role"] == "assistant"
        assert "Part 1" in formatted[0]["content"]
        assert "Part 2" in formatted[0]["content"]

    def test_format_filters_empty_content(self, chat_service: ChatService) -> None:
        """Test that empty content is filtered out."""
        chat_service._sessions["test-session"] = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "Valid response"},
            {"role": "user", "content": "   "},  # Whitespace only
        ]

        formatted = chat_service.format_history_for_client("test-session")
        assert len(formatted) == 1
        assert formatted[0]["content"] == "Valid response"

    def test_format_filters_tool_blocks(self, chat_service: ChatService) -> None:
        """Test that tool use blocks are not included."""
        chat_service._sessions["test-session"] = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check."},
                    {"type": "tool_use", "id": "123", "name": "check_calendar"},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "123", "content": "{}"},
                ],
            },
        ]

        formatted = chat_service.format_history_for_client("test-session")
        # Should only have the text content
        assert len(formatted) == 1
        assert "Let me check." in formatted[0]["content"]

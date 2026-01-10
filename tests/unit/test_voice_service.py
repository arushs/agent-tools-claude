"""Unit tests for VoiceService."""

from __future__ import annotations

from typing import Any

import pytest

from agent_demos.demos.appointment_booking.services.voice_service import VoiceService
from tests.conftest import MockSchedulingAgent, MockWebSTT, MockWebTTS


class TestVoiceServiceInit:
    """Tests for VoiceService initialization."""

    def test_init(
        self,
        mock_scheduling_agent: MockSchedulingAgent,
        notification_service: Any,
    ) -> None:
        """Test VoiceService initialization."""
        service = VoiceService(
            scheduling_agent=mock_scheduling_agent,  # type: ignore
            notification_service=notification_service,
            openai_api_key="test-key",
        )
        assert service._agent == mock_scheduling_agent
        assert service._notifications == notification_service
        assert service._sessions == {}

    def test_default_voice(self) -> None:
        """Test default voice setting."""
        # Test the class constant
        assert VoiceService.DEFAULT_VOICE == "nova"


class TestProcessVoice:
    """Tests for process_voice method."""

    @pytest.mark.asyncio
    async def test_process_voice_success(
        self,
        voice_service: VoiceService,
        mock_stt: MockWebSTT,
        mock_tts: MockWebTTS,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test successful voice processing pipeline."""
        mock_stt.set_transcription("Book a meeting for tomorrow")
        mock_scheduling_agent.set_response("I'll book that meeting for you.")

        transcribed, response, audio, changed = await voice_service.process_voice(
            session_id="test-session",
            audio_base64="SGVsbG8gV29ybGQ=",
            mime_type="audio/webm",
        )

        assert transcribed == "Book a meeting for tomorrow"
        assert response == "I'll book that meeting for you."
        assert audio == mock_tts._audio_base64
        assert changed is False

    @pytest.mark.asyncio
    async def test_process_voice_empty_transcription(
        self,
        voice_service: VoiceService,
        mock_stt: MockWebSTT,
    ) -> None:
        """Test handling of empty transcription."""
        mock_stt.set_transcription("")

        transcribed, response, audio, changed = await voice_service.process_voice(
            session_id="test-session",
            audio_base64="SGVsbG8gV29ybGQ=",
        )

        assert transcribed == ""
        assert response == "I didn't catch that. Could you try again?"
        assert audio == ""
        assert changed is False

    @pytest.mark.asyncio
    async def test_process_voice_whitespace_transcription(
        self,
        voice_service: VoiceService,
        mock_stt: MockWebSTT,
    ) -> None:
        """Test handling of whitespace-only transcription."""
        mock_stt.set_transcription("   ")

        transcribed, response, audio, changed = await voice_service.process_voice(
            session_id="test-session",
            audio_base64="SGVsbG8gV29ybGQ=",
        )

        assert response == "I didn't catch that. Could you try again?"

    @pytest.mark.asyncio
    async def test_process_voice_detects_booking(
        self,
        voice_service: VoiceService,
        mock_stt: MockWebSTT,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test that booking is detected."""
        mock_stt.set_transcription("Book a meeting")
        mock_scheduling_agent.set_response("Your meeting has been booked successfully.")

        _, _, _, changed = await voice_service.process_voice(
            session_id="test-session",
            audio_base64="SGVsbG8gV29ybGQ=",
        )

        assert changed is True

    @pytest.mark.asyncio
    async def test_process_voice_different_mime_types(
        self,
        voice_service: VoiceService,
        mock_stt: MockWebSTT,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test processing with different MIME types."""
        mock_stt.set_transcription("Hello")
        mock_scheduling_agent.set_response("Hi there!")

        mime_types = ["audio/webm", "audio/wav", "audio/mp3", "audio/ogg"]
        for mime_type in mime_types:
            transcribed, response, _, _ = await voice_service.process_voice(
                session_id=f"session-{mime_type}",
                audio_base64="SGVsbG8gV29ybGQ=",
                mime_type=mime_type,
            )
            assert transcribed == "Hello"
            assert response == "Hi there!"


class TestTranscribeOnly:
    """Tests for transcribe_only method."""

    @pytest.mark.asyncio
    async def test_transcribe_only(
        self,
        voice_service: VoiceService,
        mock_stt: MockWebSTT,
    ) -> None:
        """Test transcription-only functionality."""
        mock_stt.set_transcription("This is a test transcription.")

        result = await voice_service.transcribe_only(
            audio_base64="SGVsbG8gV29ybGQ=",
            mime_type="audio/webm",
        )

        assert result == "This is a test transcription."

    @pytest.mark.asyncio
    async def test_transcribe_only_empty(
        self,
        voice_service: VoiceService,
        mock_stt: MockWebSTT,
    ) -> None:
        """Test transcription returning empty string."""
        mock_stt.set_transcription("")

        result = await voice_service.transcribe_only(
            audio_base64="SGVsbG8gV29ybGQ=",
        )

        assert result == ""


class TestSynthesizeOnly:
    """Tests for synthesize_only method."""

    @pytest.mark.asyncio
    async def test_synthesize_only(
        self,
        voice_service: VoiceService,
        mock_tts: MockWebTTS,
    ) -> None:
        """Test text-to-speech synthesis."""
        mock_tts.set_audio_response("YXVkaW9fY29udGVudA==")

        audio, mime_type = await voice_service.synthesize_only(
            text="Hello, world!",
        )

        assert audio == "YXVkaW9fY29udGVudA=="
        assert mime_type == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_synthesize_only_with_voice(
        self,
        voice_service: VoiceService,
    ) -> None:
        """Test synthesis with specific voice."""
        audio, mime_type = await voice_service.synthesize_only(
            text="Hello",
            voice="echo",
        )

        # Should return mock audio regardless of voice
        assert audio is not None
        assert mime_type == "audio/mpeg"


class TestDetectAppointmentChanges:
    """Tests for _detect_appointment_changes method."""

    def test_detect_booked_successfully(self, voice_service: VoiceService) -> None:
        """Test detection of 'booked successfully'."""
        result = voice_service._detect_appointment_changes(
            "Your appointment has been booked successfully."
        )
        assert result is True

    def test_detect_cancelled(self, voice_service: VoiceService) -> None:
        """Test detection of cancellation."""
        result = voice_service._detect_appointment_changes(
            "Your appointment has been canceled."
        )
        assert result is True

    def test_detect_scheduled_for(self, voice_service: VoiceService) -> None:
        """Test detection of 'scheduled for'."""
        result = voice_service._detect_appointment_changes(
            "Your meeting is scheduled for 3pm tomorrow."
        )
        assert result is True

    def test_no_change_detected(self, voice_service: VoiceService) -> None:
        """Test when no change is detected."""
        result = voice_service._detect_appointment_changes(
            "Let me check your availability."
        )
        assert result is False

    def test_case_insensitive(self, voice_service: VoiceService) -> None:
        """Test case-insensitive detection."""
        result = voice_service._detect_appointment_changes(
            "YOUR MEETING HAS BEEN BOOKED SUCCESSFULLY!"
        )
        assert result is True


class TestProcessText:
    """Tests for _process_text method."""

    @pytest.mark.asyncio
    async def test_process_text_new_session(
        self,
        voice_service: VoiceService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test text processing with new session."""
        mock_scheduling_agent.set_response("I can help with that.")

        response, changed = await voice_service._process_text(
            session_id="new-session",
            message="Help me schedule a meeting",
        )

        assert response == "I can help with that."
        assert changed is False
        assert "new-session" in voice_service._sessions

    @pytest.mark.asyncio
    async def test_process_text_maintains_history(
        self,
        voice_service: VoiceService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test that history is maintained across calls."""
        mock_scheduling_agent.set_response("First response")
        await voice_service._process_text(
            session_id="test-session",
            message="First message",
        )

        mock_scheduling_agent.set_response("Second response")
        await voice_service._process_text(
            session_id="test-session",
            message="Second message",
        )

        history = voice_service._sessions.get("test-session", [])
        assert len(history) > 0


class TestGetHistory:
    """Tests for get_history method."""

    def test_get_history_empty(self, voice_service: VoiceService) -> None:
        """Test getting history for non-existent session."""
        history = voice_service.get_history("non-existent")
        assert history == []

    @pytest.mark.asyncio
    async def test_get_history_with_messages(
        self,
        voice_service: VoiceService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test getting history after processing."""
        await voice_service._process_text(
            session_id="test-session",
            message="Hello",
        )

        history = voice_service.get_history("test-session")
        assert len(history) > 0


class TestClearHistory:
    """Tests for clear_history method."""

    @pytest.mark.asyncio
    async def test_clear_history(
        self,
        voice_service: VoiceService,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test clearing session history."""
        await voice_service._process_text(
            session_id="test-session",
            message="Hello",
        )
        assert len(voice_service.get_history("test-session")) > 0

        voice_service.clear_history("test-session")
        assert voice_service.get_history("test-session") == []

    def test_clear_non_existent_session(self, voice_service: VoiceService) -> None:
        """Test clearing non-existent session doesn't raise."""
        voice_service.clear_history("non-existent")  # Should not raise


class TestFormatHistoryForClient:
    """Tests for format_history_for_client method."""

    def test_format_empty_history(self, voice_service: VoiceService) -> None:
        """Test formatting empty history."""
        formatted = voice_service.format_history_for_client("non-existent")
        assert formatted == []

    def test_format_string_content(self, voice_service: VoiceService) -> None:
        """Test formatting string content."""
        voice_service._sessions["test-session"] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        formatted = voice_service.format_history_for_client("test-session")
        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"

    def test_format_structured_content(self, voice_service: VoiceService) -> None:
        """Test formatting structured content."""
        voice_service._sessions["test-session"] = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Part 1"},
                    {"type": "text", "text": "Part 2"},
                ],
            }
        ]

        formatted = voice_service.format_history_for_client("test-session")
        assert len(formatted) == 1
        assert "Part 1" in formatted[0]["content"]
        assert "Part 2" in formatted[0]["content"]

    def test_format_filters_empty_content(self, voice_service: VoiceService) -> None:
        """Test filtering of empty content."""
        voice_service._sessions["test-session"] = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "Valid"},
        ]

        formatted = voice_service.format_history_for_client("test-session")
        assert len(formatted) == 1
        assert formatted[0]["content"] == "Valid"


class TestAvailableVoices:
    """Tests for available_voices property."""

    def test_available_voices(self, voice_service: VoiceService) -> None:
        """Test getting available voices."""
        voices = voice_service.available_voices
        assert isinstance(voices, list)
        assert len(voices) > 0
        assert "alloy" in voices
        assert "nova" in voices

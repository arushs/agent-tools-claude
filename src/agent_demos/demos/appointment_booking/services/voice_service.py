"""Voice service for handling voice conversations with Claude."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_demos.voice.tts import Voice
from agent_demos.voice.web_adapter import WebSTT, WebTTS

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.services.notification import (
        NotificationService,
    )
    from agent_demos.scheduling.agent import SchedulingAgent


class VoiceService:
    """Service for handling voice conversations with scheduling capabilities.

    Orchestrates the STT -> Claude -> TTS pipeline for voice interactions.
    """

    DEFAULT_VOICE: Voice = "nova"

    def __init__(
        self,
        scheduling_agent: SchedulingAgent,
        notification_service: NotificationService,
        openai_api_key: str | None = None,
        voice: Voice | None = None,
    ) -> None:
        """Initialize the voice service.

        Args:
            scheduling_agent: The scheduling agent for calendar operations.
            notification_service: Service for broadcasting notifications.
            openai_api_key: OpenAI API key for STT/TTS.
            voice: Default TTS voice to use.
        """
        self._agent = scheduling_agent
        self._notifications = notification_service
        self._stt = WebSTT(api_key=openai_api_key)
        self._tts = WebTTS(api_key=openai_api_key, voice=voice or self.DEFAULT_VOICE)
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    async def process_voice(
        self,
        session_id: str,
        audio_base64: str,
        mime_type: str = "audio/webm",
    ) -> tuple[str, str, str, bool]:
        """Process voice input and return voice response.

        Full pipeline: audio -> transcription -> Claude -> synthesis.

        Args:
            session_id: Session ID for conversation tracking.
            audio_base64: Base64-encoded audio data.
            mime_type: MIME type of the audio.

        Returns:
            Tuple of (transcribed_text, response_text, response_audio_base64, appointments_changed).
        """
        # Step 1: Transcribe audio to text
        transcribed_text = await self._stt.transcribe_base64_async(
            audio_base64,
            mime_type=mime_type,
        )

        if not transcribed_text.strip():
            # No speech detected
            return "", "I didn't catch that. Could you try again?", "", False

        # Step 2: Process with Claude
        response_text, appointments_changed = await self._process_text(
            session_id=session_id,
            message=transcribed_text,
        )

        # Step 3: Synthesize response to audio
        response_audio_base64, _ = await self._tts.synthesize_base64_async(
            text=response_text,
        )

        return transcribed_text, response_text, response_audio_base64, appointments_changed

    async def transcribe_only(
        self,
        audio_base64: str,
        mime_type: str = "audio/webm",
    ) -> str:
        """Transcribe audio without processing.

        Useful for voice-to-text mode where user wants to see transcription
        before sending.

        Args:
            audio_base64: Base64-encoded audio data.
            mime_type: MIME type of the audio.

        Returns:
            Transcribed text.
        """
        return await self._stt.transcribe_base64_async(audio_base64, mime_type)

    async def synthesize_only(
        self,
        text: str,
        voice: Voice | None = None,
    ) -> tuple[str, str]:
        """Synthesize text to audio without processing.

        Args:
            text: Text to synthesize.
            voice: Optional voice override.

        Returns:
            Tuple of (base64-encoded audio, MIME type).
        """
        return await self._tts.synthesize_base64_async(text, voice=voice)

    async def _process_text(
        self,
        session_id: str,
        message: str,
    ) -> tuple[str, bool]:
        """Process text message with Claude.

        Args:
            session_id: Session ID for conversation tracking.
            message: User's text message.

        Returns:
            Tuple of (response text, appointments_changed flag).
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
        appointments_changed = self._detect_appointment_changes(response)

        # If appointments changed, broadcast notification
        if appointments_changed:
            await self._notifications.broadcast("appointments_changed", {
                "session_id": session_id,
                "message": "Calendar updated via voice",
            })

        return response, appointments_changed

    def _detect_appointment_changes(self, response: str) -> bool:
        """Detect if the response indicates appointment changes.

        Args:
            response: Claude's response text.

        Returns:
            True if appointments were likely modified.
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
        return any(indicator in response_lower for indicator in change_indicators)

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

            if isinstance(content, str) and content.strip():
                formatted.append({"role": role, "content": content})
            elif isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                if text_parts:
                    formatted.append({"role": role, "content": " ".join(text_parts)})

        return formatted

    @property
    def available_voices(self) -> list[Voice]:
        """List of available TTS voices."""
        return self._tts.available_voices

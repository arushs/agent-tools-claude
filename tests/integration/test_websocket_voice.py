"""Integration tests for WebSocket voice functionality."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import MockSchedulingAgent, MockWebSTT, MockWebTTS


class TestWebSocketVoiceConnection:
    """Tests for WebSocket voice connection management."""

    def test_connect_new_session(self, client: TestClient) -> None:
        """Test connecting to voice WebSocket with new session."""
        with client.websocket_connect("/ws/voice") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "session_id" in data
            assert "voices" in data
            assert isinstance(data["voices"], list)

    def test_connect_with_session_id(self, client: TestClient) -> None:
        """Test connecting with a provided session ID."""
        session_id = "voice-session-123"
        with client.websocket_connect(f"/ws/voice?session_id={session_id}") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] == session_id

    def test_available_voices_in_connect(self, client: TestClient) -> None:
        """Test that available voices are included in connection message."""
        with client.websocket_connect("/ws/voice") as websocket:
            data = websocket.receive_json()
            voices = data.get("voices", [])
            # Our mock returns these voices
            assert "alloy" in voices
            assert "nova" in voices


class TestWebSocketVoiceAudioProcessing:
    """Tests for WebSocket voice audio processing."""

    def test_process_audio(
        self,
        client: TestClient,
        mock_stt: MockWebSTT,
        mock_tts: MockWebTTS,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test full audio processing pipeline."""
        mock_stt.set_transcription("Book a meeting for tomorrow")
        mock_scheduling_agent.set_response("I'll book that for you.")
        mock_tts.set_audio_response("YXVkaW9fZGF0YQ==")

        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            # Send audio
            websocket.send_json({
                "type": "audio",
                "data": "SGVsbG8gV29ybGQ=",
                "mime_type": "audio/webm",
            })

            # Should receive processing status (transcribing)
            status1 = websocket.receive_json()
            assert status1["type"] == "processing"
            assert status1["stage"] == "transcribing"

            # Should receive transcription
            transcription = websocket.receive_json()
            assert transcription["type"] == "transcription"
            assert transcription["text"] == "Book a meeting for tomorrow"

            # Should receive processing status (thinking)
            status2 = websocket.receive_json()
            assert status2["type"] == "processing"
            assert status2["stage"] == "thinking"

            # Should receive processing status (synthesizing)
            status3 = websocket.receive_json()
            assert status3["type"] == "processing"
            assert status3["stage"] == "synthesizing"

            # Should receive final response
            response = websocket.receive_json()
            assert response["type"] == "response"
            assert response["transcription"] == "Book a meeting for tomorrow"
            assert response["text"] == "I'll book that for you."
            assert "audio" in response
            assert "mime_type" in response
            assert "appointments_changed" in response

    def test_process_audio_no_speech(
        self,
        client: TestClient,
        mock_stt: MockWebSTT,
    ) -> None:
        """Test handling of audio with no detected speech."""
        mock_stt.set_transcription("")

        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "audio",
                "data": "SGVsbG8=",
                "mime_type": "audio/webm",
            })

            # Should receive processing status
            websocket.receive_json()  # transcribing

            # Should receive response with error
            response = websocket.receive_json()
            assert response["type"] == "response"
            assert response["error"] == "No speech detected"

    def test_process_audio_no_data(self, client: TestClient) -> None:
        """Test handling of audio request with no data."""
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "audio",
                "mime_type": "audio/webm",
            })

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "No audio data" in response["message"]

    def test_process_audio_with_appointment_change(
        self,
        client: TestClient,
        mock_stt: MockWebSTT,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test that appointment changes are detected."""
        mock_stt.set_transcription("Book a meeting")
        mock_scheduling_agent.set_response(
            "Your meeting has been booked successfully for tomorrow."
        )

        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "audio",
                "data": "SGVsbG8=",
                "mime_type": "audio/webm",
            })

            # Skip through processing messages
            for _ in range(4):  # transcribing, transcription, thinking, synthesizing
                websocket.receive_json()

            # When appointments change, we may receive notification before/after response
            messages = []
            for _ in range(2):  # Expect response and possibly notification
                msg = websocket.receive_json()
                messages.append(msg)

            # Find the response message
            response = next((m for m in messages if m["type"] == "response"), None)
            assert response is not None
            assert response["appointments_changed"] is True


class TestWebSocketVoiceTranscribeOnly:
    """Tests for transcription-only functionality."""

    def test_transcribe_only(
        self,
        client: TestClient,
        mock_stt: MockWebSTT,
    ) -> None:
        """Test transcription without Claude processing."""
        mock_stt.set_transcription("Test transcription text")

        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "transcribe",
                "data": "SGVsbG8=",
                "mime_type": "audio/webm",
            })

            # Should receive processing status
            status = websocket.receive_json()
            assert status["type"] == "processing"
            assert status["stage"] == "transcribing"

            # Should receive transcription
            transcription = websocket.receive_json()
            assert transcription["type"] == "transcription"
            assert transcription["text"] == "Test transcription text"

    def test_transcribe_only_no_data(self, client: TestClient) -> None:
        """Test transcription request with no data."""
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "transcribe",
                "mime_type": "audio/webm",
            })

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "No audio data" in response["message"]


class TestWebSocketVoiceSynthesizeOnly:
    """Tests for text-to-speech synthesis functionality."""

    def test_synthesize_only(
        self,
        client: TestClient,
        mock_tts: MockWebTTS,
    ) -> None:
        """Test text-to-speech synthesis."""
        mock_tts.set_audio_response("c3ludGhlc2l6ZWRfYXVkaW8=")

        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "synthesize",
                "text": "Hello, world!",
            })

            # Should receive processing status
            status = websocket.receive_json()
            assert status["type"] == "processing"
            assert status["stage"] == "synthesizing"

            # Should receive audio
            audio = websocket.receive_json()
            assert audio["type"] == "audio"
            assert audio["data"] == "c3ludGhlc2l6ZWRfYXVkaW8="
            assert audio["mime_type"] == "audio/mpeg"

    def test_synthesize_only_no_text(self, client: TestClient) -> None:
        """Test synthesis request with no text."""
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "synthesize",
                "text": "",
            })

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "No text" in response["message"]

    def test_synthesize_only_whitespace(self, client: TestClient) -> None:
        """Test synthesis request with whitespace-only text."""
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "synthesize",
                "text": "   ",
            })

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "No text" in response["message"]

    def test_synthesize_with_voice(self, client: TestClient) -> None:
        """Test synthesis with specific voice."""
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "type": "synthesize",
                "text": "Hello",
                "voice": "echo",
            })

            websocket.receive_json()  # processing
            audio = websocket.receive_json()
            assert audio["type"] == "audio"


class TestWebSocketVoicePing:
    """Tests for WebSocket voice ping/pong."""

    def test_ping_pong(self, client: TestClient) -> None:
        """Test ping/pong keepalive."""
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"type": "ping"})
            response = websocket.receive_json()

            assert response["type"] == "pong"


class TestWebSocketVoiceHistoryManagement:
    """Tests for WebSocket voice history management."""

    def test_clear_history(
        self,
        client: TestClient,
        mock_stt: MockWebSTT,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test clearing voice history."""
        mock_stt.set_transcription("Hello")
        mock_scheduling_agent.set_response("Hi!")

        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            # Process some audio first
            websocket.send_json({
                "type": "audio",
                "data": "SGVsbG8=",
                "mime_type": "audio/webm",
            })

            # Drain all responses
            for _ in range(5):
                websocket.receive_json()

            # Clear history
            websocket.send_json({"type": "clear_history"})
            response = websocket.receive_json()

            assert response["type"] == "history_cleared"


class TestWebSocketVoicePingPong:
    """Additional tests for voice ping/pong."""

    def test_multiple_pings(self, client: TestClient) -> None:
        """Test multiple ping/pong exchanges."""
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            for _ in range(5):
                websocket.send_json({"type": "ping"})
                response = websocket.receive_json()
                assert response["type"] == "pong"


class TestWebSocketVoiceUnknownMessageTypes:
    """Tests for handling unknown message types."""

    def test_unknown_message_type(self, client: TestClient) -> None:
        """Test that unknown message types don't crash the connection."""
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.receive_json()  # connected

            # Send unknown message type
            websocket.send_json({"type": "unknown_type"})

            # Connection should still work
            websocket.send_json({"type": "ping"})
            response = websocket.receive_json()
            assert response["type"] == "pong"

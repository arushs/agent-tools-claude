"""WebSocket endpoint for voice functionality."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from agent_demos.demos.appointment_booking.websocket.auth import authenticate_websocket

from agent_demos.demos.appointment_booking.rate_limit import check_ws_rate_limit

from agent_demos.core.exceptions import (
    AudioProcessingError,
    SynthesisError,
    TranscriptionError,
)
from agent_demos.demos.appointment_booking.error_handlers import (
    format_error_for_websocket,
)

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.app import AppState

logger = logging.getLogger(__name__)
voice_router = APIRouter()


def get_app_state(websocket: WebSocket) -> AppState:
    """Get application state from WebSocket."""
    return websocket.app.state.app_state


@voice_router.websocket("/voice")
async def websocket_voice(
    websocket: WebSocket,
    session_id: str | None = Query(default=None),
    token: str | None = Query(default=None),
) -> None:
    """WebSocket endpoint for voice interactions.

    Handles push-to-talk voice input and streams audio responses.

    Message types from client:
        - audio: { type: "audio", data: "<base64>", mime_type: "audio/webm" }
        - transcribe: { type: "transcribe", data: "<base64>", mime_type: "audio/webm" }
        - synthesize: { type: "synthesize", text: "Hello" }
        - clear_history: { type: "clear_history" }
        - ping: { type: "ping" }

    Message types to client:
        - connected: { type: "connected", session_id: "..." }
        - processing: { type: "processing", stage: "transcribing|thinking|synthesizing" }
        - transcription: { type: "transcription", text: "..." }
        - response: { type: "response", text: "...", audio: "<base64>", mime_type: "...", appointments_changed: bool }
        - audio: { type: "audio", data: "<base64>", mime_type: "audio/mpeg" }
        - error: { type: "error", message: "..." }
        - history_cleared: { type: "history_cleared" }
        - pong: { type: "pong" }

    Args:
        websocket: The WebSocket connection.
        session_id: Optional session ID for reconnection.
        token: Authentication token (required if websocket_auth_token is configured).
    """
    app_state = get_app_state(websocket)
    manager = app_state.connection_manager

    # Authenticate before accepting connection
    if not await authenticate_websocket(websocket, token, app_state):
        return

    # Accept connection and get session ID
    session_id = await manager.connect(websocket, session_id)

    # Send session ID to client
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "voices": app_state.voice_service.available_voices,
    })

    # Send any existing history
    history = app_state.voice_service.format_history_for_client(session_id)
    if history:
        await websocket.send_json({
            "type": "history",
            "messages": history,
        })

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type", "")

            if message_type == "audio":
                # Check rate limit for resource-intensive operations
                if not await check_ws_rate_limit(
                    websocket, app_state.rate_limiter, session_id
                ):
                    continue
                # Full voice pipeline: audio -> transcription -> Claude -> synthesis
                await _handle_audio_message(websocket, app_state, session_id, data)

            elif message_type == "transcribe":
                # Check rate limit for resource-intensive operations
                if not await check_ws_rate_limit(
                    websocket, app_state.rate_limiter, session_id
                ):
                    continue
                # Transcribe only (voice-to-text preview)
                await _handle_transcribe_message(websocket, app_state, data)

            elif message_type == "synthesize":
                # Check rate limit for resource-intensive operations
                if not await check_ws_rate_limit(
                    websocket, app_state.rate_limiter, session_id
                ):
                    continue
                # Synthesize text to audio
                await _handle_synthesize_message(websocket, app_state, data)

            elif message_type == "clear_history":
                app_state.voice_service.clear_history(session_id)
                await websocket.send_json({"type": "history_cleared"})

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.debug("Voice WebSocket disconnected: session %s", session_id)
        manager.disconnect(session_id)
    except Exception as e:
        logger.exception(
            "Unexpected error in voice WebSocket for session %s: %s",
            session_id,
            str(e),
        )
        manager.disconnect(session_id)


async def _handle_audio_message(
    websocket: WebSocket,
    app_state: AppState,
    session_id: str,
    data: dict,
) -> None:
    """Handle full audio processing pipeline.

    Args:
        websocket: WebSocket connection.
        app_state: Application state.
        session_id: Session ID.
        data: Message data with audio.
    """
    audio_base64 = data.get("data", "")
    mime_type = data.get("mime_type", "audio/webm")

    if not audio_base64:
        error = AudioProcessingError(
            message="No audio data provided",
            stage="validation",
        )
        await websocket.send_json(format_error_for_websocket(error))
        return

    voice_service = app_state.voice_service
    transcribed_text = None

    try:
        # Notify: transcribing
        await websocket.send_json({
            "type": "processing",
            "stage": "transcribing",
        })

        # Step 1: Transcribe
        try:
            transcribed_text = await voice_service.transcribe_only(audio_base64, mime_type)
        except Exception as e:
            logger.exception("Transcription failed for session %s", session_id)
            raise TranscriptionError(
                message="Failed to transcribe audio",
                stage="transcription",
                details={"original_error": str(e)},
            ) from e

        if not transcribed_text.strip():
            await websocket.send_json({
                "type": "response",
                "text": "",
                "transcription": "",
                "audio": "",
                "mime_type": "",
                "appointments_changed": False,
                "error": "No speech detected",
            })
            return

        # Send transcription immediately
        await websocket.send_json({
            "type": "transcription",
            "text": transcribed_text,
        })

        # Notify: thinking
        await websocket.send_json({
            "type": "processing",
            "stage": "thinking",
        })

        # Step 2: Process with Claude
        try:
            response_text, appointments_changed = await voice_service._process_text(
                session_id=session_id,
                message=transcribed_text,
            )
        except Exception as e:
            logger.exception("Claude processing failed for session %s", session_id)
            raise AudioProcessingError(
                message="Failed to process message with AI",
                stage="thinking",
                details={"original_error": str(e)},
            ) from e

        # Notify: synthesizing
        await websocket.send_json({
            "type": "processing",
            "stage": "synthesizing",
        })

        # Step 3: Synthesize response
        try:
            response_audio, response_mime = await voice_service.synthesize_only(response_text)
        except Exception as e:
            logger.exception("Speech synthesis failed for session %s", session_id)
            raise SynthesisError(
                message="Failed to synthesize audio response",
                details={"original_error": str(e)},
            ) from e

        # Send complete response
        await websocket.send_json({
            "type": "response",
            "transcription": transcribed_text,
            "text": response_text,
            "audio": response_audio,
            "mime_type": response_mime,
            "appointments_changed": appointments_changed,
        })

    except Exception as e:
        logger.exception("Error processing audio for session %s", session_id)
        await websocket.send_json(format_error_for_websocket(e))


async def _handle_transcribe_message(
    websocket: WebSocket,
    app_state: AppState,
    data: dict,
) -> None:
    """Handle transcription-only request.

    Args:
        websocket: WebSocket connection.
        app_state: Application state.
        data: Message data with audio.
    """
    audio_base64 = data.get("data", "")
    mime_type = data.get("mime_type", "audio/webm")

    if not audio_base64:
        error = AudioProcessingError(
            message="No audio data provided",
            stage="validation",
        )
        await websocket.send_json(format_error_for_websocket(error))
        return

    try:
        await websocket.send_json({
            "type": "processing",
            "stage": "transcribing",
        })

        text = await app_state.voice_service.transcribe_only(audio_base64, mime_type)

        await websocket.send_json({
            "type": "transcription",
            "text": text,
        })

    except Exception as e:
        logger.exception("Transcription failed")
        error = TranscriptionError(
            message="Failed to transcribe audio",
            stage="transcription",
            details={"original_error": str(e)},
        )
        await websocket.send_json(format_error_for_websocket(error))


async def _handle_synthesize_message(
    websocket: WebSocket,
    app_state: AppState,
    data: dict,
) -> None:
    """Handle text-to-speech synthesis request.

    Args:
        websocket: WebSocket connection.
        app_state: Application state.
        data: Message data with text.
    """
    text = data.get("text", "")
    voice = data.get("voice")

    if not text.strip():
        error = AudioProcessingError(
            message="No text provided for synthesis",
            stage="validation",
        )
        await websocket.send_json(format_error_for_websocket(error))
        return

    try:
        await websocket.send_json({
            "type": "processing",
            "stage": "synthesizing",
        })

        audio_base64, mime_type = await app_state.voice_service.synthesize_only(text, voice)

        await websocket.send_json({
            "type": "audio",
            "data": audio_base64,
            "mime_type": mime_type,
        })

    except Exception as e:
        logger.exception("Speech synthesis failed")
        error = SynthesisError(
            message="Failed to synthesize audio",
            details={"original_error": str(e)},
        )
        await websocket.send_json(format_error_for_websocket(error))

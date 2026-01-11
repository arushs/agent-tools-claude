"""WebSocket endpoint for voice functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from agent_demos.demos.appointment_booking.websocket.auth import authenticate_websocket

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.app import AppState

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
                # Full voice pipeline: audio -> transcription -> Claude -> synthesis
                await _handle_audio_message(websocket, app_state, session_id, data)

            elif message_type == "transcribe":
                # Transcribe only (voice-to-text preview)
                await _handle_transcribe_message(websocket, app_state, data)

            elif message_type == "synthesize":
                # Synthesize text to audio
                await _handle_synthesize_message(websocket, app_state, data)

            elif message_type == "clear_history":
                app_state.voice_service.clear_history(session_id)
                await websocket.send_json({"type": "history_cleared"})

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception:
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
        await websocket.send_json({
            "type": "error",
            "message": "No audio data provided",
        })
        return

    try:
        # Notify: transcribing
        await websocket.send_json({
            "type": "processing",
            "stage": "transcribing",
        })

        # Process full pipeline
        voice_service = app_state.voice_service

        # Step 1: Transcribe
        transcribed_text = await voice_service.transcribe_only(audio_base64, mime_type)

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
        response_text, appointments_changed = await voice_service._process_text(
            session_id=session_id,
            message=transcribed_text,
        )

        # Notify: synthesizing
        await websocket.send_json({
            "type": "processing",
            "stage": "synthesizing",
        })

        # Step 3: Synthesize response
        response_audio, response_mime = await voice_service.synthesize_only(response_text)

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
        await websocket.send_json({
            "type": "error",
            "message": f"Error processing audio: {str(e)}",
        })


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
        await websocket.send_json({
            "type": "error",
            "message": "No audio data provided",
        })
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
        await websocket.send_json({
            "type": "error",
            "message": f"Error transcribing audio: {str(e)}",
        })


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
        await websocket.send_json({
            "type": "error",
            "message": "No text provided",
        })
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
        await websocket.send_json({
            "type": "error",
            "message": f"Error synthesizing audio: {str(e)}",
        })

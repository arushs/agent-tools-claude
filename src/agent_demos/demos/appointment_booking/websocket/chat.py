"""WebSocket endpoint for chat functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.app import AppState

chat_router = APIRouter()


def get_app_state(websocket: WebSocket) -> AppState:
    """Get application state from WebSocket."""
    return websocket.app.state.app_state


@chat_router.websocket("/chat")
async def websocket_chat(websocket: WebSocket, session_id: str | None = None) -> None:
    """WebSocket endpoint for chat interactions.

    Args:
        websocket: The WebSocket connection.
        session_id: Optional session ID for reconnection.
    """
    app_state = get_app_state(websocket)
    manager = app_state.connection_manager

    # Accept connection and get session ID
    session_id = await manager.connect(websocket, session_id)

    # Send session ID to client
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
    })

    # Send any existing history
    history = app_state.chat_service.format_history_for_client(session_id)
    if history:
        await websocket.send_json({
            "type": "history",
            "messages": history,
        })

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type", "message")

            if message_type == "message":
                user_message = data.get("content", "").strip()
                if not user_message:
                    continue

                # Send acknowledgment
                await websocket.send_json({
                    "type": "ack",
                    "status": "processing",
                })

                try:
                    # Process with chat service
                    response, appointments_changed = await app_state.chat_service.process_message(
                        session_id=session_id,
                        message=user_message,
                    )

                    # Send response
                    await websocket.send_json({
                        "type": "response",
                        "content": response,
                        "appointments_changed": appointments_changed,
                    })

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Error processing message: {str(e)}",
                    })

            elif message_type == "clear_history":
                app_state.chat_service.clear_history(session_id)
                await websocket.send_json({
                    "type": "history_cleared",
                })

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception:
        manager.disconnect(session_id)

"""WebSocket authentication utilities."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.app import AppState

# Custom WebSocket close codes (4000-4999 are available for application use)
WS_CLOSE_AUTH_REQUIRED = 4001
WS_CLOSE_AUTH_FAILED = 4002


def verify_token(token: str | None, expected_token: str) -> bool:
    """Verify a WebSocket authentication token.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        token: The token provided by the client.
        expected_token: The expected token from configuration.

    Returns:
        True if the token is valid, False otherwise.
    """
    if token is None:
        return False

    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(token, expected_token)


def is_auth_enabled(auth_token: str) -> bool:
    """Check if WebSocket authentication is enabled.

    Args:
        auth_token: The configured authentication token.

    Returns:
        True if authentication is enabled (token is non-empty).
    """
    return bool(auth_token)


async def authenticate_websocket(
    websocket: WebSocket,
    token: str | None,
    app_state: AppState,
) -> bool:
    """Authenticate a WebSocket connection.

    This function should be called before accepting the WebSocket connection.
    If authentication fails, it closes the connection with an appropriate error code.

    Args:
        websocket: The WebSocket connection.
        token: The authentication token from the client (query parameter).
        app_state: Application state containing settings.

    Returns:
        True if authenticated (or auth disabled), False if rejected.
    """
    expected_token = app_state.settings.websocket_auth_token

    # If authentication is disabled, allow all connections
    if not is_auth_enabled(expected_token):
        return True

    # If auth is enabled but no token provided
    if token is None:
        await websocket.close(
            code=WS_CLOSE_AUTH_REQUIRED,
            reason="Authentication token required",
        )
        return False

    # Verify the token
    if not verify_token(token, expected_token):
        await websocket.close(
            code=WS_CLOSE_AUTH_FAILED,
            reason="Invalid authentication token",
        )
        return False

    return True

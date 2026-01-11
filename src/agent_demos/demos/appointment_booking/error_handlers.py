"""FastAPI error handlers for structured error responses.

Provides consistent error handling and logging across all API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent_demos.core.exceptions import (
    AgentDemoError,
    CalendarAPIError,
    CalendarAuthError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register global error handlers on the FastAPI app.

    Args:
        app: FastAPI application instance.
    """

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle validation errors with 400 status."""
        exc.log(level=logging.WARNING)
        return JSONResponse(
            status_code=400,
            content=exc.to_dict(),
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(
        request: Request, exc: NotFoundError
    ) -> JSONResponse:
        """Handle not found errors with 404 status."""
        exc.log(level=logging.INFO)
        return JSONResponse(
            status_code=404,
            content=exc.to_dict(),
        )

    @app.exception_handler(CalendarAuthError)
    async def calendar_auth_error_handler(
        request: Request, exc: CalendarAuthError
    ) -> JSONResponse:
        """Handle calendar authentication errors with 401 status."""
        exc.log(level=logging.ERROR)
        return JSONResponse(
            status_code=401,
            content=exc.to_dict(),
        )

    @app.exception_handler(CalendarAPIError)
    async def calendar_api_error_handler(
        request: Request, exc: CalendarAPIError
    ) -> JSONResponse:
        """Handle calendar API errors with 502 status."""
        exc.log(level=logging.ERROR)
        return JSONResponse(
            status_code=502,
            content=exc.to_dict(),
        )

    @app.exception_handler(AgentDemoError)
    async def agent_demo_error_handler(
        request: Request, exc: AgentDemoError
    ) -> JSONResponse:
        """Handle general agent demo errors.

        Falls back to 500 if no specific http_status_code is defined.
        """
        exc.log(level=logging.ERROR)
        status_code = getattr(exc, "http_status_code", 500)
        return JSONResponse(
            status_code=status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected errors with logging.

        Logs the full exception but returns a safe error message to the client.
        """
        logger.exception(
            "Unexpected error in %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "details": {},
            },
        )


def format_error_for_websocket(exc: Exception) -> dict[str, Any]:
    """Format an exception for WebSocket error response.

    Args:
        exc: The exception to format.

    Returns:
        Dictionary suitable for WebSocket JSON response.
    """
    if isinstance(exc, AgentDemoError):
        exc.log()
        return {
            "type": "error",
            "error_code": exc.code,
            "message": exc.message,
            "details": exc.details,
        }

    logger.exception("Unexpected WebSocket error: %s", str(exc))
    return {
        "type": "error",
        "error_code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred. Please try again.",
        "details": {},
    }

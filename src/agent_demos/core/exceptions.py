"""Custom exception hierarchy for agent demos.

Provides structured error handling with proper categorization for:
- API errors (validation, not found, service errors)
- Calendar/scheduling errors
- Voice processing errors
- WebSocket communication errors
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AgentDemoError(Exception):
    """Base exception for all agent demo errors.

    Attributes:
        message: Human-readable error message.
        code: Machine-readable error code.
        details: Additional error context.
    """

    def __init__(
        self,
        message: str,
        code: str = "AGENT_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }

    def log(self, level: int = logging.ERROR) -> None:
        """Log the exception with context."""
        logger.log(
            level,
            "%s: %s",
            self.code,
            self.message,
            extra={"error_details": self.details},
            exc_info=True,
        )


# === API / HTTP Errors ===


class ValidationError(AgentDemoError):
    """Invalid input data from client."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, code="VALIDATION_ERROR", details=details)

    @property
    def http_status_code(self) -> int:
        return 400


class NotFoundError(AgentDemoError):
    """Requested resource not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(message, code="NOT_FOUND", details=details)

    @property
    def http_status_code(self) -> int:
        return 404


class ConflictError(AgentDemoError):
    """Resource conflict (e.g., scheduling conflict)."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code="CONFLICT", details=details)

    @property
    def http_status_code(self) -> int:
        return 409


class ServiceUnavailableError(AgentDemoError):
    """External service is unavailable."""

    def __init__(
        self,
        service_name: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        details["service"] = service_name
        msg = message or f"Service unavailable: {service_name}"
        super().__init__(msg, code="SERVICE_UNAVAILABLE", details=details)

    @property
    def http_status_code(self) -> int:
        return 503


# === Calendar / Scheduling Errors ===


class CalendarError(AgentDemoError):
    """Base exception for calendar operations."""

    def __init__(
        self,
        message: str,
        code: str = "CALENDAR_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)


class CalendarAuthError(CalendarError):
    """Calendar authentication/authorization failure."""

    def __init__(
        self,
        message: str = "Calendar authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code="CALENDAR_AUTH_ERROR", details=details)

    @property
    def http_status_code(self) -> int:
        return 401


class CalendarAPIError(CalendarError):
    """Error communicating with calendar API."""

    def __init__(
        self,
        message: str,
        api_error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if api_error:
            details["api_error"] = api_error
        super().__init__(message, code="CALENDAR_API_ERROR", details=details)

    @property
    def http_status_code(self) -> int:
        return 502


class SchedulingConflictError(CalendarError):
    """Time slot conflict when scheduling."""

    def __init__(
        self,
        message: str,
        conflicting_events: list[dict[str, Any]] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if conflicting_events:
            details["conflicting_events"] = conflicting_events
        super().__init__(message, code="SCHEDULING_CONFLICT", details=details)

    @property
    def http_status_code(self) -> int:
        return 409


# === Voice Processing Errors ===


class VoiceError(AgentDemoError):
    """Base exception for voice processing."""

    def __init__(
        self,
        message: str,
        code: str = "VOICE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)


class TranscriptionError(VoiceError):
    """Speech-to-text transcription failure."""

    def __init__(
        self,
        message: str = "Failed to transcribe audio",
        stage: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if stage:
            details["stage"] = stage
        super().__init__(message, code="TRANSCRIPTION_ERROR", details=details)


class SynthesisError(VoiceError):
    """Text-to-speech synthesis failure."""

    def __init__(
        self,
        message: str = "Failed to synthesize audio",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code="SYNTHESIS_ERROR", details=details)


class AudioProcessingError(VoiceError):
    """Audio data processing failure."""

    def __init__(
        self,
        message: str,
        stage: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if stage:
            details["stage"] = stage
        super().__init__(message, code="AUDIO_PROCESSING_ERROR", details=details)


# === Tool Execution Errors ===


class ToolError(AgentDemoError):
    """Base exception for tool execution."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        code: str = "TOOL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        details["tool_name"] = tool_name
        super().__init__(message, code=code, details=details)


class ToolNotFoundError(ToolError):
    """Unknown tool requested."""

    def __init__(
        self,
        tool_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"Unknown tool: {tool_name}"
        super().__init__(message, tool_name=tool_name, code="TOOL_NOT_FOUND", details=details)


class ToolExecutionError(ToolError):
    """Tool execution failure."""

    def __init__(
        self,
        tool_name: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, tool_name=tool_name, code="TOOL_EXECUTION_ERROR", details=details)


class ToolValidationError(ToolError):
    """Tool input validation failure."""

    def __init__(
        self,
        tool_name: str,
        message: str,
        missing_params: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if missing_params:
            details["missing_params"] = missing_params
        super().__init__(message, tool_name=tool_name, code="TOOL_VALIDATION_ERROR", details=details)


# === WebSocket Errors ===


class WebSocketError(AgentDemoError):
    """Base exception for WebSocket communication."""

    def __init__(
        self,
        message: str,
        code: str = "WEBSOCKET_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)


class WebSocketMessageError(WebSocketError):
    """Invalid WebSocket message format."""

    def __init__(
        self,
        message: str,
        message_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if message_type:
            details["message_type"] = message_type
        super().__init__(message, code="WEBSOCKET_MESSAGE_ERROR", details=details)

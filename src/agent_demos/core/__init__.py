"""Core infrastructure for agent demos."""

from agent_demos.core.claude_client import ClaudeClient, MessageParam, ToolDefinition
from agent_demos.core.exceptions import (
    AgentDemoError,
    AudioProcessingError,
    CalendarAPIError,
    CalendarAuthError,
    CalendarError,
    ConflictError,
    NotFoundError,
    SchedulingConflictError,
    ServiceUnavailableError,
    SynthesisError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
    TranscriptionError,
    ValidationError,
    VoiceError,
    WebSocketError,
    WebSocketMessageError,
)

__all__ = [
    # Claude client
    "ClaudeClient",
    "MessageParam",
    "ToolDefinition",
    # Exceptions
    "AgentDemoError",
    "AudioProcessingError",
    "CalendarAPIError",
    "CalendarAuthError",
    "CalendarError",
    "ConflictError",
    "NotFoundError",
    "SchedulingConflictError",
    "ServiceUnavailableError",
    "SynthesisError",
    "ToolError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolValidationError",
    "TranscriptionError",
    "ValidationError",
    "VoiceError",
    "WebSocketError",
    "WebSocketMessageError",
]

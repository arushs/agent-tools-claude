"""Claude tool definitions for scheduling operations."""

from __future__ import annotations

from typing import Any

# Tool definitions for Claude API tool_use
SCHEDULING_TOOLS: list[dict[str, Any]] = [
    {
        "name": "check_availability",
        "description": "Check available time slots in a given date range. Returns a list of free time slots when appointments can be scheduled.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date/time in ISO 8601 format (e.g., '2024-01-15T09:00:00')",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date/time in ISO 8601 format (e.g., '2024-01-15T17:00:00')",
                },
                "slot_duration_minutes": {
                    "type": "integer",
                    "description": "Minimum duration in minutes for returned time slots. Defaults to 30.",
                    "default": 30,
                },
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "book_appointment",
        "description": "Book a new appointment on the calendar. Creates an event with the specified details and optionally invites attendees.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title/subject of the appointment",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format (e.g., '2024-01-15T10:00:00')",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in ISO 8601 format (e.g., '2024-01-15T11:00:00')",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses to invite",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description or notes for the appointment",
                },
                "location": {
                    "type": "string",
                    "description": "Optional location for the appointment",
                },
            },
            "required": ["title", "start_time", "end_time"],
        },
    },
    {
        "name": "list_appointments",
        "description": "List all appointments in a given date range. Returns event details including title, time, and attendees.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date/time in ISO 8601 format (e.g., '2024-01-15T00:00:00')",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date/time in ISO 8601 format (e.g., '2024-01-31T23:59:59')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of appointments to return. Defaults to 100.",
                    "default": 100,
                },
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment by its event ID. This will remove the event from the calendar and notify attendees.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "The unique ID of the event to cancel",
                },
            },
            "required": ["event_id"],
        },
    },
]


def get_scheduling_tools() -> list[dict[str, Any]]:
    """Get the list of scheduling tool definitions for Claude.

    Returns:
        List of tool definition dictionaries compatible with Claude API.

    Example:
        >>> from agent_demos.scheduling.tools import get_scheduling_tools
        >>> tools = get_scheduling_tools()
        >>> client.process_with_tools(messages, tools=tools, tool_executor=executor)
    """
    return SCHEDULING_TOOLS.copy()

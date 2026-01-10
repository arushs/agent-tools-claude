"""Scheduling Agent for appointment management with Claude."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_demos.core.claude_client import ClaudeClient, MessageParam
from agent_demos.scheduling.calendar import GoogleCalendarClient, Event, TimeSlot
from agent_demos.scheduling.tools import get_scheduling_tools


SYSTEM_PROMPT = """You are a helpful scheduling assistant. You help users manage their calendar by:
- Checking availability for meetings and appointments
- Booking new appointments
- Listing existing appointments
- Canceling appointments when requested

When booking appointments, always confirm the details with the user before creating the event.
Use the available tools to interact with the calendar.
Format dates and times clearly for the user.
If a time slot is not available, suggest alternative times.
"""


class SchedulingAgent:
    """Agent for managing calendar appointments using Claude and Google Calendar.

    This agent wraps a GoogleCalendarClient and provides a conversational interface
    for scheduling operations using Claude's tool use capabilities.

    Example:
        >>> agent = SchedulingAgent(credentials_path="credentials.json")
        >>> response = agent.chat("What's my schedule for tomorrow?")
        >>> print(response)
        "You have 3 appointments tomorrow: ..."

        >>> # Multi-turn conversation
        >>> response, history = agent.chat_with_history(
        ...     "Book a meeting with john@example.com",
        ...     history=[]
        ... )
    """

    def __init__(
        self,
        credentials_path: str | Path | None = None,
        token_path: str | Path | None = None,
        calendar_id: str = "primary",
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the Scheduling Agent.

        Args:
            credentials_path: Path to Google OAuth2 credentials.json file.
            token_path: Path to store/read the OAuth token.
            calendar_id: Google Calendar ID to operate on.
            api_key: Anthropic API key for Claude.
            model: Claude model to use.
        """
        self._calendar = GoogleCalendarClient(
            credentials_path=credentials_path,
            token_path=token_path,
            calendar_id=calendar_id,
        )
        self._claude = ClaudeClient(api_key=api_key, model=model)
        self._tools = get_scheduling_tools()

    def _execute_tool(self, name: str, input_data: dict[str, Any]) -> str:
        """Execute a scheduling tool and return the result.

        Args:
            name: Name of the tool to execute.
            input_data: Tool input parameters.

        Returns:
            JSON-formatted result string.
        """
        if name == "check_availability":
            return self._check_availability(input_data)
        elif name == "book_appointment":
            return self._book_appointment(input_data)
        elif name == "list_appointments":
            return self._list_appointments(input_data)
        elif name == "cancel_appointment":
            return self._cancel_appointment(input_data)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    def _check_availability(self, input_data: dict[str, Any]) -> str:
        """Handle check_availability tool call."""
        try:
            start = datetime.fromisoformat(input_data["start_date"])
            end = datetime.fromisoformat(input_data["end_date"])
            slot_duration = input_data.get("slot_duration_minutes", 30)

            slots = self._calendar.get_availability(start, end, slot_duration)
            return json.dumps({
                "available_slots": [slot.to_dict() for slot in slots],
                "total_slots": len(slots),
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _book_appointment(self, input_data: dict[str, Any]) -> str:
        """Handle book_appointment tool call."""
        try:
            start = datetime.fromisoformat(input_data["start_time"])
            end = datetime.fromisoformat(input_data["end_time"])

            event = self._calendar.create_event(
                title=input_data["title"],
                start=start,
                end=end,
                attendees=input_data.get("attendees"),
                description=input_data.get("description"),
                location=input_data.get("location"),
            )
            return json.dumps({
                "success": True,
                "event": event.to_dict(),
                "message": f"Appointment '{event.title}' booked successfully.",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _list_appointments(self, input_data: dict[str, Any]) -> str:
        """Handle list_appointments tool call."""
        try:
            start = datetime.fromisoformat(input_data["start_date"])
            end = datetime.fromisoformat(input_data["end_date"])
            max_results = input_data.get("max_results", 100)

            events = self._calendar.list_events(start, end, max_results)
            return json.dumps({
                "appointments": [event.to_dict() for event in events],
                "total_count": len(events),
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _cancel_appointment(self, input_data: dict[str, Any]) -> str:
        """Handle cancel_appointment tool call."""
        try:
            event_id = input_data["event_id"]
            success = self._calendar.cancel_event(event_id)

            if success:
                return json.dumps({
                    "success": True,
                    "message": f"Appointment {event_id} has been canceled.",
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to cancel appointment {event_id}.",
                })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> str:
        """Process a single user message and return Claude's response.

        Args:
            message: User's message.
            system_prompt: Optional custom system prompt.

        Returns:
            Claude's text response after processing any tool calls.
        """
        messages: list[MessageParam] = [{"role": "user", "content": message}]
        response, _ = self._claude.process_with_tools(
            messages=messages,
            tools=self._tools,
            tool_executor=self._execute_tool,
            system=system_prompt or SYSTEM_PROMPT,
        )
        return response

    def chat_with_history(
        self,
        message: str,
        history: list[MessageParam] | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, list[MessageParam]]:
        """Process a message with conversation history.

        Args:
            message: User's message.
            history: Previous conversation history.
            system_prompt: Optional custom system prompt.

        Returns:
            Tuple of (Claude's response, updated conversation history).
        """
        conversation = list(history) if history else []
        conversation.append({"role": "user", "content": message})

        response, full_history = self._claude.process_with_tools(
            messages=conversation,
            tools=self._tools,
            tool_executor=self._execute_tool,
            system=system_prompt or SYSTEM_PROMPT,
        )
        return response, full_history

    async def chat_async(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> str:
        """Process a single user message asynchronously.

        Args:
            message: User's message.
            system_prompt: Optional custom system prompt.

        Returns:
            Claude's text response after processing any tool calls.
        """
        messages: list[MessageParam] = [{"role": "user", "content": message}]
        response, _ = await self._claude.process_with_tools_async(
            messages=messages,
            tools=self._tools,
            tool_executor=self._execute_tool,
            system=system_prompt or SYSTEM_PROMPT,
        )
        return response

    async def chat_with_history_async(
        self,
        message: str,
        history: list[MessageParam] | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, list[MessageParam]]:
        """Process a message with conversation history asynchronously.

        Args:
            message: User's message.
            history: Previous conversation history.
            system_prompt: Optional custom system prompt.

        Returns:
            Tuple of (Claude's response, updated conversation history).
        """
        conversation = list(history) if history else []
        conversation.append({"role": "user", "content": message})

        response, full_history = await self._claude.process_with_tools_async(
            messages=conversation,
            tools=self._tools,
            tool_executor=self._execute_tool,
            system=system_prompt or SYSTEM_PROMPT,
        )
        return response, full_history

    @property
    def calendar(self) -> GoogleCalendarClient:
        """Access the underlying calendar client for direct operations."""
        return self._calendar

    @property
    def tools(self) -> list[dict[str, Any]]:
        """Get the tool definitions used by this agent."""
        return self._tools.copy()

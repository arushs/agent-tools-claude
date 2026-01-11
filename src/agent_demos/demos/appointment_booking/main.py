"""Appointment booking demo combining VoiceAgent with Google Calendar scheduling.

This demo shows how to create a voice-enabled appointment booking assistant that:
- Listens to natural language requests
- Checks calendar availability via Google Calendar API
- Creates calendar events for appointments
- Speaks confirmations back to the user

Example interaction:
    User: "Book me a meeting with John tomorrow at 2pm"
    Assistant: (checks availability) -> (creates event) -> "I've scheduled your meeting
               with John for tomorrow at 2pm. A calendar invite has been sent."
"""

from __future__ import annotations

import json
import logging
import os
import stat
from datetime import datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from agent_demos.core.claude_client import ToolDefinition
from agent_demos.core.exceptions import (
    CalendarAPIError,
    ToolNotFoundError,
    ToolValidationError,
)
from agent_demos.demos.appointment_booking.config import get_settings
from agent_demos.voice.agent import VoiceAgent

logger = logging.getLogger(__name__)

# Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _check_token_permissions(token_path: str) -> None:
    """Check if token file has secure permissions and warn if not.

    Args:
        token_path: Path to the token file.
    """
    try:
        file_stat = os.stat(token_path)
        mode = file_stat.st_mode
        # Check if group or others have any permissions
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            logger.warning(
                "Token file %s has insecure permissions (mode %o). "
                "Consider setting permissions to 0600 for security.",
                token_path,
                stat.S_IMODE(mode),
            )
    except OSError:
        pass  # File doesn't exist yet or other error


def get_calendar_service():
    """Authenticate and return Google Calendar service.

    Uses OAuth 2.0 flow with credentials from GOOGLE_CREDENTIALS_PATH.
    Stores refresh token in the path specified by config's google_token_path.

    Returns:
        Google Calendar API service instance.
    """
    settings = get_settings()
    token_path = settings.google_token_path
    creds = None
    credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")

    if not credentials_path:
        raise ValueError(
            "GOOGLE_CREDENTIALS_PATH environment variable not set. "
            "Download OAuth credentials from Google Cloud Console and set the path."
        )

    # Load existing token if available
    if os.path.exists(token_path):
        _check_token_permissions(token_path)
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh or get new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save credentials with restrictive permissions (0600)
        old_umask = os.umask(0o077)
        try:
            with open(token_path, "w") as token:
                token.write(creds.to_json())
            os.chmod(token_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        finally:
            os.umask(old_umask)

    return build("calendar", "v3", credentials=creds)


def check_availability(
    service,
    start_time: datetime,
    end_time: datetime,
    calendar_id: str = "primary",
) -> list[dict]:
    """Check calendar availability for a time range.

    Args:
        service: Google Calendar API service.
        start_time: Start of the time range to check.
        end_time: End of the time range to check.
        calendar_id: Calendar ID to check. Defaults to primary calendar.

    Returns:
        List of existing events in the time range.
    """
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time.isoformat() + "Z",
        timeMax=end_time.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return events_result.get("items", [])


def create_event(
    service,
    summary: str,
    start_time: datetime,
    end_time: datetime,
    description: str | None = None,
    attendees: list[str] | None = None,
    calendar_id: str = "primary",
) -> dict:
    """Create a calendar event.

    Args:
        service: Google Calendar API service.
        summary: Event title.
        start_time: Event start time.
        end_time: Event end time.
        description: Optional event description.
        attendees: Optional list of attendee email addresses.
        calendar_id: Calendar ID for the event. Defaults to primary.

    Returns:
        Created event details.
    """
    event = {
        "summary": summary,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC",
        },
    }

    if description:
        event["description"] = description

    if attendees:
        event["attendees"] = [{"email": email} for email in attendees]

    return service.events().insert(calendarId=calendar_id, body=event).execute()


# Tool definitions for Claude
SCHEDULING_TOOLS: list[ToolDefinition] = [
    {
        "name": "check_calendar_availability",
        "description": (
            "Check if a time slot is available on the calendar. "
            "Returns existing events that conflict with the requested time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to check in YYYY-MM-DD format",
                },
                "start_hour": {
                    "type": "integer",
                    "description": "Start hour in 24-hour format (0-23)",
                },
                "start_minute": {
                    "type": "integer",
                    "description": "Start minute (0-59)",
                    "default": 0,
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration of the meeting in minutes",
                    "default": 60,
                },
            },
            "required": ["date", "start_hour"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": (
            "Create a new calendar event/meeting. "
            "Use this after confirming availability with check_calendar_availability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title/summary of the meeting",
                },
                "date": {
                    "type": "string",
                    "description": "Date of the event in YYYY-MM-DD format",
                },
                "start_hour": {
                    "type": "integer",
                    "description": "Start hour in 24-hour format (0-23)",
                },
                "start_minute": {
                    "type": "integer",
                    "description": "Start minute (0-59)",
                    "default": 0,
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration of the meeting in minutes",
                    "default": 60,
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for the event",
                },
                "attendee_emails": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of attendee email addresses",
                },
            },
            "required": ["title", "date", "start_hour"],
        },
    },
    {
        "name": "get_todays_date",
        "description": "Get today's date and current time to help with scheduling relative dates like 'tomorrow' or 'next week'.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


class SchedulingToolExecutor:
    """Executor for scheduling-related tools.

    Handles execution of calendar tools and maintains the Google Calendar service.
    """

    def __init__(self, service=None):
        """Initialize the executor.

        Args:
            service: Optional pre-initialized Google Calendar service.
                    If not provided, will be initialized on first tool call.
        """
        self._service = service

    @property
    def service(self):
        """Lazy-initialize and return the Calendar service."""
        if self._service is None:
            self._service = get_calendar_service()
        return self._service

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a scheduling tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Input parameters for the tool.

        Returns:
            Tool execution result as a string.
        """
        try:
            if tool_name == "check_calendar_availability":
                return self._check_availability(tool_input)
            elif tool_name == "create_calendar_event":
                return self._create_event(tool_input)
            elif tool_name == "get_todays_date":
                return self._get_todays_date()
            else:
                error = ToolNotFoundError(tool_name=tool_name)
                logger.warning("Unknown tool requested: %s", tool_name)
                return json.dumps(error.to_dict())
        except ToolValidationError as e:
            logger.warning("Tool validation failed: %s", e.message)
            return json.dumps(e.to_dict())
        except CalendarAPIError as e:
            logger.exception("Calendar API error in tool %s", tool_name)
            return json.dumps(e.to_dict())
        except Exception as e:
            logger.exception("Unexpected error in tool %s", tool_name)
            return json.dumps({
                "error": "TOOL_ERROR",
                "message": f"Unexpected error executing {tool_name}: {str(e)}",
            })

    def _check_availability(self, params: dict[str, Any]) -> str:
        """Check calendar availability."""
        # Validate required parameters
        missing_params = []
        if "date" not in params:
            missing_params.append("date")
        if "start_hour" not in params:
            missing_params.append("start_hour")

        if missing_params:
            raise ToolValidationError(
                tool_name="check_calendar_availability",
                message=f"Missing required parameters: {', '.join(missing_params)}",
                missing_params=missing_params,
            )

        date_str = params["date"]
        start_hour = params["start_hour"]
        start_minute = params.get("start_minute", 0)
        duration_minutes = params.get("duration_minutes", 60)

        # Validate parameter types and values
        if not isinstance(start_hour, int) or not (0 <= start_hour <= 23):
            raise ToolValidationError(
                tool_name="check_calendar_availability",
                message="start_hour must be an integer between 0 and 23",
            )

        if not isinstance(start_minute, int) or not (0 <= start_minute <= 59):
            raise ToolValidationError(
                tool_name="check_calendar_availability",
                message="start_minute must be an integer between 0 and 59",
            )

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ToolValidationError(
                tool_name="check_calendar_availability",
                message=f"Invalid date format. Expected YYYY-MM-DD, got: {date_str}",
            ) from e

        start_time = date.replace(hour=start_hour, minute=start_minute)
        end_time = start_time + timedelta(minutes=duration_minutes)

        try:
            events = check_availability(self.service, start_time, end_time)
        except Exception as e:
            raise CalendarAPIError(
                message="Failed to check calendar availability",
                api_error=str(e),
            ) from e

        if not events:
            return json.dumps({
                "available": True,
                "message": f"The time slot from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')} on {date_str} is available.",
                "conflicting_events": [],
            })
        else:
            conflicts = [
                {
                    "title": e.get("summary", "Busy"),
                    "start": e["start"].get("dateTime", e["start"].get("date")),
                    "end": e["end"].get("dateTime", e["end"].get("date")),
                }
                for e in events
            ]
            return json.dumps({
                "available": False,
                "message": f"There are {len(events)} conflicting event(s) during this time.",
                "conflicting_events": conflicts,
            })

    def _create_event(self, params: dict[str, Any]) -> str:
        """Create a calendar event."""
        # Validate required parameters
        missing_params = []
        if "title" not in params:
            missing_params.append("title")
        if "date" not in params:
            missing_params.append("date")
        if "start_hour" not in params:
            missing_params.append("start_hour")

        if missing_params:
            raise ToolValidationError(
                tool_name="create_calendar_event",
                message=f"Missing required parameters: {', '.join(missing_params)}",
                missing_params=missing_params,
            )

        title = params["title"]
        date_str = params["date"]
        start_hour = params["start_hour"]
        start_minute = params.get("start_minute", 0)
        duration_minutes = params.get("duration_minutes", 60)
        description = params.get("description")
        attendees = params.get("attendee_emails")

        # Validate parameter types and values
        if not isinstance(title, str) or not title.strip():
            raise ToolValidationError(
                tool_name="create_calendar_event",
                message="title must be a non-empty string",
            )

        if not isinstance(start_hour, int) or not (0 <= start_hour <= 23):
            raise ToolValidationError(
                tool_name="create_calendar_event",
                message="start_hour must be an integer between 0 and 23",
            )

        if not isinstance(start_minute, int) or not (0 <= start_minute <= 59):
            raise ToolValidationError(
                tool_name="create_calendar_event",
                message="start_minute must be an integer between 0 and 59",
            )

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ToolValidationError(
                tool_name="create_calendar_event",
                message=f"Invalid date format. Expected YYYY-MM-DD, got: {date_str}",
            ) from e

        start_time = date.replace(hour=start_hour, minute=start_minute)
        end_time = start_time + timedelta(minutes=duration_minutes)

        try:
            event = create_event(
                self.service,
                summary=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                attendees=attendees,
            )
        except Exception as e:
            raise CalendarAPIError(
                message="Failed to create calendar event",
                api_error=str(e),
                details={"title": title},
            ) from e

        return json.dumps({
            "success": True,
            "message": f"Event '{title}' created successfully.",
            "event_id": event.get("id"),
            "event_link": event.get("htmlLink"),
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        })

    def _get_todays_date(self) -> str:
        """Get today's date and time."""
        now = datetime.now()
        return json.dumps({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "day_of_week": now.strftime("%A"),
            "iso": now.isoformat(),
        })


SYSTEM_PROMPT = """You are a helpful voice assistant that helps users schedule appointments and manage their calendar.

When users ask to book meetings or appointments:
1. First use get_todays_date to understand relative dates (like "tomorrow" or "next Monday")
2. Then use check_calendar_availability to verify the requested time slot is free
3. If available, use create_calendar_event to create the appointment
4. If not available, suggest alternative times based on the conflicts

Always confirm the details before creating an event:
- Meeting title/purpose
- Date and time
- Duration (default to 1 hour if not specified)

Speak naturally and conversationally. Be concise in your responses since they will be spoken aloud.
When dates or times are ambiguous, ask for clarification."""


def create_appointment_agent(
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    calendar_service=None,
) -> tuple[VoiceAgent, SchedulingToolExecutor]:
    """Create a VoiceAgent configured for appointment booking.

    Args:
        openai_api_key: OpenAI API key for STT/TTS.
        anthropic_api_key: Anthropic API key for Claude.
        calendar_service: Optional pre-initialized Google Calendar service.

    Returns:
        Tuple of (VoiceAgent, SchedulingToolExecutor).
    """
    agent = VoiceAgent(
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key,
        voice="nova",  # Use nova voice for a friendly assistant feel
        system_prompt=SYSTEM_PROMPT,
    )

    executor = SchedulingToolExecutor(service=calendar_service)

    return agent, executor


def run_demo():
    """Run the appointment booking demo.

    This starts an interactive voice conversation where users can:
    - Ask about their schedule
    - Book new appointments
    - Check availability

    Say "goodbye" or "exit" to end the conversation.
    """
    print("=" * 60)
    print("Appointment Booking Voice Assistant")
    print("=" * 60)
    print()
    print("This demo lets you book appointments using your voice.")
    print("You can say things like:")
    print("  - 'Book me a meeting with John tomorrow at 2pm'")
    print("  - 'Am I free on Friday at 3pm?'")
    print("  - 'Schedule a team standup for Monday at 9am'")
    print()
    print("Say 'goodbye' or 'exit' to end the conversation.")
    print("=" * 60)
    print()

    # Create the agent and tool executor
    agent, executor = create_appointment_agent()

    # Run the conversation with voice activity detection for natural interaction
    agent.run_conversation_vad(
        tools=SCHEDULING_TOOLS,
        tool_executor=executor.execute,
        greeting="Hello! I'm your appointment booking assistant. How can I help you schedule something today?",
    )


def run_text_demo():
    """Run a text-based version of the demo (for testing without audio).

    Useful for testing the scheduling logic without microphone/speaker setup.
    """
    print("=" * 60)
    print("Appointment Booking Assistant (Text Mode)")
    print("=" * 60)
    print()
    print("Type your scheduling requests. Type 'quit' to exit.")
    print()

    agent, executor = create_appointment_agent()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "goodbye", "bye"]:
            print("Assistant: Goodbye! Have a great day.")
            break

        response = agent.process(
            user_input,
            tools=SCHEDULING_TOOLS,
            tool_executor=executor.execute,
        )
        print(f"Assistant: {response}")
        print()


if __name__ == "__main__":
    import sys

    if "--text" in sys.argv:
        run_text_demo()
    else:
        run_demo()

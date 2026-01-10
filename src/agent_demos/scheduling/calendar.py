"""Google Calendar client for scheduling operations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar"]


@dataclass
class TimeSlot:
    """Represents an available time slot."""

    start: datetime
    end: datetime

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary format."""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


@dataclass
class Event:
    """Represents a calendar event."""

    id: str
    title: str
    start: datetime
    end: datetime
    attendees: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "attendees": self.attendees,
        }


class GoogleCalendarClient:
    """Client for interacting with Google Calendar API.

    This client handles OAuth2 authentication and provides methods for
    common calendar operations like checking availability, creating events,
    listing events, and canceling events.

    Example:
        >>> client = GoogleCalendarClient(credentials_path="credentials.json")
        >>> events = client.list_events(
        ...     start=datetime(2024, 1, 1),
        ...     end=datetime(2024, 1, 31)
        ... )
        >>> for event in events:
        ...     print(f"{event.title}: {event.start}")
    """

    TOKEN_FILE = "token.json"

    def __init__(
        self,
        credentials_path: str | Path | None = None,
        token_path: str | Path | None = None,
        calendar_id: str = "primary",
    ) -> None:
        """Initialize the Google Calendar client.

        Args:
            credentials_path: Path to OAuth2 credentials.json file.
                If not provided, uses GOOGLE_CREDENTIALS_PATH env var
                or defaults to "credentials.json".
            token_path: Path to store/read the OAuth token.
                If not provided, uses GOOGLE_TOKEN_PATH env var
                or defaults to "token.json".
            calendar_id: Calendar ID to operate on. Defaults to "primary".
        """
        self._credentials_path = Path(
            credentials_path
            or os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        )
        self._token_path = Path(
            token_path or os.environ.get("GOOGLE_TOKEN_PATH", self.TOKEN_FILE)
        )
        self._calendar_id = calendar_id
        self._service: Any = None
        self._creds: Credentials | None = None

    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth2 credentials.

        Returns:
            Valid OAuth2 credentials.

        Raises:
            FileNotFoundError: If credentials.json doesn't exist.
        """
        creds: Credentials | None = None

        # Load existing token if available
        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_path), SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self._credentials_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {self._credentials_path}. "
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            self._token_path.write_text(creds.to_json())

        return creds

    @property
    def service(self) -> Any:
        """Lazy-initialize the Calendar API service."""
        if self._service is None:
            self._creds = self._get_credentials()
            self._service = build("calendar", "v3", credentials=self._creds)
        return self._service

    def _parse_datetime(self, dt_dict: dict[str, str]) -> datetime:
        """Parse datetime from Google Calendar API response.

        Args:
            dt_dict: Dict with 'dateTime' or 'date' key.

        Returns:
            Parsed datetime object.
        """
        if "dateTime" in dt_dict:
            # Parse datetime with timezone
            dt_str = dt_dict["dateTime"]
            # Handle timezone offset format
            if "+" in dt_str or dt_str.endswith("Z"):
                dt_str = dt_str.replace("Z", "+00:00")
                return datetime.fromisoformat(dt_str)
            return datetime.fromisoformat(dt_str)
        else:
            # All-day event, parse date only
            return datetime.fromisoformat(dt_dict["date"])

    def get_availability(
        self,
        start: datetime,
        end: datetime,
        slot_duration_minutes: int = 30,
    ) -> list[TimeSlot]:
        """Get available time slots in a time range.

        Finds free time slots by querying busy periods and computing
        the inverse (free periods).

        Args:
            start: Start of time range.
            end: End of time range.
            slot_duration_minutes: Minimum duration for a slot to be returned.

        Returns:
            List of available TimeSlot objects.
        """
        # Query freebusy API for busy periods
        body = {
            "timeMin": start.isoformat() + "Z" if start.tzinfo is None else start.isoformat(),
            "timeMax": end.isoformat() + "Z" if end.tzinfo is None else end.isoformat(),
            "items": [{"id": self._calendar_id}],
        }

        result = self.service.freebusy().query(body=body).execute()
        busy_periods = result.get("calendars", {}).get(self._calendar_id, {}).get("busy", [])

        # Convert busy periods to datetime objects
        busy_slots: list[tuple[datetime, datetime]] = []
        for period in busy_periods:
            busy_start = self._parse_datetime({"dateTime": period["start"]})
            busy_end = self._parse_datetime({"dateTime": period["end"]})
            busy_slots.append((busy_start, busy_end))

        # Sort busy slots by start time
        busy_slots.sort(key=lambda x: x[0])

        # Compute free slots
        free_slots: list[TimeSlot] = []
        current = start

        for busy_start, busy_end in busy_slots:
            if current < busy_start:
                # There's a gap before this busy period
                gap_minutes = (busy_start - current).total_seconds() / 60
                if gap_minutes >= slot_duration_minutes:
                    free_slots.append(TimeSlot(start=current, end=busy_start))
            current = max(current, busy_end)

        # Check for free time after last busy period
        if current < end:
            gap_minutes = (end - current).total_seconds() / 60
            if gap_minutes >= slot_duration_minutes:
                free_slots.append(TimeSlot(start=current, end=end))

        return free_slots

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        attendees: list[str] | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> Event:
        """Create a new calendar event.

        Args:
            title: Event title/summary.
            start: Event start time.
            end: Event end time.
            attendees: List of attendee email addresses.
            description: Event description.
            location: Event location.

        Returns:
            Created Event object.
        """
        event_body: dict[str, Any] = {
            "summary": title,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "UTC",
            },
        }

        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        if description:
            event_body["description"] = description

        if location:
            event_body["location"] = location

        result = self.service.events().insert(
            calendarId=self._calendar_id,
            body=event_body,
            sendUpdates="all" if attendees else "none",
        ).execute()

        return Event(
            id=result["id"],
            title=result.get("summary", ""),
            start=self._parse_datetime(result["start"]),
            end=self._parse_datetime(result["end"]),
            attendees=[a.get("email", "") for a in result.get("attendees", [])],
        )

    def list_events(
        self,
        start: datetime,
        end: datetime,
        max_results: int = 100,
    ) -> list[Event]:
        """List events in a time range.

        Args:
            start: Start of time range.
            end: End of time range.
            max_results: Maximum number of events to return.

        Returns:
            List of Event objects.
        """
        time_min = start.isoformat() + "Z" if start.tzinfo is None else start.isoformat()
        time_max = end.isoformat() + "Z" if end.tzinfo is None else end.isoformat()

        result = self.service.events().list(
            calendarId=self._calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events: list[Event] = []
        for item in result.get("items", []):
            events.append(
                Event(
                    id=item["id"],
                    title=item.get("summary", ""),
                    start=self._parse_datetime(item["start"]),
                    end=self._parse_datetime(item["end"]),
                    attendees=[a.get("email", "") for a in item.get("attendees", [])],
                )
            )

        return events

    def cancel_event(self, event_id: str) -> bool:
        """Cancel (delete) an event.

        Args:
            event_id: ID of the event to cancel.

        Returns:
            True if successfully canceled, False otherwise.
        """
        try:
            self.service.events().delete(
                calendarId=self._calendar_id,
                eventId=event_id,
                sendUpdates="all",
            ).execute()
            return True
        except Exception:
            return False

    def get_event(self, event_id: str) -> Event | None:
        """Get a specific event by ID.

        Args:
            event_id: ID of the event to retrieve.

        Returns:
            Event object if found, None otherwise.
        """
        try:
            result = self.service.events().get(
                calendarId=self._calendar_id,
                eventId=event_id,
            ).execute()

            return Event(
                id=result["id"],
                title=result.get("summary", ""),
                start=self._parse_datetime(result["start"]),
                end=self._parse_datetime(result["end"]),
                attendees=[a.get("email", "") for a in result.get("attendees", [])],
            )
        except Exception:
            return None

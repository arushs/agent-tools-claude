"""Calendar availability REST API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from agent_demos.core.exceptions import CalendarAPIError
from agent_demos.demos.appointment_booking.models import (
    AvailabilityResponse,
    TimeSlot,
)

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.app import AppState

logger = logging.getLogger(__name__)
router = APIRouter()


def get_app_state(request: Request) -> AppState:
    """Get application state from request."""
    return request.app.state.app_state


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    request: Request,
    start: datetime | None = None,
    end: datetime | None = None,
    slot_duration_minutes: int = 30,
) -> AvailabilityResponse:
    """Get available time slots for scheduling.

    Args:
        request: FastAPI request object.
        start: Start of time range (defaults to now).
        end: End of time range (defaults to 7 days from now).
        slot_duration_minutes: Minimum slot duration in minutes.

    Returns:
        Available time slots.
    """
    app_state = get_app_state(request)

    if start is None:
        start = datetime.utcnow()
    if end is None:
        end = start + timedelta(days=7)

    try:
        slots = app_state.scheduling_agent.calendar.get_availability(
            start=start,
            end=end,
            slot_duration_minutes=slot_duration_minutes,
        )

        return AvailabilityResponse(
            available_slots=[
                TimeSlot(start=slot.start, end=slot.end) for slot in slots
            ],
            total_slots=len(slots),
        )
    except Exception as e:
        logger.exception("Failed to get calendar availability")
        raise CalendarAPIError(
            message="Failed to retrieve calendar availability",
            api_error=str(e),
        ) from e

"""Appointments REST API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from agent_demos.core.exceptions import (
    CalendarAPIError,
    NotFoundError,
)
from agent_demos.demos.appointment_booking.models import (
    Appointment,
    AppointmentCreate,
)

if TYPE_CHECKING:
    from agent_demos.demos.appointment_booking.app import AppState

logger = logging.getLogger(__name__)
router = APIRouter()


def get_app_state(request: Request) -> AppState:
    """Get application state from request."""
    return request.app.state.app_state


@router.get("/appointments", response_model=list[Appointment])
async def list_appointments(
    request: Request,
    start: datetime | None = None,
    end: datetime | None = None,
    max_results: int = 100,
) -> list[Appointment]:
    """List appointments within a date range.

    Args:
        request: FastAPI request object.
        start: Start of date range (defaults to now).
        end: End of date range (defaults to 30 days from now).
        max_results: Maximum number of results to return.

    Returns:
        List of appointments.
    """
    app_state = get_app_state(request)

    if start is None:
        start = datetime.utcnow()
    if end is None:
        end = start + timedelta(days=30)

    try:
        events = app_state.scheduling_agent.calendar.list_events(
            start=start,
            end=end,
            max_results=max_results,
        )

        return [
            Appointment(
                id=event.id,
                title=event.title,
                start=event.start,
                end=event.end,
                attendees=event.attendees,
            )
            for event in events
        ]
    except Exception as e:
        logger.exception("Failed to list appointments")
        raise CalendarAPIError(
            message="Failed to retrieve appointments from calendar",
            api_error=str(e),
        ) from e


@router.post("/appointments", response_model=Appointment, status_code=201)
async def create_appointment(
    request: Request,
    appointment: AppointmentCreate,
) -> Appointment:
    """Create a new appointment.

    Args:
        request: FastAPI request object.
        appointment: Appointment details.

    Returns:
        Created appointment.
    """
    app_state = get_app_state(request)

    try:
        event = app_state.scheduling_agent.calendar.create_event(
            title=appointment.title,
            start=appointment.start,
            end=appointment.end,
            attendees=appointment.attendees or None,
            description=appointment.description,
            location=appointment.location,
        )

        created_appointment = Appointment(
            id=event.id,
            title=event.title,
            start=event.start,
            end=event.end,
            attendees=event.attendees,
            description=appointment.description,
            location=appointment.location,
        )

        # Broadcast notification
        await app_state.notification_service.broadcast_appointment_created(
            created_appointment.model_dump(mode="json")
        )

        return created_appointment
    except Exception as e:
        logger.exception("Failed to create appointment: %s", appointment.title)
        raise CalendarAPIError(
            message="Failed to create appointment",
            api_error=str(e),
            details={"title": appointment.title},
        ) from e


@router.get("/appointments/{appointment_id}", response_model=Appointment)
async def get_appointment(
    request: Request,
    appointment_id: str,
) -> Appointment:
    """Get a specific appointment by ID.

    Args:
        request: FastAPI request object.
        appointment_id: The appointment ID.

    Returns:
        The appointment.
    """
    app_state = get_app_state(request)

    try:
        event = app_state.scheduling_agent.calendar.get_event(appointment_id)
        if event is None:
            raise NotFoundError(
                resource_type="Appointment",
                resource_id=appointment_id,
            )

        return Appointment(
            id=event.id,
            title=event.title,
            start=event.start,
            end=event.end,
            attendees=event.attendees,
        )
    except NotFoundError:
        raise
    except Exception as e:
        logger.exception("Failed to get appointment: %s", appointment_id)
        raise CalendarAPIError(
            message="Failed to retrieve appointment",
            api_error=str(e),
            details={"appointment_id": appointment_id},
        ) from e


@router.delete("/appointments/{appointment_id}", status_code=204)
async def delete_appointment(
    request: Request,
    appointment_id: str,
) -> None:
    """Delete (cancel) an appointment.

    Args:
        request: FastAPI request object.
        appointment_id: The appointment ID to cancel.
    """
    app_state = get_app_state(request)

    try:
        success = app_state.scheduling_agent.calendar.cancel_event(appointment_id)
        if not success:
            raise NotFoundError(
                resource_type="Appointment",
                resource_id=appointment_id,
            )

        # Broadcast notification
        await app_state.notification_service.broadcast_appointment_cancelled(
            {"id": appointment_id}
        )
    except NotFoundError:
        raise
    except Exception as e:
        logger.exception("Failed to delete appointment: %s", appointment_id)
        raise CalendarAPIError(
            message="Failed to delete appointment",
            api_error=str(e),
            details={"appointment_id": appointment_id},
        ) from e

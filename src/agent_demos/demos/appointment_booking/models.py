"""Pydantic models for the appointment booking demo."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AppointmentStatus(str, Enum):
    """Status of an appointment."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class Appointment(BaseModel):
    """Appointment model for API responses."""

    id: str
    title: str
    start: datetime
    end: datetime
    attendees: list[str] = Field(default_factory=list)
    description: str | None = None
    location: str | None = None
    status: AppointmentStatus = AppointmentStatus.CONFIRMED

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AppointmentCreate(BaseModel):
    """Request model for creating an appointment."""

    title: str
    start: datetime
    end: datetime
    attendees: list[str] = Field(default_factory=list)
    description: str | None = None
    location: str | None = None


class TimeSlot(BaseModel):
    """Available time slot."""

    start: datetime
    end: datetime


class AvailabilityRequest(BaseModel):
    """Request model for checking availability."""

    start: datetime
    end: datetime
    slot_duration_minutes: int = 30


class AvailabilityResponse(BaseModel):
    """Response model for availability check."""

    available_slots: list[TimeSlot]
    total_slots: int


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """WebSocket chat request."""

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """WebSocket chat response."""

    message: str
    session_id: str
    appointments_changed: bool = False


class WebSocketMessage(BaseModel):
    """Generic WebSocket message wrapper."""

    type: str
    data: dict[str, Any]


class NotificationMessage(BaseModel):
    """Real-time notification message."""

    event: str  # appointment_created, appointment_cancelled, etc.
    data: dict[str, Any]

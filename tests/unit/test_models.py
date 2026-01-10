"""Unit tests for Pydantic models."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from agent_demos.demos.appointment_booking.models import (
    Appointment,
    AppointmentCreate,
    AppointmentStatus,
    AvailabilityRequest,
    AvailabilityResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    NotificationMessage,
    TimeSlot,
    WebSocketMessage,
)


class TestAppointmentStatus:
    """Tests for AppointmentStatus enum."""

    def test_status_values(self) -> None:
        """Test that all status values are correct."""
        assert AppointmentStatus.CONFIRMED == "confirmed"
        assert AppointmentStatus.CANCELLED == "cancelled"
        assert AppointmentStatus.PENDING == "pending"

    def test_status_is_string(self) -> None:
        """Test that status values are strings."""
        assert isinstance(AppointmentStatus.CONFIRMED, str)
        assert isinstance(AppointmentStatus.CANCELLED, str)
        assert isinstance(AppointmentStatus.PENDING, str)


class TestAppointment:
    """Tests for Appointment model."""

    def test_create_appointment(self) -> None:
        """Test creating an appointment with required fields."""
        now = datetime.utcnow()
        appointment = Appointment(
            id="test-123",
            title="Test Meeting",
            start=now,
            end=now + timedelta(hours=1),
        )
        assert appointment.id == "test-123"
        assert appointment.title == "Test Meeting"
        assert appointment.start == now
        assert appointment.end == now + timedelta(hours=1)
        assert appointment.attendees == []
        assert appointment.description is None
        assert appointment.location is None
        assert appointment.status == AppointmentStatus.CONFIRMED

    def test_create_appointment_with_all_fields(self) -> None:
        """Test creating an appointment with all fields."""
        now = datetime.utcnow()
        appointment = Appointment(
            id="test-456",
            title="Full Meeting",
            start=now,
            end=now + timedelta(hours=2),
            attendees=["alice@example.com", "bob@example.com"],
            description="A test meeting",
            location="Conference Room A",
            status=AppointmentStatus.PENDING,
        )
        assert appointment.id == "test-456"
        assert len(appointment.attendees) == 2
        assert "alice@example.com" in appointment.attendees
        assert appointment.description == "A test meeting"
        assert appointment.location == "Conference Room A"
        assert appointment.status == AppointmentStatus.PENDING

    def test_appointment_json_serialization(self) -> None:
        """Test JSON serialization of appointment."""
        now = datetime(2025, 1, 10, 14, 0, 0)
        appointment = Appointment(
            id="test-789",
            title="JSON Test",
            start=now,
            end=now + timedelta(hours=1),
        )
        json_data = appointment.model_dump(mode="json")
        assert json_data["id"] == "test-789"
        assert json_data["title"] == "JSON Test"
        assert isinstance(json_data["start"], str)
        assert "2025-01-10" in json_data["start"]

    def test_appointment_missing_required_fields(self) -> None:
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            Appointment(
                id="test",
                title="Test",
                # Missing start and end
            )  # type: ignore


class TestAppointmentCreate:
    """Tests for AppointmentCreate model."""

    def test_create_appointment_request(self) -> None:
        """Test creating an appointment create request."""
        now = datetime.utcnow()
        request = AppointmentCreate(
            title="New Meeting",
            start=now,
            end=now + timedelta(hours=1),
        )
        assert request.title == "New Meeting"
        assert request.attendees == []
        assert request.description is None
        assert request.location is None

    def test_create_appointment_request_with_optional_fields(self) -> None:
        """Test creating request with optional fields."""
        now = datetime.utcnow()
        request = AppointmentCreate(
            title="Full Meeting",
            start=now,
            end=now + timedelta(hours=1),
            attendees=["user@example.com"],
            description="Important meeting",
            location="Room 101",
        )
        assert len(request.attendees) == 1
        assert request.description == "Important meeting"
        assert request.location == "Room 101"


class TestTimeSlot:
    """Tests for TimeSlot model."""

    def test_create_time_slot(self) -> None:
        """Test creating a time slot."""
        now = datetime.utcnow()
        slot = TimeSlot(
            start=now,
            end=now + timedelta(minutes=30),
        )
        assert slot.start == now
        assert slot.end == now + timedelta(minutes=30)

    def test_time_slot_duration(self) -> None:
        """Test time slot duration calculation."""
        now = datetime.utcnow()
        slot = TimeSlot(
            start=now,
            end=now + timedelta(hours=1),
        )
        duration = slot.end - slot.start
        assert duration == timedelta(hours=1)


class TestAvailabilityRequest:
    """Tests for AvailabilityRequest model."""

    def test_create_availability_request(self) -> None:
        """Test creating an availability request."""
        now = datetime.utcnow()
        request = AvailabilityRequest(
            start=now,
            end=now + timedelta(days=1),
        )
        assert request.slot_duration_minutes == 30  # Default value

    def test_custom_slot_duration(self) -> None:
        """Test custom slot duration."""
        now = datetime.utcnow()
        request = AvailabilityRequest(
            start=now,
            end=now + timedelta(days=1),
            slot_duration_minutes=60,
        )
        assert request.slot_duration_minutes == 60


class TestAvailabilityResponse:
    """Tests for AvailabilityResponse model."""

    def test_create_availability_response(self) -> None:
        """Test creating an availability response."""
        now = datetime.utcnow()
        slots = [
            TimeSlot(start=now, end=now + timedelta(minutes=30)),
            TimeSlot(start=now + timedelta(hours=1), end=now + timedelta(hours=1, minutes=30)),
        ]
        response = AvailabilityResponse(
            available_slots=slots,
            total_slots=2,
        )
        assert len(response.available_slots) == 2
        assert response.total_slots == 2

    def test_empty_availability(self) -> None:
        """Test empty availability response."""
        response = AvailabilityResponse(
            available_slots=[],
            total_slots=0,
        )
        assert response.available_slots == []
        assert response.total_slots == 0


class TestChatMessage:
    """Tests for ChatMessage model."""

    def test_create_user_message(self) -> None:
        """Test creating a user chat message."""
        message = ChatMessage(
            role="user",
            content="Hello, I need help with scheduling.",
        )
        assert message.role == "user"
        assert message.content == "Hello, I need help with scheduling."
        assert isinstance(message.timestamp, datetime)

    def test_create_assistant_message(self) -> None:
        """Test creating an assistant chat message."""
        message = ChatMessage(
            role="assistant",
            content="I can help you with that!",
        )
        assert message.role == "assistant"
        assert message.content == "I can help you with that!"

    def test_invalid_role(self) -> None:
        """Test that invalid role raises validation error."""
        with pytest.raises(ValidationError):
            ChatMessage(
                role="invalid",
                content="Test",
            )

    def test_custom_timestamp(self) -> None:
        """Test setting custom timestamp."""
        custom_time = datetime(2025, 1, 10, 12, 0, 0)
        message = ChatMessage(
            role="user",
            content="Test",
            timestamp=custom_time,
        )
        assert message.timestamp == custom_time


class TestChatRequest:
    """Tests for ChatRequest model."""

    def test_create_chat_request(self) -> None:
        """Test creating a chat request."""
        request = ChatRequest(
            message="Hello",
        )
        assert request.message == "Hello"
        assert request.session_id is None

    def test_chat_request_with_session(self) -> None:
        """Test chat request with session ID."""
        request = ChatRequest(
            message="Hello",
            session_id="session-123",
        )
        assert request.session_id == "session-123"


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_create_chat_response(self) -> None:
        """Test creating a chat response."""
        response = ChatResponse(
            message="I can help!",
            session_id="session-123",
        )
        assert response.message == "I can help!"
        assert response.session_id == "session-123"
        assert response.appointments_changed is False  # Default

    def test_chat_response_with_changes(self) -> None:
        """Test chat response indicating appointment changes."""
        response = ChatResponse(
            message="Appointment booked!",
            session_id="session-123",
            appointments_changed=True,
        )
        assert response.appointments_changed is True


class TestWebSocketMessage:
    """Tests for WebSocketMessage model."""

    def test_create_websocket_message(self) -> None:
        """Test creating a WebSocket message."""
        message = WebSocketMessage(
            type="chat",
            data={"content": "Hello"},
        )
        assert message.type == "chat"
        assert message.data["content"] == "Hello"

    def test_complex_data_payload(self) -> None:
        """Test WebSocket message with complex data."""
        message = WebSocketMessage(
            type="notification",
            data={
                "event": "appointment_created",
                "appointment": {
                    "id": "123",
                    "title": "Meeting",
                },
            },
        )
        assert message.data["event"] == "appointment_created"
        assert message.data["appointment"]["id"] == "123"


class TestNotificationMessage:
    """Tests for NotificationMessage model."""

    def test_create_notification(self) -> None:
        """Test creating a notification message."""
        notification = NotificationMessage(
            event="appointment_created",
            data={"id": "123", "title": "New Meeting"},
        )
        assert notification.event == "appointment_created"
        assert notification.data["id"] == "123"

    def test_different_event_types(self) -> None:
        """Test different notification event types."""
        events = [
            "appointment_created",
            "appointment_cancelled",
            "appointment_updated",
            "calendar_synced",
        ]
        for event in events:
            notification = NotificationMessage(
                event=event,
                data={},
            )
            assert notification.event == event

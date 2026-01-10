"""Integration tests for Appointments REST API."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MockGoogleCalendarClient, MockSchedulingAgent


class TestListAppointments:
    """Tests for GET /api/appointments endpoint."""

    def test_list_appointments_empty(
        self,
        client: TestClient,
    ) -> None:
        """Test listing appointments when none exist."""
        response = client.get("/api/appointments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_appointments_with_events(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test listing appointments when some exist."""
        # Create events in mock calendar
        now = datetime.utcnow()
        mock_scheduling_agent.calendar.create_event(
            title="Test Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            attendees=["test@example.com"],
        )

        response = client.get("/api/appointments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Test Meeting"

    def test_list_appointments_with_date_range(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test listing appointments with date range filter."""
        now = datetime.utcnow()

        # Create events
        mock_scheduling_agent.calendar.create_event(
            title="Today Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        mock_scheduling_agent.calendar.create_event(
            title="Future Meeting",
            start=now + timedelta(days=7),
            end=now + timedelta(days=7, hours=1),
        )

        # Query with date range
        start = now.isoformat()
        end = (now + timedelta(days=2)).isoformat()

        response = client.get(f"/api/appointments?start={start}&end={end}")
        assert response.status_code == 200
        data = response.json()
        # Should only include today's meeting
        assert len(data) == 1
        assert data[0]["title"] == "Today Meeting"

    def test_list_appointments_with_max_results(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test limiting number of results."""
        now = datetime.utcnow()

        # Create multiple events
        for i in range(5):
            mock_scheduling_agent.calendar.create_event(
                title=f"Meeting {i}",
                start=now + timedelta(hours=i + 1),
                end=now + timedelta(hours=i + 2),
            )

        response = client.get("/api/appointments?max_results=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2


class TestCreateAppointment:
    """Tests for POST /api/appointments endpoint."""

    def test_create_appointment(
        self,
        client: TestClient,
    ) -> None:
        """Test creating a new appointment."""
        now = datetime.utcnow()
        appointment_data = {
            "title": "New Meeting",
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
        }

        response = client.post("/api/appointments", json=appointment_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Meeting"
        assert "id" in data
        assert data["attendees"] == []

    def test_create_appointment_with_attendees(
        self,
        client: TestClient,
    ) -> None:
        """Test creating appointment with attendees."""
        now = datetime.utcnow()
        appointment_data = {
            "title": "Team Meeting",
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "attendees": ["alice@example.com", "bob@example.com"],
        }

        response = client.post("/api/appointments", json=appointment_data)
        assert response.status_code == 201
        data = response.json()
        assert len(data["attendees"]) == 2
        assert "alice@example.com" in data["attendees"]

    def test_create_appointment_with_description(
        self,
        client: TestClient,
    ) -> None:
        """Test creating appointment with description."""
        now = datetime.utcnow()
        appointment_data = {
            "title": "Planning Meeting",
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "description": "Discuss Q1 goals",
        }

        response = client.post("/api/appointments", json=appointment_data)
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Discuss Q1 goals"

    def test_create_appointment_with_location(
        self,
        client: TestClient,
    ) -> None:
        """Test creating appointment with location."""
        now = datetime.utcnow()
        appointment_data = {
            "title": "On-site Meeting",
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "location": "Conference Room A",
        }

        response = client.post("/api/appointments", json=appointment_data)
        assert response.status_code == 201
        data = response.json()
        assert data["location"] == "Conference Room A"

    def test_create_appointment_missing_required_fields(
        self,
        client: TestClient,
    ) -> None:
        """Test creating appointment with missing required fields."""
        # Missing title
        appointment_data = {
            "start": datetime.utcnow().isoformat(),
            "end": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }

        response = client.post("/api/appointments", json=appointment_data)
        assert response.status_code == 422  # Validation error


class TestGetAppointment:
    """Tests for GET /api/appointments/{id} endpoint."""

    def test_get_appointment(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test getting a specific appointment."""
        now = datetime.utcnow()
        event = mock_scheduling_agent.calendar.create_event(
            title="Specific Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )

        response = client.get(f"/api/appointments/{event.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event.id
        assert data["title"] == "Specific Meeting"

    def test_get_appointment_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test getting a non-existent appointment."""
        response = client.get("/api/appointments/non-existent-id")
        assert response.status_code == 404


class TestDeleteAppointment:
    """Tests for DELETE /api/appointments/{id} endpoint."""

    def test_delete_appointment(
        self,
        client: TestClient,
        mock_scheduling_agent: MockSchedulingAgent,
    ) -> None:
        """Test deleting an appointment."""
        now = datetime.utcnow()
        event = mock_scheduling_agent.calendar.create_event(
            title="Meeting to Delete",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )

        response = client.delete(f"/api/appointments/{event.id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/appointments/{event.id}")
        assert get_response.status_code == 404

    def test_delete_appointment_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test deleting a non-existent appointment."""
        response = client.delete("/api/appointments/non-existent-id")
        assert response.status_code == 404


class TestAppointmentLifecycle:
    """Tests for full appointment lifecycle."""

    def test_create_read_delete_lifecycle(
        self,
        client: TestClient,
    ) -> None:
        """Test full create, read, delete lifecycle."""
        now = datetime.utcnow()

        # Create
        create_response = client.post("/api/appointments", json={
            "title": "Lifecycle Test Meeting",
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
        })
        assert create_response.status_code == 201
        appointment_id = create_response.json()["id"]

        # Read
        get_response = client.get(f"/api/appointments/{appointment_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "Lifecycle Test Meeting"

        # List
        list_response = client.get("/api/appointments")
        assert list_response.status_code == 200
        ids = [a["id"] for a in list_response.json()]
        assert appointment_id in ids

        # Delete
        delete_response = client.delete(f"/api/appointments/{appointment_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        get_after_delete = client.get(f"/api/appointments/{appointment_id}")
        assert get_after_delete.status_code == 404

    def test_multiple_appointments(
        self,
        client: TestClient,
    ) -> None:
        """Test managing multiple appointments."""
        now = datetime.utcnow()
        appointment_ids = []

        # Create multiple appointments
        for i in range(3):
            response = client.post("/api/appointments", json={
                "title": f"Meeting {i}",
                "start": (now + timedelta(hours=i + 1)).isoformat(),
                "end": (now + timedelta(hours=i + 2)).isoformat(),
            })
            assert response.status_code == 201
            appointment_ids.append(response.json()["id"])

        # List all
        list_response = client.get("/api/appointments")
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data) == 3

        # Delete first
        client.delete(f"/api/appointments/{appointment_ids[0]}")

        # List again
        list_response = client.get("/api/appointments")
        assert len(list_response.json()) == 2


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestCalendarAvailability:
    """Tests for calendar availability endpoint."""

    def test_get_availability(self, client: TestClient) -> None:
        """Test getting availability."""
        response = client.get("/api/calendar/availability")
        assert response.status_code == 200
        data = response.json()
        assert "available_slots" in data
        assert "total_slots" in data

    def test_get_availability_with_date_range(
        self,
        client: TestClient,
    ) -> None:
        """Test getting availability with date range."""
        now = datetime.utcnow()
        start = now.isoformat()
        end = (now + timedelta(days=1)).isoformat()

        response = client.get(
            f"/api/calendar/availability?start={start}&end={end}"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["available_slots"], list)

    def test_get_availability_with_slot_duration(
        self,
        client: TestClient,
    ) -> None:
        """Test getting availability with custom slot duration."""
        response = client.get(
            "/api/calendar/availability?slot_duration_minutes=60"
        )
        assert response.status_code == 200
        data = response.json()
        assert "available_slots" in data

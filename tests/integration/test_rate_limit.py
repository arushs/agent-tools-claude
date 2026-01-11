"""Integration tests for rate limiting."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent_demos.demos.appointment_booking.app import AppState, create_app
from agent_demos.demos.appointment_booking.config import Settings
from agent_demos.demos.appointment_booking.rate_limit import RateLimitConfig, RateLimiter

from tests.conftest import MockSchedulingAgent


class TestHttpRateLimiting:
    """Tests for HTTP rate limiting middleware."""

    @pytest.fixture
    def rate_limited_client(self) -> TestClient:
        """Create a test client with aggressive rate limiting."""
        settings = Settings(
            anthropic_api_key="test-key",
            openai_api_key="test-key",
            rate_limit_enabled=True,
            rate_limit_http_per_minute=60,
            rate_limit_http_burst=3,
        )
        app = create_app(settings)

        # Manually set up app state to avoid needing lifespan
        rate_limiter = RateLimiter(
            RateLimitConfig(
                http_requests_per_minute=60,
                http_burst_limit=3,
                ws_messages_per_minute=30,
                ws_burst_limit=5,
                enabled=True,
            )
        )
        app_state = AppState(settings, rate_limiter)
        app_state._scheduling_agent = MockSchedulingAgent()  # type: ignore
        app.state.app_state = app_state

        return TestClient(app)

    def test_requests_within_limit(self, rate_limited_client: TestClient) -> None:
        """Test requests within rate limit are allowed."""
        for _ in range(3):
            response = rate_limited_client.get("/api/appointments")
            assert response.status_code == 200

    def test_requests_exceed_limit(self, rate_limited_client: TestClient) -> None:
        """Test requests exceeding rate limit are blocked."""
        # Exhaust burst limit
        for _ in range(3):
            response = rate_limited_client.get("/api/appointments")
            assert response.status_code == 200

        # Next request should be rate limited
        response = rate_limited_client.get("/api/appointments")
        assert response.status_code == 429
        assert response.json()["detail"] == "Rate limit exceeded"
        assert "Retry-After" in response.headers

    def test_health_excluded_from_rate_limit(
        self, rate_limited_client: TestClient
    ) -> None:
        """Test health endpoint is excluded from rate limiting."""
        # Exhaust rate limit on regular endpoint
        for _ in range(3):
            rate_limited_client.get("/api/appointments")

        # Regular endpoint should be blocked
        response = rate_limited_client.get("/api/appointments")
        assert response.status_code == 429

        # Health endpoint should still work
        response = rate_limited_client.get("/health")
        assert response.status_code == 200

    def test_rate_limit_header(self, rate_limited_client: TestClient) -> None:
        """Test rate limit header is included in response."""
        response = rate_limited_client.get("/api/appointments")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "60"


class TestRateLimitingDisabled:
    """Tests for disabled rate limiting."""

    @pytest.fixture
    def unlimited_client(self) -> TestClient:
        """Create a test client with rate limiting disabled."""
        settings = Settings(
            anthropic_api_key="test-key",
            openai_api_key="test-key",
            rate_limit_enabled=False,
            rate_limit_http_burst=1,  # Would block after 1 if enabled
        )
        app = create_app(settings)

        # Manually set up app state
        rate_limiter = RateLimiter(
            RateLimitConfig(
                http_burst_limit=1,
                enabled=False,
            )
        )
        app_state = AppState(settings, rate_limiter)
        app_state._scheduling_agent = MockSchedulingAgent()  # type: ignore
        app.state.app_state = app_state

        return TestClient(app)

    def test_unlimited_requests(self, unlimited_client: TestClient) -> None:
        """Test many requests allowed when rate limiting disabled."""
        for _ in range(10):
            response = unlimited_client.get("/api/appointments")
            assert response.status_code == 200


class TestRateLimitRecovery:
    """Tests for rate limit recovery over time."""

    def test_rate_limit_recovers(self) -> None:
        """Test rate limit recovers over time."""
        import time

        settings = Settings(
            anthropic_api_key="test-key",
            openai_api_key="test-key",
            rate_limit_enabled=True,
            rate_limit_http_per_minute=60,  # 1 per second - slow refill
            rate_limit_http_burst=2,
        )
        app = create_app(settings)

        # Create rate limiter with slow refill
        rate_limiter = RateLimiter(
            RateLimitConfig(
                http_requests_per_minute=60,  # 1 per second
                http_burst_limit=2,
                enabled=True,
            )
        )
        app_state = AppState(settings, rate_limiter)
        app_state._scheduling_agent = MockSchedulingAgent()  # type: ignore
        app.state.app_state = app_state

        client = TestClient(app)

        # Exhaust burst immediately
        client.get("/api/appointments")
        client.get("/api/appointments")

        # Third request should be rate limited
        response = client.get("/api/appointments")
        assert response.status_code == 429

        # Wait 1.5 seconds for 1 token to refill (1 token/sec)
        time.sleep(1.5)

        # Should be allowed again
        response = client.get("/api/appointments")
        assert response.status_code == 200

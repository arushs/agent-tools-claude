"""Unit tests for rate limiting."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_demos.demos.appointment_booking.rate_limit import (
    RateLimitConfig,
    RateLimiter,
    TokenBucket,
    check_ws_rate_limit,
    get_client_ip,
    get_ws_client_ip,
)


class TestTokenBucket:
    """Tests for TokenBucket."""

    def test_init_with_full_capacity(self) -> None:
        """Test bucket initializes with full capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.tokens == 10.0
        assert bucket.capacity == 10

    def test_consume_success(self) -> None:
        """Test successful token consumption."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.consume(1) is True
        assert bucket.tokens == 9.0

    def test_consume_multiple(self) -> None:
        """Test consuming multiple tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.consume(5) is True
        assert bucket.tokens == 5.0

    def test_consume_fails_when_empty(self) -> None:
        """Test consumption fails when not enough tokens."""
        bucket = TokenBucket(capacity=2, refill_rate=1.0)
        assert bucket.consume(1) is True
        assert bucket.consume(1) is True
        assert bucket.consume(1) is False

    def test_refill_over_time(self) -> None:
        """Test tokens refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/second
        bucket.tokens = 0.0
        bucket.last_refill = time.time() - 0.5  # Half second ago

        # Should have refilled ~5 tokens
        result = bucket.consume(1)
        assert result is True
        assert bucket.tokens >= 3.5  # Allow some variance

    def test_refill_caps_at_capacity(self) -> None:
        """Test refill doesn't exceed capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=100.0)
        bucket.last_refill = time.time() - 1.0  # 1 second ago

        bucket.consume(1)
        assert bucket.tokens <= bucket.capacity

    def test_time_until_available(self) -> None:
        """Test calculating time until tokens available."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)  # 2 tokens/second
        bucket.tokens = 0.0

        wait_time = bucket.time_until_available(1)
        assert 0.4 <= wait_time <= 0.6  # About 0.5 seconds

    def test_time_until_available_immediate(self) -> None:
        """Test time is 0 when tokens available."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.time_until_available(1) == 0.0


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_init_default_config(self) -> None:
        """Test initialization with default config."""
        limiter = RateLimiter()
        assert limiter.config.http_requests_per_minute == 60
        assert limiter.config.ws_messages_per_minute == 30

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = RateLimitConfig(
            http_requests_per_minute=120,
            http_burst_limit=20,
        )
        limiter = RateLimiter(config)
        assert limiter.config.http_requests_per_minute == 120
        assert limiter.config.http_burst_limit == 20

    def test_check_http_allowed(self) -> None:
        """Test HTTP request is allowed."""
        limiter = RateLimiter(RateLimitConfig(http_burst_limit=10))
        allowed, retry_after = limiter.check_http("192.168.1.1")
        assert allowed is True
        assert retry_after == 0.0

    def test_check_http_rate_limited(self) -> None:
        """Test HTTP request is rate limited after burst."""
        config = RateLimitConfig(
            http_burst_limit=3,
            http_requests_per_minute=60,
        )
        limiter = RateLimiter(config)

        # Exhaust burst limit
        for _ in range(3):
            allowed, _ = limiter.check_http("192.168.1.1")
            assert allowed is True

        # Next request should be rate limited
        allowed, retry_after = limiter.check_http("192.168.1.1")
        assert allowed is False
        assert retry_after > 0

    def test_check_http_different_clients(self) -> None:
        """Test different clients have separate rate limits."""
        config = RateLimitConfig(http_burst_limit=2)
        limiter = RateLimiter(config)

        # Client 1 exhausts limit
        limiter.check_http("client1")
        limiter.check_http("client1")
        allowed, _ = limiter.check_http("client1")
        assert allowed is False

        # Client 2 still has quota
        allowed, _ = limiter.check_http("client2")
        assert allowed is True

    def test_check_ws_allowed(self) -> None:
        """Test WebSocket message is allowed."""
        limiter = RateLimiter(RateLimitConfig(ws_burst_limit=5))
        allowed, retry_after = limiter.check_ws("session-1")
        assert allowed is True
        assert retry_after == 0.0

    def test_check_ws_rate_limited(self) -> None:
        """Test WebSocket message is rate limited after burst."""
        config = RateLimitConfig(
            ws_burst_limit=2,
            ws_messages_per_minute=30,
        )
        limiter = RateLimiter(config)

        # Exhaust burst limit
        for _ in range(2):
            allowed, _ = limiter.check_ws("session-1")
            assert allowed is True

        # Next message should be rate limited
        allowed, retry_after = limiter.check_ws("session-1")
        assert allowed is False
        assert retry_after > 0

    def test_disabled_rate_limiting(self) -> None:
        """Test rate limiting can be disabled."""
        config = RateLimitConfig(
            enabled=False,
            http_burst_limit=1,
            ws_burst_limit=1,
        )
        limiter = RateLimiter(config)

        # Should always be allowed when disabled
        for _ in range(100):
            allowed, _ = limiter.check_http("client")
            assert allowed is True

            allowed, _ = limiter.check_ws("session")
            assert allowed is True

    def test_reset_specific_key(self) -> None:
        """Test resetting rate limit for specific key."""
        config = RateLimitConfig(http_burst_limit=2)
        limiter = RateLimiter(config)

        # Exhaust limit
        limiter.check_http("client1")
        limiter.check_http("client1")

        # Reset
        limiter.reset("client1")

        # Should be allowed again
        allowed, _ = limiter.check_http("client1")
        assert allowed is True

    def test_reset_all(self) -> None:
        """Test resetting all rate limits."""
        config = RateLimitConfig(http_burst_limit=1, ws_burst_limit=1)
        limiter = RateLimiter(config)

        # Exhaust limits for multiple clients
        limiter.check_http("client1")
        limiter.check_http("client2")
        limiter.check_ws("session1")

        # Reset all
        limiter.reset()

        # All should be allowed again
        allowed, _ = limiter.check_http("client1")
        assert allowed is True
        allowed, _ = limiter.check_http("client2")
        assert allowed is True
        allowed, _ = limiter.check_ws("session1")
        assert allowed is True


class TestGetClientIp:
    """Tests for get_client_ip."""

    def test_direct_client(self) -> None:
        """Test getting IP from direct client."""
        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.1"

        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_x_forwarded_for(self) -> None:
        """Test getting IP from X-Forwarded-For header."""
        request = MagicMock()
        request.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
        request.client.host = "192.168.1.1"

        ip = get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_x_real_ip(self) -> None:
        """Test getting IP from X-Real-IP header."""
        request = MagicMock()
        request.headers = {"x-real-ip": "10.0.0.1"}
        request.client.host = "192.168.1.1"

        ip = get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_x_forwarded_for_priority(self) -> None:
        """Test X-Forwarded-For takes priority over X-Real-IP."""
        request = MagicMock()
        request.headers = {
            "x-forwarded-for": "10.0.0.1",
            "x-real-ip": "10.0.0.2",
        }
        request.client.host = "192.168.1.1"

        ip = get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_no_client(self) -> None:
        """Test fallback when no client info."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = get_client_ip(request)
        assert ip == "unknown"


class TestGetWsClientIp:
    """Tests for get_ws_client_ip."""

    def test_direct_client(self) -> None:
        """Test getting IP from direct WebSocket client."""
        websocket = MagicMock()
        websocket.headers = {}
        websocket.client.host = "192.168.1.1"

        ip = get_ws_client_ip(websocket)
        assert ip == "192.168.1.1"

    def test_x_forwarded_for(self) -> None:
        """Test getting IP from X-Forwarded-For header."""
        websocket = MagicMock()
        websocket.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
        websocket.client.host = "192.168.1.1"

        ip = get_ws_client_ip(websocket)
        assert ip == "10.0.0.1"


class TestCheckWsRateLimit:
    """Tests for check_ws_rate_limit helper."""

    @pytest.mark.asyncio
    async def test_allowed(self) -> None:
        """Test message is allowed."""
        websocket = MagicMock()
        websocket.send_json = AsyncMock()

        limiter = RateLimiter(RateLimitConfig(ws_burst_limit=5))

        result = await check_ws_rate_limit(websocket, limiter, "session-1")

        assert result is True
        websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_rate_limited(self) -> None:
        """Test message is rate limited."""
        websocket = MagicMock()
        websocket.send_json = AsyncMock()

        config = RateLimitConfig(ws_burst_limit=1, ws_messages_per_minute=30)
        limiter = RateLimiter(config)

        # First message allowed
        await check_ws_rate_limit(websocket, limiter, "session-1")

        # Second message rate limited
        result = await check_ws_rate_limit(websocket, limiter, "session-1")

        assert result is False
        websocket.send_json.assert_called_once()

        # Verify error message format
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["code"] == "rate_limit_exceeded"
        assert "retry_after" in call_args

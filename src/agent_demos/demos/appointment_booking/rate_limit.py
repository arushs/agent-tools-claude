"""Rate limiting for HTTP and WebSocket endpoints."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import Request, WebSocket
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.types import ASGIApp


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # HTTP rate limits
    http_requests_per_minute: int = 60
    http_burst_limit: int = 10

    # WebSocket rate limits
    ws_messages_per_minute: int = 30
    ws_burst_limit: int = 5

    # Enable/disable
    enabled: bool = True


@dataclass
class TokenBucket:
    """Token bucket for rate limiting with burst support."""

    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Initialize tokens to capacity."""
        self.tokens = float(self.capacity)

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if tokens were consumed, False if rate limited.
        """
        now = time.time()
        elapsed = now - self.last_refill
        self.last_refill = now

        # Refill tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until tokens are available.

        Args:
            tokens: Number of tokens needed.

        Returns:
            Seconds until tokens are available, or 0 if available now.
        """
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """In-memory rate limiter using token bucket algorithm."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        """Initialize the rate limiter.

        Args:
            config: Rate limit configuration.
        """
        self.config = config or RateLimitConfig()
        self._http_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=self.config.http_burst_limit,
                refill_rate=self.config.http_requests_per_minute / 60.0,
            )
        )
        self._ws_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=self.config.ws_burst_limit,
                refill_rate=self.config.ws_messages_per_minute / 60.0,
            )
        )

    def check_http(self, key: str) -> tuple[bool, float]:
        """Check if an HTTP request is allowed.

        Args:
            key: Unique identifier for the client (e.g., IP address).

        Returns:
            Tuple of (allowed, retry_after_seconds).
        """
        if not self.config.enabled:
            return True, 0.0

        bucket = self._http_buckets[key]
        allowed = bucket.consume()
        retry_after = 0.0 if allowed else bucket.time_until_available()
        return allowed, retry_after

    def check_ws(self, key: str) -> tuple[bool, float]:
        """Check if a WebSocket message is allowed.

        Args:
            key: Unique identifier for the client (e.g., session ID).

        Returns:
            Tuple of (allowed, retry_after_seconds).
        """
        if not self.config.enabled:
            return True, 0.0

        bucket = self._ws_buckets[key]
        allowed = bucket.consume()
        retry_after = 0.0 if allowed else bucket.time_until_available()
        return allowed, retry_after

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit buckets.

        Args:
            key: Specific key to reset, or None to reset all.
        """
        if key is None:
            self._http_buckets.clear()
            self._ws_buckets.clear()
        else:
            self._http_buckets.pop(key, None)
            self._ws_buckets.pop(key, None)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies.

    Args:
        request: The HTTP request.

    Returns:
        Client IP address.
    """
    # Check X-Forwarded-For header (for requests behind proxy/load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client host
    if request.client:
        return request.client.host
    return "unknown"


def get_ws_client_ip(websocket: WebSocket) -> str:
    """Extract client IP from WebSocket connection.

    Args:
        websocket: The WebSocket connection.

    Returns:
        Client IP address.
    """
    # Check X-Forwarded-For header
    forwarded_for = websocket.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = websocket.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client host
    if websocket.client:
        return websocket.client.host
    return "unknown"


class RateLimitMiddleware:
    """Pure ASGI middleware for HTTP rate limiting.

    Note: Uses pure ASGI instead of BaseHTTPMiddleware to properly support WebSocket.
    """

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter,
        key_func: Callable[[Request], str] | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            rate_limiter: The rate limiter instance.
            key_func: Function to extract rate limit key from request.
            exclude_paths: Paths to exclude from rate limiting.
        """
        self.app = app
        self.rate_limiter = rate_limiter
        self.key_func = key_func or get_client_ip
        self.exclude_paths = set(exclude_paths or ["/health", "/healthz", "/"])

    async def __call__(self, scope, receive, send) -> None:
        """Process the request with rate limiting."""
        # Pass through non-HTTP requests (including WebSocket)
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)

        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Skip rate limiting for WebSocket upgrade requests
        if request.headers.get("upgrade", "").lower() == "websocket":
            await self.app(scope, receive, send)
            return

        key = self.key_func(request)
        allowed, retry_after = self.rate_limiter.check_http(key)

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
            await response(scope, receive, send)
            return

        # Add rate limit headers via send wrapper
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((
                    b"x-ratelimit-limit",
                    str(self.rate_limiter.config.http_requests_per_minute).encode(),
                ))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


async def check_ws_rate_limit(
    websocket: WebSocket,
    rate_limiter: RateLimiter,
    session_id: str,
) -> bool:
    """Check WebSocket message rate limit and send error if exceeded.

    Args:
        websocket: The WebSocket connection.
        rate_limiter: The rate limiter instance.
        session_id: The session ID for rate limiting.

    Returns:
        True if message is allowed, False if rate limited.
    """
    allowed, retry_after = rate_limiter.check_ws(session_id)

    if not allowed:
        await websocket.send_json({
            "type": "error",
            "code": "rate_limit_exceeded",
            "message": "Rate limit exceeded. Please slow down.",
            "retry_after": int(retry_after) + 1,
        })
        return False

    return True

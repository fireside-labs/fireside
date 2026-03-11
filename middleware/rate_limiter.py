"""
middleware/rate_limiter.py — Token-bucket rate limiter for Valhalla Bifrost V2.

FastAPI middleware that enforces per-route, per-IP rate limits.
Returns 429 Too Many Requests with Retry-After header when exceeded.

Usage in bifrost.py:
    from middleware.rate_limiter import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, config=config)
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = logging.getLogger("heimdall.rate_limiter")

# ---------------------------------------------------------------------------
# Default route limits: (max_requests, window_seconds)
# ---------------------------------------------------------------------------

DEFAULT_LIMITS: dict[str, tuple[int, int]] = {
    "POST /api/v1/model-switch":          (5, 60),
    "POST /model-switch":                 (5, 60),    # plugin route
    "PUT /api/v1/config":                 (2, 60),
    "POST /api/v1/hypotheses/generate":   (3, 60),
    "POST /api/v1/mesh/join-token":       (5, 60),
    "POST /api/v1/mesh/announce":         (10, 60),
    "POST /api/v1/plugins/install":       (5, 60),
    "POST /api/v1/reflect":              (3, 60),
}

# Catch-all for any POST not explicitly listed
_DEFAULT_POST_LIMIT = (30, 60)

# No limit on GET requests by default
_DEFAULT_GET_LIMIT = (120, 60)


# ---------------------------------------------------------------------------
# Token bucket implementation
# ---------------------------------------------------------------------------

class TokenBucket:
    """Simple token bucket rate limiter."""

    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill")

    def __init__(self, capacity: int, window_seconds: int):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = capacity / window_seconds  # tokens per second
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Try to consume a token. Returns True if allowed, False if rate limited."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    @property
    def retry_after(self) -> int:
        """Seconds until a token is available."""
        if self.tokens >= 1.0:
            return 0
        return max(1, int((1.0 - self.tokens) / self.refill_rate) + 1)


# ---------------------------------------------------------------------------
# Bucket registry
# ---------------------------------------------------------------------------

class BucketRegistry:
    """Manages token buckets keyed by (route_key, client_ip)."""

    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}
        self._cleanup_counter = 0
        self._cleanup_interval = 100  # every N requests

    def get_or_create(self, route_key: str, client_ip: str,
                      capacity: int, window: int) -> TokenBucket:
        key = f"{route_key}:{client_ip}"
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(capacity, window)

        # Periodic cleanup of stale buckets
        self._cleanup_counter += 1
        if self._cleanup_counter >= self._cleanup_interval:
            self._cleanup()
            self._cleanup_counter = 0

        return self._buckets[key]

    def _cleanup(self):
        """Remove buckets that haven't been used in 5 minutes."""
        now = time.monotonic()
        stale = [
            k for k, b in self._buckets.items()
            if now - b.last_refill > 300
        ]
        for k in stale:
            del self._buckets[k]
        if stale:
            log.debug("[rate_limiter] Cleaned %d stale buckets", len(stale))

    def stats(self) -> dict:
        """Return stats about the bucket registry."""
        return {
            "total_buckets": len(self._buckets),
            "requests_since_cleanup": self._cleanup_counter,
        }


# ---------------------------------------------------------------------------
# FastAPI Middleware
# ---------------------------------------------------------------------------

_registry = BucketRegistry()

# Routes exempt from rate limiting
_EXEMPT_ROUTES = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces per-route rate limits."""

    def __init__(self, app, config: Optional[dict] = None):
        super().__init__(app)
        self._limits = dict(DEFAULT_LIMITS)

        # Load custom limits from config if available
        if config:
            custom = config.get("rate_limits", {})
            for route_key, limit in custom.items():
                if isinstance(limit, dict):
                    self._limits[route_key] = (
                        limit.get("max", 30),
                        limit.get("window", 60),
                    )

        log.info("[rate_limiter] Initialized with %d route limits", len(self._limits))

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Skip exempt routes
        if path in _EXEMPT_ROUTES:
            return await call_next(request)

        # Skip GET requests unless explicitly limited
        route_key = f"{method} {path}"
        if route_key in self._limits:
            capacity, window = self._limits[route_key]
        elif method == "GET":
            capacity, window = _DEFAULT_GET_LIMIT
        elif method in ("POST", "PUT", "DELETE", "PATCH"):
            capacity, window = _DEFAULT_POST_LIMIT
        else:
            return await call_next(request)

        # Get client IP
        client_ip = _get_client_ip(request)

        # Check rate limit
        bucket = _registry.get_or_create(route_key, client_ip, capacity, window)
        if not bucket.consume():
            retry_after = bucket.retry_after
            log.warning(
                "[rate_limiter] 429 → %s %s from %s (retry in %ds)",
                method, path, client_ip, retry_after
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "too_many_requests",
                    "detail": f"Rate limit exceeded for {method} {path}",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For if present."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ---------------------------------------------------------------------------
# Stats endpoint helper
# ---------------------------------------------------------------------------

def get_rate_limit_stats() -> dict:
    """Return rate limiter statistics for monitoring."""
    return {
        "limits": {k: {"max": v[0], "window_seconds": v[1]}
                   for k, v in DEFAULT_LIMITS.items()},
        "registry": _registry.stats(),
    }

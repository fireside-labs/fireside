"""
rate_limiter.py -- Token bucket rate limiter for Bifrost routes.

Per-route, per-source-IP buckets. Thread-safe.

Default limits (overridable via config):
    /critique      → 10 req/min   (inference-heavy)
    /route-message → 30 req/min
    /snapshot      → 5 req/min
    /absorb        → 5 req/min
    default        → 60 req/min   (generous for everything else)

Usage:
    from rate_limiter import RateLimiter
    _rl = RateLimiter(config)

    allowed, info = _rl.check("/critique", client_ip)
    if not allowed:
        _json_respond(handler, 429, {"error": "rate limit", **info})
        return

GET /rate-limit-status via bifrost_local exposes all bucket states.
"""

import threading
import time
import logging

log = logging.getLogger("rate_limiter")

# Default limits: requests per minute per source IP
_DEFAULT_LIMITS: dict[str, int] = {
    "/critique":      10,
    "/route-message": 30,
    "/snapshot":      5,
    "/absorb":        5,
    "/absorb/release": 10,
    "_default":       60,
}


class _Bucket:
    """Token bucket for one (route, ip) pair."""
    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill", "_lock")

    def __init__(self, capacity: int):
        self.capacity    = capacity
        self.tokens      = float(capacity)
        self.refill_rate = capacity / 60.0   # tokens per second
        self.last_refill = time.monotonic()
        self._lock       = threading.Lock()

    def consume(self) -> tuple[bool, dict]:
        """Try to consume one token. Returns (allowed, info_dict)."""
        with self._lock:
            now    = time.monotonic()
            elapsed = now - self.last_refill
            # Refill
            self.tokens = min(self.capacity,
                              self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True, {
                    "tokens_remaining": int(self.tokens),
                    "capacity":         self.capacity,
                    "retry_after_s":    0,
                }
            else:
                wait = (1.0 - self.tokens) / self.refill_rate
                return False, {
                    "tokens_remaining": 0,
                    "capacity":         self.capacity,
                    "retry_after_s":    round(wait, 1),
                }


class RateLimiter:
    """
    Thread-safe per-route, per-IP rate limiter.
    Buckets are created lazily and pruned every 5 minutes.
    """

    def __init__(self, config: dict = None):
        # Allow config to override limits: {"rate_limits": {"/critique": 20}}
        self._limits = dict(_DEFAULT_LIMITS)
        if config and "rate_limits" in config:
            self._limits.update(config["rate_limits"])
            log.info("[rate_limiter] Custom limits: %s", config["rate_limits"])

        # {(route, ip): _Bucket}
        self._buckets: dict[tuple[str, str], _Bucket] = {}
        self._lock    = threading.Lock()
        self._last_prune = time.monotonic()

    def _get_bucket(self, route: str, ip: str) -> _Bucket:
        key      = (route, ip)
        capacity = self._limits.get(route, self._limits["_default"])
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = _Bucket(capacity)
            return self._buckets[key]

    def check(self, route: str, client_ip: str) -> tuple[bool, dict]:
        """
        Check rate limit for this route + IP.
        Returns (allowed: bool, info: dict).
        """
        self._maybe_prune()
        bucket = self._get_bucket(route, client_ip)
        allowed, info = bucket.consume()
        if not allowed:
            log.warning("[rate_limiter] 429 %s from %s — retry in %.1fs",
                        route, client_ip, info["retry_after_s"])
        return allowed, {**info, "route": route, "ip": client_ip}

    def status(self) -> dict:
        """Snapshot of all active buckets — for GET /rate-limit-status."""
        with self._lock:
            result = {}
            for (route, ip), bucket in self._buckets.items():
                key = f"{route}|{ip}"
                result[key] = {
                    "route":    route,
                    "ip":       ip,
                    "tokens":   round(bucket.tokens, 2),
                    "capacity": bucket.capacity,
                    "rpm_limit": bucket.capacity,
                }
            return {
                "buckets":      result,
                "bucket_count": len(result),
                "limits":       {k: v for k, v in self._limits.items()
                                 if k != "_default"},
                "default_rpm":  self._limits["_default"],
            }

    def _maybe_prune(self):
        """Remove buckets idle > 5 minutes to keep memory bounded."""
        now = time.monotonic()
        if now - self._last_prune < 300:
            return
        with self._lock:
            cutoff = now - 300
            stale  = [k for k, b in self._buckets.items()
                      if b.last_refill < cutoff]
            for k in stale:
                del self._buckets[k]
            if stale:
                log.debug("[rate_limiter] Pruned %d stale buckets", len(stale))
            self._last_prune = now


# Module-level singleton — initialized by bifrost_local
_instance: RateLimiter | None = None


def init(config: dict):
    global _instance
    _instance = RateLimiter(config)
    return _instance


def get() -> RateLimiter | None:
    return _instance

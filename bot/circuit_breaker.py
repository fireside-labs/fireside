"""
circuit_breaker.py -- Per-node circuit breaker for Bifrost mesh outbound calls.

Pattern: CLOSED → (N failures) → OPEN → (timeout) → HALF-OPEN → (success) → CLOSED
                                                                 → (failure) → OPEN

Usage:
    from circuit_breaker import breaker, call

    # Wrap any outbound HTTP call:
    result = call("freya", lambda: _get("http://100.102.105.3:8765/memory-query?q=foo"))

    # Check state:
    breaker("thor").state   # "CLOSED" | "OPEN" | "HALF_OPEN"

    # All states:
    from circuit_breaker import all_states
    all_states()  # {"freya": {...}, "heimdall": {...}}
"""

import logging
import threading
import time
from typing import Callable, Any

log = logging.getLogger("circuit_breaker")

# Tuning constants
_FAILURE_THRESHOLD  = 3       # consecutive failures to trip OPEN
_OPEN_TIMEOUT_SEC   = 60      # seconds before trying HALF-OPEN
_HALF_OPEN_MAX      = 1       # probe requests allowed in HALF-OPEN


class CircuitBreaker:
    """Thread-safe circuit breaker for a single target node."""

    CLOSED    = "CLOSED"
    OPEN      = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, name: str):
        self.name             = name
        self._state           = self.CLOSED
        self._failures        = 0
        self._last_failure_ts = 0.0
        self._half_open_in    = 0
        self._total_calls     = 0
        self._total_failures  = 0
        self._total_successes = 0
        self._lock            = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._get_state()

    def _get_state(self) -> str:
        """Internal: check if OPEN timer has expired → transition to HALF_OPEN."""
        if self._state == self.OPEN:
            if time.time() - self._last_failure_ts >= _OPEN_TIMEOUT_SEC:
                log.info("[cb:%s] OPEN → HALF_OPEN (probe allowed)", self.name)
                self._state = self.HALF_OPEN
                self._half_open_in = 0
        return self._state

    def allow_request(self) -> bool:
        """Return True if this call should proceed."""
        with self._lock:
            state = self._get_state()
            if state == self.CLOSED:
                return True
            if state == self.HALF_OPEN and self._half_open_in < _HALF_OPEN_MAX:
                self._half_open_in += 1
                return True
            return False     # OPEN or HALF_OPEN probe quota exhausted

    def record_success(self):
        with self._lock:
            self._total_calls     += 1
            self._total_successes += 1
            if self._state in (self.HALF_OPEN, self.OPEN):
                log.info("[cb:%s] %s → CLOSED (probe succeeded)", self.name, self._state)
            self._state    = self.CLOSED
            self._failures = 0

    def record_failure(self, exc: Exception = None):
        with self._lock:
            self._total_calls   += 1
            self._total_failures += 1
            self._failures       += 1
            self._last_failure_ts = time.time()
            if self._state == self.HALF_OPEN:
                log.warning("[cb:%s] HALF_OPEN probe failed → OPEN", self.name)
                self._state = self.OPEN
            elif self._failures >= _FAILURE_THRESHOLD:
                if self._state != self.OPEN:
                    log.warning("[cb:%s] %d consecutive failures → OPEN (exc: %s)",
                                self.name, self._failures, exc)
                self._state = self.OPEN

    def status(self) -> dict:
        with self._lock:
            state = self._get_state()
            remaining = 0
            if state == self.OPEN:
                remaining = max(0, _OPEN_TIMEOUT_SEC -
                                (time.time() - self._last_failure_ts))
            return {
                "node":             self.name,
                "state":            state,
                "consecutive_fails": self._failures,
                "open_remaining_s": round(remaining),
                "total_calls":      self._total_calls,
                "total_failures":   self._total_failures,
                "total_successes":  self._total_successes,
                "failure_rate":     round(self._total_failures / max(1, self._total_calls), 3),
            }


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------
_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def breaker(node: str) -> CircuitBreaker:
    """Get-or-create the CircuitBreaker for a node."""
    with _registry_lock:
        if node not in _breakers:
            _breakers[node] = CircuitBreaker(node)
        return _breakers[node]


def all_states() -> dict:
    """Snapshot of all breaker states — used by GET /circuit-status."""
    with _registry_lock:
        return {name: cb.status() for name, cb in _breakers.items()}


def call(node: str, fn: Callable, fallback: Any = None) -> Any:
    """
    Execute fn() through the circuit breaker for node.
    Raises on failure (caller decides whether to use fallback).
    Returns fallback if circuit is OPEN.
    """
    cb = breaker(node)
    if not cb.allow_request():
        log.warning("[cb:%s] Circuit OPEN — fast-fail, not calling", node)
        if fallback is not None:
            return fallback
        raise ConnectionError(f"Circuit breaker OPEN for node '{node}'")
    try:
        result = fn()
        cb.record_success()
        return result
    except Exception as exc:
        cb.record_failure(exc)
        raise

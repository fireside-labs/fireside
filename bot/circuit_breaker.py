# -*- coding: utf-8 -*-
"""
circuit_breaker.py -- CLOSED/OPEN/HALF-OPEN state machine for outbound HTTP.

Compatible with Thor's implementation. Trips after N failures,
recovers after a cooldown period with a single test request.

Usage:
    cb = CircuitBreaker("freya-memory")
    result = cb.call(lambda: urllib.request.urlopen(req, timeout=10))
"""

import logging
import threading
import time
from enum import Enum

log = logging.getLogger("bifrost")


class State(Enum):
    CLOSED = "closed"        # normal operation
    OPEN = "open"            # tripped -- all calls fail-fast
    HALF_OPEN = "half_open"  # testing -- one call allowed through


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3,
                 recovery_timeout: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = State.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == State.OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = State.HALF_OPEN
            return self._state.value

    def call(self, fn, fallback=None):
        """Execute fn through the circuit breaker."""
        current = self.state

        if current == State.OPEN.value:
            log.warning("[circuit:%s] OPEN -- call blocked", self.name)
            if fallback:
                return fallback()
            raise CircuitOpenError(f"Circuit {self.name} is OPEN")

        try:
            result = fn()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if fallback:
                return fallback()
            raise

    def _on_success(self):
        with self._lock:
            if self._state == State.HALF_OPEN:
                log.info("[circuit:%s] HALF_OPEN -> CLOSED (recovered)", self.name)
            self._state = State.CLOSED
            self._failures = 0

    def _on_failure(self):
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self.failure_threshold:
                if self._state != State.OPEN:
                    log.warning("[circuit:%s] TRIPPED -> OPEN after %d failures",
                                self.name, self._failures)
                self._state = State.OPEN

    def reset(self):
        with self._lock:
            self._state = State.CLOSED
            self._failures = 0
            self._last_failure_time = 0.0

    def status(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failures": self._failures,
                "threshold": self.failure_threshold,
                "recovery_s": self.recovery_timeout,
            }


class CircuitOpenError(Exception):
    pass


# -- Global registry of circuit breakers --
_circuits: dict = {}
_registry_lock = threading.Lock()


def get_circuit(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    with _registry_lock:
        if name not in _circuits:
            _circuits[name] = CircuitBreaker(name, **kwargs)
        return _circuits[name]


def all_statuses() -> list:
    """Return status of all registered circuit breakers."""
    with _registry_lock:
        return [cb.status() for cb in _circuits.values()]

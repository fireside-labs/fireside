"""
circuit.py — Per-node circuit breaker for the Valhalla mesh.

States:
  CLOSED     Normal operation. Requests flow through.
  OPEN       Node is tripped. Requests fail immediately without network call.
  HALF_OPEN  Recovery probe. One request allowed through; success → CLOSED, fail → OPEN.

Thresholds (all tunable via env vars):
  BIFROST_CB_THRESHOLD   int   Consecutive failures to trip (default 3)
  BIFROST_CB_TIMEOUT     int   Seconds before trying recovery (default 60)

Thread-safe — uses a per-node lock.
"""

import logging
import os
import threading
import time
from enum import Enum
from typing import Optional

log = logging.getLogger("bifrost.circuit")

FAILURE_THRESHOLD = int(os.environ.get("BIFROST_CB_THRESHOLD", "3"))
RECOVERY_TIMEOUT  = int(os.environ.get("BIFROST_CB_TIMEOUT",   "60"))


class State(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class NodeCircuit:
    """Circuit breaker for a single node."""

    def __init__(self, node: str):
        self.node         = node
        self.state        = State.CLOSED
        self.failures     = 0
        self.last_failure: Optional[float] = None
        self.last_success: Optional[float] = None
        self._lock        = threading.Lock()

    def allow_request(self) -> bool:
        """Return True if a request should be attempted."""
        with self._lock:
            if self.state == State.CLOSED:
                return True
            if self.state == State.OPEN:
                # Check if recovery timeout has elapsed
                if self.last_failure and (time.time() - self.last_failure) >= RECOVERY_TIMEOUT:
                    log.info("[circuit] %s → HALF_OPEN (attempting recovery probe)", self.node)
                    self.state = State.HALF_OPEN
                    return True
                return False
            # HALF_OPEN — allow the probe through
            return True

    def record_success(self):
        """Call after a successful request."""
        with self._lock:
            prev = self.state
            self.failures     = 0
            self.last_success = time.time()
            self.state        = State.CLOSED
            if prev != State.CLOSED:
                log.info("[circuit] %s → CLOSED (recovered after %s)", self.node, prev.value)

    def record_failure(self):
        """Call after a failed request."""
        with self._lock:
            self.failures     += 1
            self.last_failure  = time.time()
            if self.state == State.HALF_OPEN:
                # Probe failed — back to OPEN
                log.warning("[circuit] %s probe failed → OPEN (will retry in %ds)", self.node, RECOVERY_TIMEOUT)
                self.state = State.OPEN
            elif self.failures >= FAILURE_THRESHOLD:
                if self.state != State.OPEN:
                    log.warning("[circuit] %s TRIPPED → OPEN (%d consecutive failures)", self.node, self.failures)
                self.state = State.OPEN

    def status(self) -> dict:
        """Return a serialisable status dict."""
        with self._lock:
            return {
                "node":         self.node,
                "state":        self.state.value,
                "failures":     self.failures,
                "threshold":    FAILURE_THRESHOLD,
                "last_failure": self.last_failure,
                "last_success": self.last_success,
                "recovery_in":  max(0, RECOVERY_TIMEOUT - (time.time() - self.last_failure))
                                if self.state == State.OPEN and self.last_failure
                                else None,
            }


class CircuitBreakerRegistry:
    """Manages NodeCircuit instances for all nodes in the mesh."""

    def __init__(self, nodes: dict):
        """nodes: { "thor": {"ip": ..., "port": ...}, ... }"""
        self._circuits = {name: NodeCircuit(name) for name in nodes}
        self._lock = threading.Lock()

    def get(self, node: str) -> NodeCircuit:
        """Get-or-create circuit for a node."""
        with self._lock:
            if node not in self._circuits:
                self._circuits[node] = NodeCircuit(node)
            return self._circuits[node]

    def allow(self, node: str) -> bool:
        return self.get(node).allow_request()

    def success(self, node: str):
        self.get(node).record_success()

    def failure(self, node: str):
        self.get(node).record_failure()

    def status_all(self) -> dict:
        """Return status for every node."""
        with self._lock:
            return {name: c.status() for name, c in self._circuits.items()}

    def tripped_nodes(self) -> list:
        """Return list of node names currently OPEN."""
        with self._lock:
            return [name for name, c in self._circuits.items() if c.state == State.OPEN]

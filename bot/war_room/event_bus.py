"""
event_bus.py ΓÇö Freya's Internal Event Bus (Pillar 8: IIT / Phi)

Purpose:
    Lightweight in-process pub/sub hub. Gives every Bifrost subsystem a shared
    communication channel so that significant events in one module can trigger
    reactions in another ΓÇö without hard-wiring imports between them.

    The more cross-module connections, the higher the system's integrated
    information (╬ª). This is the connective tissue.

Usage:
    from war_room import event_bus as bus

    # Subscribe (typically called once in register_routes())
    bus.subscribe("hypothesis.confirmed", my_handler)

    # Publish (from anywhere ΓÇö hypotheses.py, circuit.py, etc.)
    bus.publish("hypothesis.confirmed", {"id": "hyp_abc", "confidence": 0.85})

Handler contract:
    - Handlers receive a single dict payload.
    - They run in daemon threads (fire-and-forget). A slow handler NEVER blocks
      the caller (critical for /ask latency).
    - Exceptions in handlers are logged but never re-raised.

Standard topics:
    hypothesis.created      {id, text, confidence, origin_node}
    hypothesis.confirmed    {id, text, confidence, delta}
    hypothesis.refuted      {id, text, confidence}
    hypothesis.nightmare    {id, text, reason}
    hypothesis.shared       {id, target_count}
    hypothesis.received     {id, sender, confidence}
    circuit.tripped         {node, failures}
    circuit.recovered       {node}
    pheromone.dropped       {resource, type, intensity}
    memory.written          {id, importance, tags}
    prediction.scored       {query_hash, error}
    sleep.completed         {dreamed, decayed, pruned}
    self_model.updated      {path, ts}

Endpoint:
    GET /event-log?limit=50&topic=<filter>   (wired in bifrost_local.py)
"""

import logging
import threading
import time
from collections import deque
from typing import Callable

log = logging.getLogger("bifrost.event_bus")

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_lock        = threading.Lock()
_subscribers: dict[str, list[Callable]] = {}   # topic ΓåÆ [handler, ...]
_event_log: deque = deque(maxlen=500)           # rolling history for self-model


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def subscribe(topic: str, handler: Callable) -> None:
    """
    Register a handler for a topic.

    topic   : Exact topic string (e.g. "hypothesis.confirmed") or wildcard
              prefix ending with ".*" (e.g. "hypothesis.*").
    handler : Callable that accepts a single dict payload.
    """
    with _lock:
        _subscribers.setdefault(topic, []).append(handler)
    log.debug("[bus] subscribed %s ΓåÆ %s", topic, handler.__name__ if hasattr(handler, "__name__") else repr(handler))


def publish(topic: str, payload: dict) -> None:
    """
    Publish an event. All matching handlers are dispatched in daemon threads.
    Returns immediately ΓÇö never blocks the caller.
    """
    event = {
        "topic":   topic,
        "payload": payload,
        "ts":      int(time.time()),
    }

    # Log event regardless of subscriber count
    with _lock:
        _event_log.append(event)
        handlers = _collect_handlers(topic)

    if not handlers:
        log.debug("[bus] publish %s ΓÇö no subscribers", topic)
        return

    log.debug("[bus] publish %s ΓåÆ %d handler(s)", topic, len(handlers))

    for handler in handlers:
        t = threading.Thread(
            target=_safe_call,
            args=(handler, topic, payload),
            daemon=True,
        )
        t.start()


def get_log(limit: int = 50, topic_filter: str = "") -> list:
    """
    Return recent events, optionally filtered by topic prefix.
    Used by GET /event-log.
    """
    with _lock:
        snapshot = list(_event_log)

    if topic_filter:
        # Strip trailing ".*" for prefix matching
        prefix = topic_filter.rstrip(".*").rstrip(".")
        snapshot = [e for e in snapshot if e["topic"].startswith(prefix)]

    return snapshot[-limit:]


def subscriber_count() -> dict:
    """Return a dict of topic ΓåÆ subscriber count (for /event-log status)."""
    with _lock:
        return {t: len(hs) for t, hs in _subscribers.items()}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_handlers(topic: str) -> list:
    """
    Collect all handlers that match this topic.
    Matches:
      - exact topic string ("hypothesis.confirmed")
      - wildcard subscriptions covering this topic ("hypothesis.*")
    Must be called with _lock held.
    """
    matched = []
    for sub_topic, handlers in _subscribers.items():
        if sub_topic == topic:
            matched.extend(handlers)
        elif sub_topic.endswith(".*"):
            prefix = sub_topic[:-2]  # strip ".*"
            if topic.startswith(prefix):
                matched.extend(handlers)
    return matched


def _safe_call(handler: Callable, topic: str, payload: dict) -> None:
    """Run a handler, catching and logging any exception."""
    try:
        handler(payload)
    except Exception as exc:
        log.error("[bus] handler %s raised on topic %s: %s",
                  getattr(handler, "__name__", repr(handler)), topic, exc)
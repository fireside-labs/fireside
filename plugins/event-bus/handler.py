"""
event-bus plugin — In-process pub/sub hub with WebSocket streaming.

Ported from V1 bot/war_room/event_bus.py (162 lines).
All other plugins emit and subscribe to events through this backbone.
Adds WebSocket endpoint for real-time dashboard updates.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import deque
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

log = logging.getLogger("valhalla.event_bus")

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_subscribers: dict[str, list[Callable]] = {}   # topic → [handler, ...]
_event_log: deque = deque(maxlen=1000)          # rolling history

# WebSocket clients
_ws_clients: list[WebSocket] = []
_ws_lock = threading.Lock()

# asyncio loop reference (set during register_routes)
_loop: asyncio.AbstractEventLoop | None = None


# ---------------------------------------------------------------------------
# Core API (used by other plugins: from plugins.event_bus_api import ...)
# ---------------------------------------------------------------------------

def subscribe(topic: str, handler: Callable) -> None:
    """Register a handler for a topic.

    topic   : Exact string ("hypothesis.confirmed") or wildcard ("hypothesis.*").
    handler : Callable accepting a single dict payload.
    """
    with _lock:
        _subscribers.setdefault(topic, []).append(handler)
    log.debug("[bus] subscribed %s → %s", topic,
              handler.__name__ if hasattr(handler, "__name__") else repr(handler))


def publish(topic: str, payload: dict) -> None:
    """Publish an event. Handlers run in daemon threads (never blocks caller).

    Also pushes to all WebSocket clients for real-time dashboard updates.
    """
    event = {
        "topic": topic,
        "payload": payload,
        "ts": int(time.time()),
    }

    with _lock:
        _event_log.append(event)
        handlers = _collect_handlers(topic)

    if handlers:
        log.debug("[bus] publish %s → %d handler(s)", topic, len(handlers))
        for handler in handlers:
            t = threading.Thread(
                target=_safe_call,
                args=(handler, topic, payload),
                daemon=True,
            )
            t.start()

    # Push to WebSocket clients
    _broadcast_ws(event)


def get_log(limit: int = 50, topic_filter: str = "") -> list:
    """Return recent events, optionally filtered by topic prefix."""
    with _lock:
        snapshot = list(_event_log)

    if topic_filter:
        prefix = topic_filter.rstrip(".*").rstrip(".")
        snapshot = [e for e in snapshot if e["topic"].startswith(prefix)]

    return snapshot[-limit:]


def subscriber_count() -> dict:
    """Return dict of topic → subscriber count."""
    with _lock:
        return {t: len(hs) for t, hs in _subscribers.items()}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_handlers(topic: str) -> list:
    """Collect handlers matching this topic (exact + wildcard). Must hold _lock."""
    matched = []
    for sub_topic, handlers in _subscribers.items():
        if sub_topic == topic:
            matched.extend(handlers)
        elif sub_topic.endswith(".*"):
            prefix = sub_topic[:-2]
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


def _broadcast_ws(event: dict) -> None:
    """Push event to all connected WebSocket clients."""
    global _loop
    if not _ws_clients or _loop is None:
        return

    msg = json.dumps(event, default=str)

    async def _send_all():
        dead = []
        with _ws_lock:
            clients = list(_ws_clients)
        for ws in clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        if dead:
            with _ws_lock:
                for ws in dead:
                    if ws in _ws_clients:
                        _ws_clients.remove(ws)

    try:
        asyncio.run_coroutine_threadsafe(_send_all(), _loop)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    """Called by plugin_loader. Registers event endpoints."""
    global _loop

    try:
        _loop = asyncio.get_event_loop()
    except RuntimeError:
        _loop = asyncio.new_event_loop()

    router = APIRouter(tags=["events"])

    @router.get("/api/v1/events")
    async def get_events(
        limit: int = Query(50, ge=1, le=500),
        topic: str = Query("", description="Filter by topic prefix"),
    ):
        """Recent event log with optional topic filter."""
        events = get_log(limit=limit, topic_filter=topic)
        return {
            "events": events,
            "count": len(events),
            "subscribers": subscriber_count(),
        }

    @router.websocket("/api/v1/events/stream")
    async def events_stream(ws: WebSocket):
        """WebSocket real-time event stream for dashboard."""
        await ws.accept()
        with _ws_lock:
            _ws_clients.append(ws)

        log.info("[bus] WebSocket client connected (%d total)", len(_ws_clients))

        try:
            # Send recent events on connect (last 20)
            recent = get_log(limit=20)
            for event in recent:
                await ws.send_text(json.dumps(event, default=str))

            # Keep alive — wait for disconnect
            while True:
                try:
                    data = await asyncio.wait_for(ws.receive_text(), timeout=30)
                    # Client can send topic filter
                    if data.startswith("filter:"):
                        pass  # Sprint 2+: per-client topic filtering
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    try:
                        await ws.send_text(json.dumps({"topic": "ping", "ts": int(time.time())}))
                    except Exception:
                        break
        except WebSocketDisconnect:
            pass
        finally:
            with _ws_lock:
                if ws in _ws_clients:
                    _ws_clients.remove(ws)
            log.info("[bus] WebSocket client disconnected (%d remaining)", len(_ws_clients))

    app.include_router(router)

    # Update asyncio loop reference after app startup
    @app.on_event("startup")
    async def _set_loop():
        global _loop
        _loop = asyncio.get_event_loop()

    log.info("[event-bus] Plugin loaded — pub/sub + WebSocket ready")

"""
mycelium.py — Self-healing network layer.

Like mycelium in a forest, this background process senses when nodes are
struggling and silently ships relevant solutions from the shared memory
to the stressed agent — without any human intervention.

Cycle (every POLL_INTERVAL seconds):
  1. Query Heimdall GET /audit?severity=high&since=<now-5min>
  2. Count high-severity events per node
  3. Any node with >= STRESS_THRESHOLD events = "stressed"
  4. For each stressed node, extract error topics
  5. Query /memory-query?q=<topic>&node=all for relevant successful memories
  6. Re-inject top memories tagged for the stressed node

Started as a daemon thread by bifrost_local.py register_routes().
"""

import json
import logging
import math
import os
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.mycelium")

POLL_INTERVAL   = 300       # 5 minutes
STRESS_WINDOW   = 300       # look-back window (seconds) for stress detection
STRESS_THRESHOLD = 3        # events in window = stressed
HEALING_LIMIT   = 3         # max memories to inject per stressed node per cycle
HEALING_IMPORTANCE = 0.9    # importance score for injected memories

# Heimdall's audit endpoint
_HEIMDALL_AUDIT_URL: Optional[str] = None
# Local bifrost address
_LOCAL_URL = "http://localhost:8765"

# Track which nodes got healing this cycle (avoid spam)
_healed_this_cycle: set = set()

_thread: Optional[threading.Thread] = None
_running = False


def start(nodes: dict) -> None:
    """Start the mycelium background thread. Called from register_routes()."""
    global _HEIMDALL_AUDIT_URL, _thread, _running

    heimdall = nodes.get("heimdall", {})
    ip   = heimdall.get("ip", "100.108.153.23")
    port = heimdall.get("port", 8765)
    _HEIMDALL_AUDIT_URL = f"http://{ip}:{port}/audit"

    if _thread and _thread.is_alive():
        log.info("[mycelium] Already running")
        return

    _running = True
    _thread = threading.Thread(target=_loop, daemon=True, name="mycelium")
    _thread.start()
    log.info("[mycelium] Started — polling Heimdall every %ds (stress threshold: %d events/%ds)",
             POLL_INTERVAL, STRESS_THRESHOLD, STRESS_WINDOW)


def stop() -> None:
    global _running
    _running = False


def _loop() -> None:
    """Main mycelium cycle — runs forever in background."""
    # Stagger first run by 30s to let Bifrost fully initialise
    time.sleep(30)
    while _running:
        try:
            _cycle()
        except Exception as e:
            log.error("[mycelium] Cycle error: %s", e)
        # Sleep in small chunks so stop() is responsive
        for _ in range(POLL_INTERVAL):
            if not _running:
                break
            time.sleep(1)


def _cycle() -> None:
    """One mycelium scan cycle."""
    global _healed_this_cycle
    _healed_this_cycle = set()

    # 1. Poll Heimdall for recent high-severity audit events
    events = _fetch_audit_events()
    if events is None:
        log.debug("[mycelium] Heimdall unreachable — skipping cycle")
        return

    if not events:
        log.debug("[mycelium] No high-severity events — mesh healthy")
        return

    # 2. Count events per node in the stress window
    now  = time.time()
    cutoff = now - STRESS_WINDOW
    node_events: dict = {}
    for ev in events:
        ts = ev.get("ts") or ev.get("timestamp", 0)
        if isinstance(ts, str):
            # ISO string — parse roughly
            try:
                import datetime
                ts = datetime.datetime.fromisoformat(ts).timestamp()
            except Exception:
                ts = 0
        if ts < cutoff:
            continue
        node = ev.get("node", "unknown")
        node_events.setdefault(node, []).append(ev)

    # 3. Identify stressed nodes
    stressed = {n: evs for n, evs in node_events.items()
                if len(evs) >= STRESS_THRESHOLD}

    if not stressed:
        log.debug("[mycelium] No stressed nodes (max events in window: %d)",
                  max((len(v) for v in node_events.values()), default=0))
        return

    log.info("[mycelium] Stressed nodes: %s", list(stressed.keys()))

    # 4 + 5 + 6. Heal each stressed node
    for node, evs in stressed.items():
        if node in _healed_this_cycle:
            continue
        _heal(node, evs)
        _healed_this_cycle.add(node)


def _fetch_audit_events() -> Optional[list]:
    """GET Heimdall's /audit endpoint. Returns list of events or None on failure."""
    if not _HEIMDALL_AUDIT_URL:
        return None
    try:
        params = urllib.parse.urlencode({"severity": "high", "limit": 50})
        url    = f"{_HEIMDALL_AUDIT_URL}?{params}"
        req    = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            # Heimdall returns {"events": [...]} or just a list
            if isinstance(data, list):
                return data
            return data.get("events") or data.get("logs") or []
    except Exception as e:
        log.debug("[mycelium] Heimdall audit fetch failed: %s", e)
        return None


def _extract_topics(events: list) -> list:
    """Extract error keywords from audit events to use as query topics."""
    topics = []
    for ev in events:
        # Gather text from common audit event fields
        text = " ".join(filter(None, [
            ev.get("detail", ""),
            ev.get("message", ""),
            ev.get("error", ""),
            ev.get("event", ""),
        ]))
        if text.strip():
            topics.append(text[:200])
    return topics[:5]  # cap to top 5 topics


def _heal(node: str, events: list) -> None:
    """
    Fetch relevant successful memories and inject them for the stressed node.
    """
    topics = _extract_topics(events)
    if not topics:
        topics = [f"{node} error recovery"]

    injected = 0
    seen_ids: set = set()

    for topic in topics:
        if injected >= HEALING_LIMIT:
            break

        # Query shared memory for relevant successful solutions
        memories = _query_memory(topic)
        if not memories:
            continue

        for mem in memories:
            if injected >= HEALING_LIMIT:
                break
            mid = mem.get("memory_id", "")
            if mid in seen_ids:
                continue
            content = mem.get("content", "").strip()
            if not content or "[MYCELIUM]" in content:
                # Don't re-inject mycelium memories — avoid echo loops
                continue
            seen_ids.add(mid)

            healing_memory = {
                "memories": [{
                    "content":    f"[MYCELIUM] For {node}: {content}",
                    "node":       node,
                    "importance": HEALING_IMPORTANCE,
                    "tags":       ["mycelium", "healing", node],
                    "shared":     True,
                }]
            }
            ok = _post_memory(healing_memory)
            if ok:
                injected += 1
                log.info("[mycelium] Injected healing memory for %s: %s...",
                         node, content[:60])

    if injected == 0:
        log.info("[mycelium] No relevant memories found for stressed node %s (topics: %s)",
                 node, topics)
    else:
        log.info("[mycelium] Healed %s with %d memories (%d events triggered)",
                 node, injected, len(events))


def _query_memory(topic: str) -> list:
    """Query local /memory-query for successful memories related to topic."""
    try:
        params = urllib.parse.urlencode({"q": topic, "node": "all", "limit": 5,
                                         "min_importance": "0.6"})
        url = f"{_LOCAL_URL}/memory-query?{params}"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
            return data.get("results", [])
    except Exception as e:
        log.debug("[mycelium] Memory query failed for '%s': %s", topic[:40], e)
        return []


def _post_memory(payload: dict) -> bool:
    """POST a healing memory to local /memory-sync."""
    try:
        body = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{_LOCAL_URL}/memory-sync", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read())
            return resp.get("upserted", 0) > 0
    except Exception as e:
        log.debug("[mycelium] Memory inject failed: %s", e)
        return False


def status() -> dict:
    """Return current mycelium health."""
    return {
        "running":          _running and bool(_thread and _thread.is_alive()),
        "poll_interval_s":  POLL_INTERVAL,
        "stress_threshold": STRESS_THRESHOLD,
        "stress_window_s":  STRESS_WINDOW,
        "healing_limit":    HEALING_LIMIT,
        "heimdall_url":     _HEIMDALL_AUDIT_URL,
        "healed_this_cycle": list(_healed_this_cycle),
    }

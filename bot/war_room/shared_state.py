"""
shared_state.py — Freya's receiver for Heimdall's distributed shared state broadcasts.

Heimdall broadcasts state changes via POST /shared-state-sync.
Freya stores them locally with last-writer-wins (LWW) by ts.
Expired entries (TTL > 0) are lazily pruned on read.

Payload format (from Heimdall):
{
  "key":   "model_error",
  "entry": {
    "value":  <any>,
    "ts":     1741285200.0,
    "ttl":    300.0,          # 0 = permanent
    "origin": "heimdall"
  },
  "from": "heimdall"
}

GET /shared-state          → all live entries
GET /shared-state?key=<k>  → single entry
POST /shared-state-sync    → receive broadcast (Heimdall calls this)

Auto-injects into attention.py so Freya's focus window picks up mesh-wide topics.
"""

import threading
import time
import logging

log = logging.getLogger("war-room.shared_state")

# { key: {"value": any, "ts": float, "ttl": float, "origin": str} }
_store: dict = {}
_lock = threading.Lock()


def receive(key: str, entry: dict, from_node: str = "unknown") -> dict:
    """
    Accept an incoming shared-state broadcast.
    LWW: only update if incoming ts > stored ts.
    Returns {"accepted": bool, "reason": str}.
    """
    if not key:
        return {"accepted": False, "reason": "missing key"}

    ts      = float(entry.get("ts", time.time()))
    ttl     = float(entry.get("ttl", 0))
    value   = entry.get("value")
    origin  = entry.get("origin", from_node)

    with _lock:
        existing = _store.get(key)
        if existing and existing["ts"] >= ts:
            return {"accepted": False, "reason": "stale — existing ts is newer"}
        _store[key] = {"value": value, "ts": ts, "ttl": ttl, "origin": origin}

    log.debug("[shared_state] accepted %s from %s (ts=%.0f ttl=%.0f)",
              key, origin, ts, ttl)

    # Inject into attention window so Freya's focus picks up the topic
    try:
        from war_room import attention as _att
        _att.record_query(key)
    except Exception:
        pass

    return {"accepted": True, "key": key, "origin": origin}


def get(key: str = "") -> dict:
    """Return live entries. Prunes expired TTL entries lazily."""
    now = time.time()
    with _lock:
        if key:
            entry = _store.get(key)
            if entry is None:
                return {"key": key, "found": False}
            if entry["ttl"] > 0 and (now - entry["ts"]) > entry["ttl"]:
                del _store[key]
                return {"key": key, "found": False, "reason": "expired"}
            return {"key": key, "found": True, **entry}
        else:
            live = {}
            expired = []
            for k, e in list(_store.items()):
                if e["ttl"] > 0 and (now - e["ts"]) > e["ttl"]:
                    expired.append(k)
                else:
                    age = round(now - e["ts"], 1)
                    remaining = round(e["ttl"] - age, 1) if e["ttl"] > 0 else None
                    live[k] = {**e, "age_s": age, "ttl_remaining_s": remaining}
            for k in expired:
                del _store[k]
            return {
                "total": len(live),
                "entries": live,
                "pruned_expired": len(expired),
            }

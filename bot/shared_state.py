"""
shared_state.py -- Distributed key-value shared state for the Bifrost mesh.

Nodes POST to /shared-state to set a value locally and broadcast to peers.
Peers receive via POST /shared-state-sync (signed).

Data is held in memory with optional TTL.
Auto-feeds into watchdog / working context if key matches known patterns.

API (via bifrost_local.py):
    POST /shared-state      {"key": "...", "value": ..., "ttl": 300}
    POST /shared-state-sync {"key": "...", "value": ..., "ttl": ..., "from": "node"}
    GET  /shared-state      ?key=foo   (or all keys if no param)
"""

import json
import logging
import threading
import time
import urllib.request
from typing import Any

log = logging.getLogger("shared_state")

_lock   = threading.Lock()
# {key: {"value": Any, "ts": float, "ttl": int|None, "from": str}}
_store: dict[str, dict] = {}


def set_local(key: str, value: Any, ttl: int = None, source: str = "self"):
    """Write a key to local store."""
    with _lock:
        _store[key] = {
            "value": value,
            "ts":    time.time(),
            "ttl":   ttl,
            "from":  source,
        }
    log.debug("[shared_state] set %s = %r (ttl=%s from=%s)", key, value, ttl, source)


def get(key: str = None) -> dict:
    """Read one or all keys. Expired TTL entries are removed."""
    now = time.time()
    with _lock:
        # Prune expired
        expired = [k for k, v in _store.items()
                   if v.get("ttl") and now - v["ts"] > v["ttl"]]
        for k in expired:
            del _store[k]

        if key:
            return _store.get(key, {})
        return dict(_store)


def broadcast(key: str, value: Any, ttl: int = None,
              peer_urls: list[str] = None, config: dict = None):
    """Broadcast a state change to peer nodes via POST /shared-state-sync."""
    if not peer_urls:
        return

    payload = json.dumps({
        "key":   key,
        "value": value,
        "ttl":   ttl,
        "from":  (config or {}).get("node_name", "thor"),
        "ts":    time.time(),
    }).encode()

    # Sign if signing available
    headers = {"Content-Type": "application/json"}
    try:
        from signing import sign_body  # type: ignore
        headers.update(sign_body(payload, config or {}))
    except Exception:
        pass

    def _send(url):
        try:
            req = urllib.request.Request(
                f"{url}/shared-state-sync",
                data=payload, headers=headers, method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
            log.debug("[shared_state] broadcast %s -> %s OK", key, url)
        except Exception as e:
            log.warning("[shared_state] broadcast %s -> %s failed: %s", key, url, e)

    import threading as _t
    for url in peer_urls:
        _t.Thread(target=_send, args=(url,), daemon=True).start()


def all_keys() -> list[str]:
    with _lock:
        return list(_store.keys())

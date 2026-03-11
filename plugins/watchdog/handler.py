"""
watchdog plugin — Health monitoring for Valhalla Mesh V2.

Ported from V1 bot/watchdog.py (242 lines).
Background thread polls /health on each peer node.
After 2 consecutive failures → marks node offline.
Upon recovery → marks node online.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.plugin.watchdog")

router = APIRouter(tags=["watchdog"])

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
_enabled = True
_running = False
_thread: threading.Thread | None = None
_stop_event = threading.Event()

# node_name → { url, status, consecutive_failures, last_check, last_seen }
_nodes: dict[str, dict] = {}

_POLL_INTERVAL = 60  # seconds
_FAILURE_THRESHOLD = 2


# ---------------------------------------------------------------------------
# Polling logic
# ---------------------------------------------------------------------------

def _check_health(url: str, timeout: int = 5) -> bool:
    """Hit GET /health on a peer node. Returns True if 200."""
    try:
        req = urllib.request.Request(f"{url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _poll_once(node_name: str, node_info: dict) -> None:
    """Poll a single node and update state."""
    url = node_info["url"]
    now = datetime.now(timezone.utc).isoformat()
    healthy = _check_health(url)

    if healthy:
        if node_info.get("status") == "offline":
            log.info("⚡ Node '%s' recovered", node_name)
        node_info["status"] = "online"
        node_info["consecutive_failures"] = 0
        node_info["last_seen"] = now
    else:
        node_info["consecutive_failures"] = node_info.get("consecutive_failures", 0) + 1
        if node_info["consecutive_failures"] >= _FAILURE_THRESHOLD:
            if node_info.get("status") != "offline":
                log.warning("🔥 Node '%s' OFFLINE (%d consecutive failures)",
                            node_name, node_info["consecutive_failures"])
            node_info["status"] = "offline"

    node_info["last_check"] = now


def _poll_loop() -> None:
    """Background loop: poll all nodes every POLL_INTERVAL seconds."""
    global _running
    _running = True
    log.info("[watchdog] Poll loop started (%ds interval)", _POLL_INTERVAL)

    while not _stop_event.is_set():
        if _enabled:
            for name, info in _nodes.items():
                if _stop_event.is_set():
                    break
                _poll_once(name, info)

        _stop_event.wait(_POLL_INTERVAL)

    _running = False
    log.info("[watchdog] Poll loop stopped")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def start(config: dict) -> None:
    """Initialize node list from config and start the poll thread."""
    global _thread
    _nodes.clear()

    this_node = config.get("node", {}).get("name", "")
    mesh_nodes = config.get("mesh", {}).get("nodes", {})

    for name, ncfg in mesh_nodes.items():
        if name == this_node:
            continue  # don't poll ourselves
        ip = ncfg.get("ip", "")
        port = ncfg.get("port", 8765)
        if ip:
            _nodes[name] = {
                "url": f"http://{ip}:{port}",
                "role": ncfg.get("role", ""),
                "status": "unknown",
                "consecutive_failures": 0,
                "last_check": None,
                "last_seen": None,
            }

    if _nodes and not _running:
        _stop_event.clear()
        _thread = threading.Thread(target=_poll_loop, daemon=True, name="watchdog")
        _thread.start()
        log.info("[watchdog] Monitoring %d nodes: %s",
                 len(_nodes), list(_nodes.keys()))


def stop() -> None:
    """Stop the watchdog poll loop."""
    _stop_event.set()


def get_status() -> dict:
    """Return current watchdog state."""
    return {
        "enabled": _enabled,
        "running": _running,
        "poll_interval_seconds": _POLL_INTERVAL,
        "failure_threshold": _FAILURE_THRESHOLD,
        "nodes": {
            name: {
                "url": info["url"],
                "role": info["role"],
                "status": info["status"],
                "consecutive_failures": info["consecutive_failures"],
                "last_check": info["last_check"],
                "last_seen": info["last_seen"],
            }
            for name, info in _nodes.items()
        },
    }


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

class ToggleRequest(BaseModel):
    enabled: bool


def register_routes(app, config: dict) -> None:
    """Called by plugin_loader at startup."""

    @router.get("/watchdog-status")
    async def watchdog_status():
        return get_status()

    @router.post("/watchdog/toggle")
    async def watchdog_toggle(req: ToggleRequest):
        global _enabled
        _enabled = req.enabled
        return {"ok": True, "enabled": _enabled}

    app.include_router(router)

    # Start polling in a delayed thread (let Bifrost finish booting)
    def _delayed_start():
        time.sleep(5)
        start(config)

    threading.Thread(target=_delayed_start, daemon=True, name="watchdog-init").start()
    log.info("[watchdog] Registered (delayed start in 5s)")

"""
watchdog.py -- Auto-Hydra Watchdog for the Bifrost mesh.

Background thread polls /health on each peer node every 60 seconds.
After 2 consecutive failures for a node -> auto-absorb its role.
After node recovers -> release the absorbed role + drop reliable pheromone.

API (called from bifrost_local.py):
    start(config)               -- begin polling (called once at startup)
    stop()                      -- clean shutdown
    status()                    -- dict of node states for GET /watchdog-status
    set_enabled(bool)           -- pause/resume polling without stopping thread
"""

import json
import logging
import threading
import time
import urllib.request
from typing import Callable

log = logging.getLogger("watchdog")

# ---- Tuning ----------------------------------------------------------------
POLL_INTERVAL_S   = 60     # seconds between polls
FAILURE_THRESHOLD = 2      # consecutive misses before absorbing

# ---- State -----------------------------------------------------------------
_lock      = threading.Lock()
_enabled   = True
_thread    = None
_stop_evt  = threading.Event()

# {node: {"last_seen": float, "failures": int, "state": "ok"|"absorbed"|"unknown"}}
_nodes: dict[str, dict] = {}

# Callbacks wired in from bifrost_local
_absorb_fn:  Callable[[str], None] | None = None
_release_fn: Callable[[str], None] | None = None
_log_event:  Callable[[str, dict], None] | None = None

# URLs set at start()
_freya_base:   str = "http://100.102.105.3:8765"
_heimdall_base: str = "http://100.108.153.23:8765"


def _get(url: str, timeout: int = 5) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def _drop_pheromone(freya_base: str, node: str, ptype: str, intensity: float, reason: str):
    """Drop a pheromone on Freya (best-effort, no error propagation)."""
    try:
        payload = json.dumps({
            "node":      "thor",
            "resource":  f"{node}->/health",
            "type":      ptype,
            "intensity": intensity,
            "reason":    reason,
        }).encode()
        req = urllib.request.Request(
            f"{freya_base}/pheromone",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log.debug("[watchdog] pheromone drop failed (non-critical): %s", e)


def _notify_quarantine(node: str, intensity: float):
    """
    Odin spec: when danger pheromone > 0.7 on a node, POST intensity
    to Heimdall /quarantine-config so it extends quarantine delay.
    Non-blocking, best-effort.
    """
    if intensity <= 0.7:
        return
    try:
        payload = json.dumps({
            "node":      node,
            "intensity": intensity,
            "source":    "thor-watchdog",
            "reason":    f"auto-absorb: {node} unreachable",
        }).encode()
        req = urllib.request.Request(
            f"{_heimdall_base}/quarantine-config",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        log.info("[watchdog] quarantine-config notified: %s intensity=%.2f", node, intensity)
    except Exception as e:
        log.debug("[watchdog] quarantine notify failed (non-critical): %s", e)


def _poll_once(node: str, url: str, freya_base: str):
    """Poll one node's /health. Update state and trigger absorb/release as needed."""
    global _absorb_fn, _release_fn, _log_event
    try:
        data = _get(f"{url}/health", timeout=5)
        alive = data.get("status") in ("ok", "degraded")
    except Exception:
        alive = False

    with _lock:
        rec = _nodes.setdefault(node, {"failures": 0, "state": "unknown", "last_seen": 0})

        if alive:
            if rec["state"] == "absorbed":
                log.info("[watchdog] %s is back online — releasing absorbed role", node)
                if _release_fn:
                    try:
                        _release_fn(node)
                    except Exception as e:
                        log.warning("[watchdog] release_fn error: %s", e)
                if _log_event:
                    _log_event("hydra:release", {"node": node, "reason": "recovered"})
                _drop_pheromone(freya_base, node, "reliable", 0.7, f"{node} recovered")
            rec["failures"]  = 0
            rec["last_seen"] = time.time()
            rec["state"]     = "ok"
        else:
            rec["failures"] += 1
            log.warning("[watchdog] %s unreachable (failure #%d)", node, rec["failures"])

            if rec["failures"] == FAILURE_THRESHOLD and rec["state"] != "absorbed":
                log.warning("[watchdog] %s hit threshold — auto-absorbing role", node)
                if _absorb_fn:
                    try:
                        _absorb_fn(node)
                        rec["state"] = "absorbed"
                    except Exception as e:
                        log.error("[watchdog] absorb_fn error for %s: %s", node, e)
                if _log_event:
                    _log_event("hydra:auto_absorb", {
                        "node": node, "consecutive_failures": rec["failures"],
                    })
                _drop_pheromone(freya_base, node, "danger", 0.8,
                                f"{node} unreachable x{rec['failures']}")
                # Odin spec: notify Heimdall to extend quarantine delay
                _notify_quarantine(node, 0.8)


def _poll_loop(node_urls: dict[str, str], freya_base: str):
    """Background polling loop."""
    log.info("[watchdog] Started — monitoring: %s", list(node_urls.keys()))
    while not _stop_evt.is_set():
        if _enabled:
            for node, url in node_urls.items():
                if _stop_evt.is_set():
                    break
                try:
                    _poll_once(node, url, freya_base)
                except Exception as e:
                    log.error("[watchdog] Unexpected error polling %s: %s", node, e)
        _stop_evt.wait(timeout=POLL_INTERVAL_S)
    log.info("[watchdog] Stopped")


def start(config: dict,
          absorb_fn: Callable = None,
          release_fn: Callable = None,
          log_event_fn: Callable = None):
    """Start the watchdog background thread."""
    global _thread, _absorb_fn, _release_fn, _log_event

    _absorb_fn  = absorb_fn
    _release_fn = release_fn
    _log_event  = log_event_fn

    nodes_cfg  = config.get("nodes", {})
    freya_base = "http://100.102.105.3:8765"

    # Build URL map for peers (exclude ourselves)
    this_node  = config.get("node_name", "thor")
    node_urls  = {}
    for name, ncfg in nodes_cfg.items():
        if name == this_node:
            continue
        ip   = ncfg.get("ip", "")
        port = ncfg.get("port", 8765)
        if ip:
            node_urls[name] = f"http://{ip}:{port}"
            if name == "freya":
                freya_base = f"http://{ip}:{port}"
            if name == "heimdall":
                _heimdall_base = f"http://{ip}:{port}"

    if not node_urls:
        log.warning("[watchdog] No peer nodes in config — watchdog idle")
        return

    _stop_evt.clear()
    _thread = threading.Thread(
        target=_poll_loop,
        args=(node_urls, freya_base),
        daemon=True,
        name="hydra-watchdog",
    )
    _thread.start()
    log.info("[watchdog] Watching %d nodes: %s", len(node_urls), list(node_urls.keys()))


def stop():
    _stop_evt.set()


def set_enabled(value: bool):
    global _enabled
    _enabled = value
    log.info("[watchdog] %s", "enabled" if value else "paused")


def status() -> dict:
    with _lock:
        now = time.time()
        nodes_status = {}
        for node, rec in _nodes.items():
            last = rec.get("last_seen", 0)
            nodes_status[node] = {
                "state":          rec.get("state", "unknown"),
                "failures":       rec.get("failures", 0),
                "last_seen_s":    round(now - last) if last else None,
                "last_seen_iso":  _ts_to_iso(last) if last else None,
            }
        return {
            "enabled":       _enabled,
            "poll_interval": POLL_INTERVAL_S,
            "threshold":     FAILURE_THRESHOLD,
            "nodes":         nodes_status,
            "thread_alive":  _thread.is_alive() if _thread else False,
        }


def _ts_to_iso(ts: float) -> str:
    import datetime
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")

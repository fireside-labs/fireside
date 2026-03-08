"""
bifrost.py -- The Bifrost Bridge
v5 -- cross-node callback routing. All nodes send Telegram messages.
Only the polling node handles callbacks, routing execution back to the origin.

Usage: python bifrost.py

HTTP API (port 8765):
    POST /request          { "caller": "odin", "command": "run_exporter", "params": {} }
    POST /propose-command  { "caller": "odin", "name": "cmd_name", "definition": {...} }
    POST /receive-files    { "dst_path": "...", "filename": "...", "data_hex": "..." }
    POST /execute          { "request_id": "abc123" }  -- called by polling node
    GET  /health           -> 200 OK
    GET  /commands         -> current whitelist
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import uuid
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Optional


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each request in a new thread so /ask doesn't freeze the node."""
    daemon_threads = True
    allow_reuse_address = True


from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bifrost")

# Windows cp1252 charmap fix — force UTF-8 on stdout/stderr so log messages
# containing non-ASCII (em-dash, arrows, emoji) don't crash threads.
# IMPORTANT: wrap everything in try/except — when Bifrost starts detached
# (scheduled task with no console / pythonw.exe), sys.stdout and sys.stderr
# are None. hasattr(None, 'buffer') returns False safely but other stream ops
# will raise ValueError: "I/O operation on closed file". Swallow that here.
if sys.platform == "win32":
    import io
    try:
        if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, AttributeError, OSError):
        # Detached/closed streams — redirect logging to a file instead
        import tempfile, os
        _log_path = os.path.join(tempfile.gettempdir(), "bifrost.log")
        logging.basicConfig(filename=_log_path, level=logging.INFO,
                            format="%(asctime)s [%(levelname)s] %(message)s",
                            force=True)

# Valhalla War Room — peer-to-peer agent mesh
try:
    from war_room import WarRoomStore, GossipSync, AskHandler
    from war_room.routes import WarRoomRoutes
    from war_room.sync import OverseerLoop
    WAR_ROOM_AVAILABLE = True
except ImportError as _wr_err:
    WAR_ROOM_AVAILABLE = False
    logging.getLogger("bifrost").warning("War Room module not found: %s", _wr_err)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ---------------------------------------------------------------------------
# Config — two-layer system
#   config.json          shared/generic — Odin can push freely
#   config.<node>.json   permanent identity — never touched by Odin
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent

# Ensure script directory is on sys.path for local imports (war_room, event_log, etc.)
import sys as _sys
_script_dir = str(BASE.resolve())
if _script_dir not in _sys.path:
    _sys.path.insert(0, _script_dir)

def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, override wins on conflicts. Dicts are merged recursively."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result

_base_config = json.loads((BASE / "config.json").read_text())
# Discover node identity: explicit config > hostname > "unknown"
import socket as _socket
_hostname   = _socket.gethostname().lower().split(".")[0]
_candidates = [_base_config.get("this_node"), _hostname]
_node_cfg   = None
for _candidate in _candidates:
    if _candidate:
        _node_cfg = BASE / f"config.{_candidate}.json"
        if _node_cfg.exists():
            break
        _node_cfg = None
CONFIG = _deep_merge(_base_config, json.loads(_node_cfg.read_text())) if _node_cfg and _node_cfg.exists() else _base_config

COMMANDS_FILE = BASE / "commands.json"

def _load_commands() -> dict:
    return json.loads(COMMANDS_FILE.read_text())

def _save_commands(cmds: dict):
    COMMANDS_FILE.write_text(json.dumps(cmds, indent=2))

BOT_TOKEN        = CONFIG["telegram_bot_token"]
CHAT_ID          = CONFIG["telegram_chat_id"]
LISTEN_PORT      = CONFIG.get("listen_port", 8765)
THIS_NODE        = CONFIG.get("this_node", "unknown")
NODES            = CONFIG.get("nodes", {})
MEMORY_MASTER    = CONFIG.get("memory_master", "freya")  # node hosting canonical LanceDB
TELEGRAM_POLLING = CONFIG.get("telegram_polling", True)
AGENT_CONFIG     = CONFIG.get("agent", {"id": THIS_NODE, "role": "general", "local_model": "qwen3.5:9b"})
WAR_ROOM_CONFIG  = CONFIG.get("war_room", {})

# ---------------------------------------------------------------------------
# Workspace sync
# ---------------------------------------------------------------------------
import hashlib, sys

_SYNC_CFG         = CONFIG.get("workspace_sync", {})
SYNC_ENABLED      = _SYNC_CFG.get("enabled", THIS_NODE != "odin")  # auto-on for non-odin
SYNC_INTERVAL     = _SYNC_CFG.get("interval_seconds", 300)          # 5 min default
SYNC_ODIN_IP      = _SYNC_CFG.get("odin_ip", NODES.get("odin", {}).get("ip", "100.105.27.121"))
SYNC_ODIN_PORT    = _SYNC_CFG.get("odin_port", 8765)
SYNC_EXTENSIONS   = set(_SYNC_CFG.get("extensions", [".md", ".txt", ".json"]))
SYNC_EXCLUDE_DIRS = set(_SYNC_CFG.get("exclude_dirs", ["bot", ".git", "__pycache__"]))

# Local workspace root — override in config if different on this node
if sys.platform == "win32":
    import os as _os
    _default_ws = str(Path(_os.environ.get("USERPROFILE", "C:/Users/Jorda")) / ".openclaw" / "workspace")
else:
    _default_ws = str(Path.home() / ".openclaw" / "workspace")
SYNC_LOCAL_WORKSPACE = Path(_SYNC_CFG.get("local_workspace", _default_ws))

def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()[:16]  # short enough for comparison

def _build_manifest(root: Path) -> dict:
    """Return {relative_path: sha256_short} for all tracked files under root."""
    manifest = {}
    if not root.exists():
        return manifest
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        parts = p.parts
        if any(ex in parts for ex in SYNC_EXCLUDE_DIRS):
            continue
        if p.suffix.lower() not in SYNC_EXTENSIONS:
            continue
        rel = p.relative_to(root).as_posix()
        try:
            manifest[rel] = _file_sha256(p)
        except Exception:
            pass
    return manifest

class WorkspaceSyncThread(threading.Thread):
    """Runs on non-Odin nodes. Polls Odin's workspace manifest and pulls changed files."""
    def __init__(self):
        super().__init__(daemon=True, name="workspace-sync")
        self._stop = threading.Event()

    def stop(self): self._stop.set()

    def run(self):
        log.info("WorkspaceSync started — pulling from odin every %ds", SYNC_INTERVAL)
        while not self._stop.wait(SYNC_INTERVAL):
            try:
                self._sync_once()
            except Exception as e:
                log.warning("WorkspaceSync error: %s", e)

    def _sync_once(self):
        base_url = f"http://{SYNC_ODIN_IP}:{SYNC_ODIN_PORT}"
        try:
            # 1. Fetch Odin's manifest
            with urllib.request.urlopen(f"{base_url}/workspace-manifest", timeout=10) as r:
                remote = json.loads(r.read())
        except Exception as e:
            hook_sync_failed(THIS_NODE, str(e))
            raise
        # 2. Build local manifest
        local = _build_manifest(SYNC_LOCAL_WORKSPACE)
        # 3. Pull files that are missing or changed
        updated = []
        for rel, rhash in remote.items():
            if local.get(rel) != rhash:
                self._pull_file(base_url, rel)
                updated.append(rel)
        if updated:
            log.info("WorkspaceSync pulled %d file(s): %s", len(updated), updated[:5])
        hook_sync_complete(THIS_NODE, len(updated))

    def _pull_file(self, base_url: str, rel: str):
        encoded = urllib.parse.quote(rel, safe="")
        with urllib.request.urlopen(f"{base_url}/workspace-file?path={encoded}", timeout=15) as r:
            payload = json.loads(r.read())
        data = base64.b64decode(payload["data_b64"])
        dest = SYNC_LOCAL_WORKSPACE / rel.replace("/", os.sep)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)

_workspace_sync: Optional[WorkspaceSyncThread] = None
if SYNC_ENABLED and THIS_NODE != "odin":
    _workspace_sync = WorkspaceSyncThread()

# ---------------------------------------------------------------------------
# Hook Engine — unified event-driven automation for mesh events
#
# Two sources merged:
#   config.json → "hooks" key  (Odin's original: event→handler list)
#   hooks.json                 (Heimdall's: richer format with templates)
#
# Event name aliases so both naming conventions work:
#   on_error ↔ node:error, on_node_down ↔ node:offline, etc.
# ---------------------------------------------------------------------------

_SEVERITY_EMOJI = {
    "critical": "🚨", "high": "⚠️ ", "medium": "⚡", "low": "ℹ️ ", "info": "📋"
}

# Alias map: Heimdall names → Odin names (bidirectional lookup)
_EVENT_ALIASES = {
    "on_error":          "node:error",
    "on_node_down":      "node:offline",
    "on_model_fallback": "model:fallback",
    "on_task_complete":  "task:complete",
    "on_denial_spike":   "node:error",   # denial spikes are security errors
}
_EVENT_ALIASES_REV = {v: k for k, v in _EVENT_ALIASES.items()}

# Load hooks.json (Heimdall's format) if present, else fall back to config.json
_hooks_json_path = BASE / "hooks.json"
_hooks_registry = {}
if _hooks_json_path.exists():
    try:
        _hj = json.loads(_hooks_json_path.read_text())
        for hname, hdef in _hj.get("hooks", {}).items():
            if not hdef.get("enabled", True):
                continue
            # Map to Odin event name
            odin_name = _EVENT_ALIASES.get(hname, hname)
            actions = []
            for act in hdef.get("actions", []):
                atype = act.get("type", "log_only")
                # Map Heimdall action types → Odin handler names
                if atype == "telegram_notify":
                    actions.append("telegram_alert")
                elif atype == "war_room_post":
                    actions.append("war_room_post")
                elif atype == "http_post":
                    actions.append("event_log")
                else:
                    actions.append(atype)
            _hooks_registry[odin_name] = actions
        log.info("Loaded %d hooks from hooks.json", len(_hooks_registry))
    except Exception as e:
        log.warning("Failed to load hooks.json: %s", e)

# Merge: hooks.json wins, config.json fills gaps, hardcoded defaults as last resort
_HOOK_DEFAULTS = {
    "node:error":     ["telegram_alert", "event_log"],
    "node:offline":   ["telegram_alert", "event_log"],
    "model:fallback": ["telegram_alert", "event_log"],
    "task:complete":  ["event_log"],
    "sync:complete":  ["log_only"],
    "sync:failed":    ["telegram_alert", "event_log"],
}
_cfg_hooks = CONFIG.get("hooks", {})
_HOOK_CFG = {**_HOOK_DEFAULTS, **_cfg_hooks, **_hooks_registry}

# Event log endpoint — Thor hosts the SQLite store
_EVENT_LOG_URL = f"http://{NODES.get('thor', {}).get('ip', '100.117.255.38')}:{NODES.get('thor', {}).get('port', 8765)}/event-log"

# ---------------------------------------------------------------------------
# Shared Memory Layer — proxy reads/writes to the MEMORY_MASTER node
# Any node can call /memory-sync or /memory-query locally;
# if this node is not the master, the request is forwarded transparently.
# Change "memory_master" in config.json to promote a different node.
# ---------------------------------------------------------------------------

def _memory_master_url(path: str) -> str:
    """Return the full URL for a memory endpoint on the master node."""
    master = NODES.get(MEMORY_MASTER, {})
    ip   = master.get("ip", "100.102.105.3")  # fallback to Freya's current IP
    port = master.get("port", 8765)
    return f"http://{ip}:{port}{path}"


def _proxy_memory_write(payload: dict) -> dict:
    """Forward a memory-sync payload to the master node. Returns master's response."""
    if THIS_NODE == MEMORY_MASTER:
        return {"error": "call local handler directly"}  # should not happen
    url  = _memory_master_url("/memory-sync")
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=body,
           headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error("[memory] proxy write failed: %s", e)
        return {"error": str(e)}


def _proxy_memory_query(query_string: str) -> dict:
    """Forward a memory-query to the master node. query_string = raw GET query string."""
    if THIS_NODE == MEMORY_MASTER:
        return {"error": "call local handler directly"}
    sep = "?" if query_string else ""
    url = _memory_master_url(f"/memory-query{sep}{query_string}")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error("[memory] proxy query failed: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Node Status — persistent heartbeat file for session-spanning task awareness
# Agents read this at startup to know what they were last doing.
# Updated automatically on task claim/complete/status-change.
# ---------------------------------------------------------------------------

_STATUS_FILE = BASE / "status.json"

def _read_node_status() -> dict:
    """Read the current node status from status.json."""
    try:
        if _STATUS_FILE.exists():
            return json.loads(_STATUS_FILE.read_text())
    except Exception:
        pass
    return {"node": THIS_NODE, "status": "idle", "last_task": None, "updated": None}

def _write_node_status(status: str, last_task: str = None, detail: str = None):
    """Write the current node status to status.json."""
    import time
    from datetime import datetime, timezone
    current = _read_node_status()
    current.update({
        "node": THIS_NODE,
        "status": status,
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_ts": time.time(),
    })
    if last_task is not None:
        current["last_task"] = last_task
    if detail is not None:
        current["detail"] = detail[:300]
    try:
        _STATUS_FILE.write_text(json.dumps(current, indent=2))
    except Exception as e:
        log.warning("[status] write failed: %s", e)


class HookEngine:
    """Fire registered handlers when mesh events occur."""

    def emit(self, event: str, payload: dict, source_node: str = THIS_NODE):
        """Emit an event. Handlers fire in background threads — non-blocking."""
        handlers = _HOOK_CFG.get(event, ["log_only"])
        for handler_name in handlers:
            threading.Thread(
                target=self._dispatch,
                args=(handler_name, event, payload, source_node),
                daemon=True,
                name=f"hook-{handler_name}"
            ).start()

    def _dispatch(self, handler: str, event: str, payload: dict, source_node: str):
        try:
            if handler == "telegram_alert":
                self._handler_telegram(event, payload, source_node)
            elif handler == "war_room_post":
                self._handler_war_room(event, payload, source_node)
            elif handler == "event_log":
                self._handler_event_log(event, payload, source_node)
            elif handler == "heimdall_audit":
                self._handler_heimdall_audit(event, payload, source_node)
            elif handler == "memory_write":
                self._handler_memory_write(event, payload, source_node)
            elif handler == "crispr_extract":
                self._handler_crispr_extract(event, payload, source_node)
            elif handler == "log_only":
                log.info("[hook] %s from %s: %s", event, source_node, payload)
            else:
                log.warning("[hook] Unknown handler '%s' for event '%s'", handler, event)
        except Exception as e:
            log.error("[hook] Handler '%s' failed for event '%s': %s", handler, event, e)

    def _handler_telegram(self, event: str, payload: dict, source_node: str):
        """Send a Telegram alert for this event."""
        severity = payload.get("severity", "medium")
        emoji = _SEVERITY_EMOJI.get(severity, "⚡")
        node_label = source_node.upper()
        error = payload.get("error") or payload.get("reason") or payload.get("message") or ""
        event_label = event.replace(":", " → ")
        lines = [
            f"{emoji} *Mesh Event: {event_label}*",
            f"Node: `{node_label}`",
        ]
        if error:
            lines.append(f"Detail: `{error[:200]}`")
        for k, v in payload.items():
            if k not in ("error", "reason", "message", "severity", "node"):
                lines.append(f"{k}: `{str(v)[:100]}`")
        msg = "\n".join(lines)

        async def _send():
            if _bot:
                await _bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        if _event_loop and _event_loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), _event_loop)
        else:
            log.warning("[hook:telegram] event loop not ready; dropping alert for %s", event)

    def _handler_war_room(self, event: str, payload: dict, source_node: str):
        """Post event to War Room message board."""
        if _war_room_store is None:
            return
        _war_room_store.add_message(source_node, f"[HOOK:{event}] {payload}")

    def _handler_event_log(self, event: str, payload: dict, source_node: str):
        """POST event to Thor's /event-log endpoint for persistent storage."""
        import time as _time
        body = {
            "event": event,
            "node": source_node,
            "payload": payload,
            "severity": payload.get("severity", "medium"),
            "ts": _time.time(),
        }
        try:
            req = urllib.request.Request(
                _EVENT_LOG_URL,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception as e:
            log.debug("[hook:event_log] Could not reach event-log: %s", e)

    def _handler_heimdall_audit(self, event: str, payload: dict, source_node: str):
        """Forward event to Heimdall's audit_log via his /log-cost endpoint (reused as audit)."""
        import time as _time
        heimdall = NODES.get("heimdall", {})
        ip   = heimdall.get("ip", "100.108.153.23")
        port = heimdall.get("port", 8765)
        body = {
            "node":     source_node,
            "event":    event,
            "severity": payload.get("severity", "info"),
            "detail":   json.dumps(payload)[:500],
        }
        try:
            req = urllib.request.Request(
                f"http://{ip}:{port}/hook",
                data=json.dumps({"event": event, "node": source_node, "payload": payload}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            log.debug("[hook:heimdall_audit] %s", e)

    def _handler_memory_write(self, event: str, payload: dict, source_node: str):
        """Auto-write task completions to shared memory via the memory master."""
        detail = payload.get("detail") or payload.get("message") or payload.get("task") or str(payload)
        text = f"[{source_node}] Completed: {detail[:300]}"
        mem_body = {
            "node":       source_node,
            "text":       text,
            "importance": 0.8,
            "tags":       ["task", "completion", event],
            "shared":     True,
        }
        try:
            url = _memory_master_url("/memory-sync")
            req = urllib.request.Request(
                url, data=json.dumps(mem_body).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=10)
            log.info("[hook:memory_write] Wrote memory for %s: %s", source_node, text[:60])
        except Exception as e:
            log.debug("[hook:memory_write] %s", e)

    def _handler_crispr_extract(self, event: str, payload: dict, source_node: str):
        """CRISPR: extract a reusable pattern from successful task completions
        and inject it as a permanent shared memory for all agents."""
        detail = payload.get("detail") or payload.get("message") or payload.get("task") or ""
        if not detail or len(detail) < 20:
            return  # Too short to extract a meaningful pattern
        # Ask local model to extract a reusable pattern
        prompt = (
            f"Extract a reusable lesson from this completed task. "
            f"Format EXACTLY as: WHEN <situation> DO <approach> BECAUSE <reason>\n\n"
            f"Completed task by {source_node}: {detail[:500]}\n\n"
            f"Return ONLY the single-line WHEN/DO/BECAUSE pattern. No explanation."
        )
        try:
            ask_body = json.dumps({
                "from": "system", "prompt": prompt,
                "system": "You extract reusable patterns. Return only WHEN/DO/BECAUSE format.",
                "model": "local", "max_tokens": 200,
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8765/ask", data=ask_body,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=45) as r:
                result = json.loads(r.read())
                pattern = result.get("response", "").strip()
            if not pattern or len(pattern) < 15:
                return
            # Write as permanent CRISPR memory
            mem_body = json.dumps({"memories": [{
                "node": source_node,
                "content": f"[CRISPR] {pattern}",
                "importance": 0.95,
                "tags": ["crispr", "skill-transfer", "permanent"],
                "permanent": True,
            }]}).encode()
            url = _memory_master_url("/memory-sync")
            req2 = urllib.request.Request(
                url, data=mem_body,
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req2, timeout=10)
            log.info("[hook:crispr] Extracted pattern from %s: %s", source_node, pattern[:80])
        except Exception as e:
            log.debug("[hook:crispr] %s", e)


_hooks = HookEngine()

# ---------------------------------------------------------------------------
# Convenience helpers — call these from anywhere in bifrost.py
# ---------------------------------------------------------------------------

def hook_node_error(node: str, error: str, severity: str = "high"):
    _hooks.emit("node:error", {"node": node, "error": error, "severity": severity})

def hook_node_offline(node: str):
    _hooks.emit("node:offline", {"node": node, "severity": "high"})

def hook_model_fallback(node: str, from_model: str, to_model: str):
    _hooks.emit("model:fallback", {"node": node, "from": from_model, "to": to_model, "severity": "low"})

def hook_task_complete(task_id: str, agent: str, summary: str):
    _hooks.emit("task:complete", {"task_id": task_id, "agent": agent, "summary": summary[:300], "severity": "info"})

def hook_sync_complete(node: str, files_updated: int):
    _hooks.emit("sync:complete", {"node": node, "files_updated": files_updated, "severity": "info"})

def hook_sync_failed(node: str, reason: str):
    _hooks.emit("sync:failed", {"node": node, "reason": reason, "severity": "medium"})


# Initialize War Room (if module is available)
_war_room_store = None
_war_room_routes = None
_gossip_sync = None
_overseer = None

if WAR_ROOM_AVAILABLE:
    _wr_data_dir = BASE / "war_room_data"  # separate from the war_room/ Python package
    _war_room_store = WarRoomStore(_wr_data_dir, max_messages=WAR_ROOM_CONFIG.get("max_messages", 500))
    _ask_handler = AskHandler(AGENT_CONFIG)
    _war_room_routes = WarRoomRoutes(_war_room_store, _ask_handler)
    _gossip_sync = GossipSync(
        _war_room_store, THIS_NODE, NODES,
        interval=WAR_ROOM_CONFIG.get("sync_interval_seconds", 30),
    )
    if THIS_NODE == "odin":
        _overseer = OverseerLoop(
            _war_room_store,
            interval=WAR_ROOM_CONFIG.get("overseer_interval_seconds", 60),
        )
    log.info("War Room initialized for '%s' (role=%s)", AGENT_CONFIG.get('id'), AGENT_CONFIG.get('role'))

try:
    from philosopher_stone import PhilosopherStone
    _philosopher = PhilosopherStone() if THIS_NODE == "odin" else None
except ImportError:
    _philosopher = None


# Pending action requests (persisted to disk)
PENDING_FILE = BASE / "pending.json"

def _load_pending() -> dict:
    try:
        return json.loads(PENDING_FILE.read_text()) if PENDING_FILE.exists() else {}
    except Exception:
        return {}

def _save_pending():
    PENDING_FILE.write_text(json.dumps(pending_requests, indent=2))

pending_requests: dict[str, dict] = _load_pending()

# Pending command proposals (persisted to disk)
PROPOSALS_FILE = BASE / "proposals.json"

def _load_proposals() -> dict:
    try:
        return json.loads(PROPOSALS_FILE.read_text()) if PROPOSALS_FILE.exists() else {}
    except Exception:
        return {}

def _save_proposals():
    PROPOSALS_FILE.write_text(json.dumps(pending_proposals, indent=2))

pending_proposals: dict[str, dict] = _load_proposals()

# Set during startup (both modes)
_event_loop: asyncio.AbstractEventLoop = None
_bot = None


# ---------------------------------------------------------------------------
# Audit log — append-only JSONL, one decision per line
# ---------------------------------------------------------------------------
AUDIT_LOG = BASE / "audit.log"

def _audit(action: str, caller: str, command: str, decision: str, result: str = ""):
    """Append one audit record to audit.log."""
    from datetime import datetime, timezone
    record = {
        "ts":      datetime.now(timezone.utc).isoformat(),
        "node":    THIS_NODE,
        "caller":  caller,
        "command": command,
        "action":  action,
        "decision":decision,
        "result":  result[:500] if result else "",
    }
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        log.warning("audit write failed: %s", e)

# ---------------------------------------------------------------------------
# Command execution (blocking -- runs in thread executor)
# ---------------------------------------------------------------------------

def execute_command(command: str, params: dict) -> str:
    cmds = _load_commands()
    cmd = cmds[command]
    kind = cmd["type"]

    if kind == "ping":
        return f"Bifrost on {THIS_NODE} is alive."

    if kind == "script":
        # Use platform-appropriate Python
        if sys.platform == "win32":
            python = r"C:\Users\Jorda\AppData\Local\Programs\Python\Python312\python.exe"
        else:
            python = sys.executable  # Use current Python on macOS/Linux
        script = cmd["script"]
        model_hint = cmd.get("model_hint")  # D: model pinning — passed through for logging
        if model_hint:
            log.info("Command '%s' has model_hint=%s", command, model_hint)
        result = subprocess.run([python, script], capture_output=True, text=True, timeout=120)
        out = result.stdout.strip() or result.stderr.strip() or "(no output)"
        return f"Exited {result.returncode}:\n{out[:4000]}"

    if kind == "file_copy":
        node_info = NODES.get(cmd["dst_node"])
        if not node_info:
            return f"Unknown node: {cmd['dst_node']}"
        dst_url = f"http://{node_info['ip']}:{node_info.get('port', 8765)}/receive-files"
        src_path = Path(cmd["src"])
        files = list(src_path.glob("*"))
        if not files:
            return f"No files found in {cmd['src']}"
        copied = 0
        errors = []
        for f in files:
            if not f.is_file():
                continue
            try:
                data = f.read_bytes()
                payload = json.dumps({
                    "dst_path": cmd["dst_path"],
                    "filename": f.name,
                    "data_b64": base64.b64encode(data).decode(),  # base64 is 33% overhead vs hex 100%
                }).encode()
                req = urllib.request.Request(
                    dst_url, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status == 200:
                        copied += 1
                    else:
                        errors.append(f"{f.name}: HTTP {resp.status}")
            except Exception as e:
                errors.append(f"{f.name}: {e}")
        summary = f"Copied {copied}/{len(files)} file(s) to {cmd['dst_node']}:{cmd['dst_path']}"
        if errors:
            summary += "\nErrors:\n" + "\n".join(errors)
        return summary

    return f"Unknown type: {kind}"

# ---------------------------------------------------------------------------
# Telegram -- send approval request (runs on ANY node)
# ---------------------------------------------------------------------------

async def send_approval_request(request_id: str, req: dict):
    cmds = _load_commands()
    cmd_def = cmds.get(req["command"], {})
    desc = cmd_def.get("description", req["command"])
    model_hint = cmd_def.get("model_hint", "")
    params_str = json.dumps(req.get("params", {}), indent=2) or "(none)"
    model_line = f"\nModel:   `{model_hint}`" if model_hint else ""
    text = (
        f"*Bifrost - Action Request*\n\n"
        f"Node:    `{THIS_NODE}`\n"
        f"From:    `{req['caller']}`\n"
        f"Action:  `{req['command']}`\n"
        f"Details: {desc}{model_line}\n"
        f"Params:\n```\n{params_str}\n```"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Approve", callback_data=f"approve:{THIS_NODE}:{request_id}"),
        InlineKeyboardButton("Deny",    callback_data=f"deny:{THIS_NODE}:{request_id}"),
    ]])
    await _bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown", reply_markup=keyboard)
    log.info("Sent approval request %s to Telegram", request_id)

async def send_proposal_approval(proposal_id: str, prop: dict):
    defn_str = json.dumps(prop["definition"], indent=2)
    text = (
        f"*Bifrost - Command Proposal*\n\n"
        f"Node:    `{THIS_NODE}`\n"
        f"From:    `{prop['caller']}`\n"
        f"Name:    `{prop['name']}`\n"
        f"Details:\n```\n{defn_str[:800]}\n```"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Approve", callback_data=f"addcmd-approve:{THIS_NODE}:{proposal_id}"),
        InlineKeyboardButton("Deny",    callback_data=f"addcmd-deny:{THIS_NODE}:{proposal_id}"),
    ]])
    await _bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown", reply_markup=keyboard)
    log.info("Sent command proposal %s to Telegram", proposal_id)

# ---------------------------------------------------------------------------
# Helpers: remote calls with fast-fail health check
# ---------------------------------------------------------------------------
REMOTE_TIMEOUT = 5  # seconds — nodes are either up or they're not

def _health_check(node_name: str) -> bool:
    """Ping a node's /health endpoint. Returns True if reachable within REMOTE_TIMEOUT."""
    node_info = NODES.get(node_name)
    if not node_info:
        return False
    url = f"http://{node_info['ip']}:{node_info.get('port', 8765)}/health"
    try:
        with urllib.request.urlopen(url, timeout=REMOTE_TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        return False

def _remote_call(node_name: str, endpoint: str, payload: dict) -> dict:
    """POST to another node's Bifrost. Health-checks first, fails fast if unreachable."""
    node_info = NODES.get(node_name)
    if not node_info:
        return {"error": f"unknown node {node_name}"}
    if not _health_check(node_name):
        return {"error": f"{node_name} is unreachable (health check failed)"}
    url = f"http://{node_info['ip']}:{node_info.get('port', 8765)}{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=REMOTE_TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def _cluster_status() -> dict:
    """Ping all nodes in parallel and return a status grid."""
    results = {}
    def check_node(name, info):
        url = f"http://{info['ip']}:{info.get('port', 8765)}/health"
        try:
            with urllib.request.urlopen(url, timeout=REMOTE_TIMEOUT) as resp:
                data = json.loads(resp.read())
                return name, {"status": "online", **data}
        except Exception as e:
            return name, {"status": "offline", "error": str(e)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(check_node, n, i): n for n, i in NODES.items()}
        for f in as_completed(futures, timeout=REMOTE_TIMEOUT + 2):
            name, result = f.result()
            results[name] = result
    return results

# ---------------------------------------------------------------------------
# Telegram -- callback handler (ONLY on the polling node)
# Routes execution back to the originating node.
# ---------------------------------------------------------------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # --- Code execution approval callbacks: exec-approve:id / exec-deny:id ---
    if data.startswith("exec-"):
        parts = data.split(":", 1)  # ["exec-approve", "abc123"]
        if len(parts) == 2:
            action_str, req_id = parts
            decision = "approved" if "approve" in action_str else "denied"
            try:
                from war_room.code_executor import set_approval
                set_approval(req_id, decision)
                await query.edit_message_text(
                    f"Code execution *{decision}* (`{req_id}`)",
                    parse_mode="Markdown")
            except Exception as _ce:
                await query.edit_message_text(f"Error: {_ce}")
        else:
            await query.edit_message_text("Bad callback data.")
        return

    # --- Command proposal callbacks: addcmd-approve:node:id ---
    if data.startswith("addcmd-"):
        parts = data.split(":", 2)  # ["addcmd-approve", "thor", "abc123"]
        if len(parts) != 3:
            await query.edit_message_text("Bad callback data."); return
        action, origin_node, proposal_id = parts

        if origin_node == THIS_NODE:
            # This IS the polling node -- handle locally
            prop = pending_proposals.pop(proposal_id, None)
            _save_proposals()
            if prop is None:
                await query.edit_message_text("Proposal expired or already handled."); return
            if action == "addcmd-deny":
                await query.edit_message_text(f"Denied: `{prop['name']}`", parse_mode="Markdown"); return
            cmds = _load_commands()
            cmds[prop["name"]] = prop["definition"]
            _save_commands(cmds)
            await query.edit_message_text(f"Added `{prop['name']}` to whitelist.", parse_mode="Markdown"); return
        else:
            # Forward to the origin node
            result = await asyncio.get_event_loop().run_in_executor(
                None, _remote_call, origin_node, "/proposal-result",
                {"proposal_id": proposal_id, "action": action.replace("addcmd-", "")}
            )
            msg = result.get("message", result.get("error", "done"))
            await query.edit_message_text(msg, parse_mode="Markdown"); return

    # --- Regular action callbacks: approve:node:id ---
    parts = data.split(":", 2)
    if len(parts) != 3:
        await query.edit_message_text("Bad callback data."); return
    action, origin_node, request_id = parts

    if origin_node == THIS_NODE:
        # Local -- handle directly
        req = pending_requests.pop(request_id, None)
        _save_pending()
        if req is None:
            await query.edit_message_text("Request expired or already handled."); return
        if action == "deny":
            await query.edit_message_text(f"Denied: `{req['command']}`", parse_mode="Markdown"); return
        await query.edit_message_text(f"Approved. Running `{req['command']}`...", parse_mode="Markdown")
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, execute_command, req["command"], req.get("params", {})
            )
        except Exception as e:
            result = f"Error: {e}"
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=f"*Bifrost - Result*\n\nNode: `{THIS_NODE}`\nCommand: `{req['command']}`\n\n```\n{result[:1500]}\n```",
            parse_mode="Markdown",
        )
    else:
        # Forward approve/deny to origin node
        if action == "deny":
            result = await asyncio.get_event_loop().run_in_executor(
                None, _remote_call, origin_node, "/execute",
                {"request_id": request_id, "action": "deny"}
            )
            msg = result.get("message", "Denied")
            await query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await query.edit_message_text(f"Approved. Routing to `{origin_node}`...", parse_mode="Markdown")
            result = await asyncio.get_event_loop().run_in_executor(
                None, _remote_call, origin_node, "/execute",
                {"request_id": request_id, "action": "approve"}
            )
            msg = result.get("result", result.get("error", "done"))
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=f"*Bifrost - Result*\n\nNode: `{origin_node}`\n\n```\n{msg[:1500]}\n```",
                parse_mode="Markdown",
            )

# ---------------------------------------------------------------------------
# @mention dispatcher — user types "@thor check memory" in Telegram
# Routes to that agent's /ask and sends the reply back
# ---------------------------------------------------------------------------

_KNOWN_AGENTS = {a: info for a, info in NODES.items()}  # name → {ip, port}

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse @agentname messages and route to that agent's /ask endpoint.
    Private chats go straight to Odin without needing @ prefix.
    """
    text = (update.message.text or "").strip()
    log.info("[telegram] incoming message: %r from chat_type=%s",
             text[:80], update.message.chat.type)
    if not text:
        return

    # Determine target agent and query
    if text.startswith("@"):
        # Explicit @mention — route to that agent
        parts = text.split(None, 1)  # ["@thor", "check the memory sync"]
        agent_tag = parts[0].lstrip("@").lower()
        query = parts[1].strip() if len(parts) > 1 else ""
        if not query:
            await update.message.reply_text(f"Usage: @{agent_tag} <your message>")
            return
    else:
        # Private/direct message — route to Odin
        agent_tag = "odin"
        query = text

    node_info = NODES.get(agent_tag)
    if not node_info:
        known = ", ".join(f"@{n}" for n in NODES)
        await update.message.reply_text(f"Unknown agent '{agent_tag}'.\nKnown: {known}")
        return

    await update.message.reply_text(f"Routing to {agent_tag}...")

    def _call_ask():
        url = f"http://{node_info['ip']}:{node_info.get('port', 8765)}/ask"
        body = json.dumps({"query": query, "prompt": query, "caller": "user", "context": "telegram_direct"}).encode()
        req = urllib.request.Request(url, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            return {"error": str(e)}

    result = await asyncio.get_event_loop().run_in_executor(None, _call_ask)
    reply = result.get("reply") or result.get("response") or result.get("error", "(no response)")
    text = f"{agent_tag.upper()}:\n\n{reply[:4000]}"
    try:
        await update.message.reply_text(text)
    except Exception as e:
        log.error("[mention] reply failed: %s", e)
        await update.message.reply_text(f"[{agent_tag}] Response received but couldn't send: {e}")


_SCORE_WEIGHTS = {
    "task:complete":    10,
    "request:approve":   5,
    "command:complete":  3,
    "memory:sync":       2,
    "sync:complete":     1,
    "model:fallback":   -1,
    "sync:failed":      -3,
    "command:error":    -5,
    "node:error":       -8,
}
_ALL_AGENTS = ["odin", "thor", "freya", "heimdall", "huginn", "munnin", "brisinga", "mjolnir"]
_SEASON_BASE_SCORE = 5  # everyone starts each season with 5 pts — ship day bonus

# Simple 60s cache so repeated /leaderboard hits don’t hammer Thor
_lb_cache: dict = {"ts": 0.0, "payload": None}
_LB_CACHE_TTL = 60  # seconds

def _compute_leaderboard() -> tuple:
    """Query Thor’s event log and compute per-agent scores for the current ISO week."""
    import time as _time
    from datetime import datetime, timezone, timedelta

    now_ts = _time.time()
    if _lb_cache["payload"] and (now_ts - _lb_cache["ts"]) < _LB_CACHE_TTL:
        return 200, _lb_cache["payload"]

    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    week_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    since_ts = week_start.timestamp()

    # Fetch from Thor — use a large limit and filter locally (Thor’s GET doesn’t support ?since)
    try:
        url = f"{_EVENT_LOG_URL}?limit=5000"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        all_events = data.get("events", [])
        # Filter to current week client-side
        events = [ev for ev in all_events
                  if float(ev.get("ts") or ev.get("timestamp") or 0) >= since_ts]
    except Exception as e:
        result = {
            "season": f"Week {now.isocalendar()[1]} / {now.year}",
            "leaderboard": [{"rank": i + 1, "agent": a, "score": 0,
                             "breakdown": {}, "note": "event log unreachable"}
                            for i, a in enumerate(_ALL_AGENTS)],
            "error": f"Could not reach event log: {e}",
        }
        return 200, result

    # Compute per-agent scores
    scores = {a: {"total": _SEASON_BASE_SCORE, "breakdown": {"season_bonus": _SEASON_BASE_SCORE}} for a in _ALL_AGENTS}
    for ev in events:
        node  = ev.get("node", "unknown")
        etype = ev.get("event_type") or ev.get("event", "")
        if node not in scores:
            scores[node] = {"total": 0, "breakdown": {}}
        pts = _SCORE_WEIGHTS.get(etype, 0)
        if pts:
            scores[node]["total"] += pts
            scores[node]["breakdown"][etype] = scores[node]["breakdown"].get(etype, 0) + pts

    ranked = sorted(scores.items(), key=lambda x: x[1]["total"], reverse=True)
    leaderboard = [
        {"rank": r, "agent": a, "score": info["total"], "breakdown": info["breakdown"]}
        for r, (a, info) in enumerate(ranked, 1)
    ]

    payload = {
        "season": f"Week {now.isocalendar()[1]} / {now.year}",
        "week_start": week_start.isoformat(),
        "events_this_week": len(events),
        "leaderboard": leaderboard,
    }
    _lb_cache["ts"] = now_ts
    _lb_cache["payload"] = payload
    return 200, payload

# ---------------------------------------------------------------------------
# Direct agent-to-user Telegram notify
# POST /notify { "from": "heimdall", "message": "...", "type": "tattle|praise|alert|note" }
# Works from ANY node — calls Telegram REST API directly, no _bot dependency
# ---------------------------------------------------------------------------

_NOTIFY_EMOJI = {
    "tattle":  "👀",  # sneaky eye
    "praise":  "🏆",  # trophy
    "alert":   "🚨",  # siren
    "note":    "📝",  # memo
    "idea":    "💡",  # bulb
    "question": "❓",  # question
}

def _send_telegram_rest(text: str) -> bool:
    """Send a Telegram message via the REST API — no bot library needed."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    body = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode()
    try:
        req = urllib.request.Request(url, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10): pass
        return True
    except Exception as e:
        log.error("[notify] Telegram REST send failed: %s", e)
        return False


class BifrostHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): log.debug(fmt, *args)

    def do_GET(self):
        try:
            self._do_GET_inner()
        except Exception as e:
            log.exception("Unhandled error in do_GET %s: %s", self.path, e)
            try:
                self._respond(500, {"error": str(e)})
            except Exception:
                pass

    def _do_GET_inner(self):
        # --- Exact-match simple routes ---
        _simple = {
            "/commands":          lambda: self._respond(200, _load_commands()),
            "/cluster-status":    lambda: self._respond(200, _cluster_status()),
            "/node-status":       lambda: self._respond(200, _read_node_status()),
            "/workspace-manifest":lambda: self._respond(200, _build_manifest(SYNC_LOCAL_WORKSPACE)),
        }
        if self.path in _simple:
            _simple[self.path]()
            return

        # --- /health — needs Ollama probe ---
        if self.path == "/health":
            load_info = {"ollama_available": False}
            try:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=2) as r:
                    ps = json.loads(r.read())
                    models = ps.get("models", [])
                    load_info = {
                        "ollama_available": True,
                        "models_loaded": len(models),
                        "active_models": [m.get("name", "?") for m in models],
                        "total_vram_gb": sum(m.get("size_vram", 0) for m in models) / (1024**3),
                    }
            except Exception:
                pass
            self._respond(200, {"status": "ok", "node": THIS_NODE, "platform": sys.platform,
                                "war_room": WAR_ROOM_AVAILABLE, "load": load_info})
            return

        # --- HTML file routes ---
        _html = {
            "/dashboard":  "dashboard.html",
            "/taskboard":  "taskboard.html",
            "/guild-hall": "guild_hall.html",
        }
        if self.path in _html:
            f = BASE / _html[self.path]
            if f.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(f.read_bytes())
            else:
                self._respond(404, {"error": f"{_html[self.path]} not found"})
            return

        # --- /workspace-file?path=... ---
        if self.path.startswith("/workspace-file"):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            rel = params.get("path", [""])[0]
            if not rel:
                self._respond(400, {"error": "missing path param"}); return
            target = SYNC_LOCAL_WORKSPACE / rel.replace("/", os.sep)
            if target.exists() and target.is_file():
                self._respond(200, {"path": rel, "data_b64": base64.b64encode(target.read_bytes()).decode()})
            else:
                self._respond(404, {"error": f"file not found: {rel}"})
            return

        # --- Memory proxy routes (non-master nodes forward to Freya) ---
        if self.path.startswith("/memory-query"):
            if THIS_NODE == MEMORY_MASTER:
                self._respond(503, {"error": "memory master must serve via bifrost_local.py"})
            else:
                qs = self.path.split("?", 1)[1] if "?" in self.path else ""
                self._respond(200, _proxy_memory_query(qs))
            return
        if self.path.startswith("/memory-info"):
            if THIS_NODE == MEMORY_MASTER:
                self._respond(503, {"error": "memory master must serve via bifrost_local.py"})
            else:
                self._respond(200, _proxy_memory_query("__info__"))
            return

        # --- Valhalla War Room GET routes ---
        if _war_room_routes:
            _wr_exact = {
                "/war-room/summary": lambda: _war_room_routes.handle_summary(),
                "/ask/info":         lambda: _war_room_routes.handle_ask_info(),
            }
            if self.path in _wr_exact:
                code, data = _wr_exact[self.path]()
                self._respond(code, data); return
            if self.path.startswith("/war-room/tasks"):
                code, data = _war_room_routes.handle_get_tasks(self.path)
                self._respond(code, data); return
            if self.path.startswith("/war-room/read"):
                code, data = _war_room_routes.handle_read(self.path)
                self._respond(code, data); return
            if self.path.startswith("/war-room/tombstones"):
                code, data = _war_room_routes.handle_tombstones(self.path)
                self._respond(code, data); return
            if self.path.startswith("/war-room/progress"):
                progress = _war_room_routes.store.get_progress()
                self._respond(200, progress); return
        if self.path.startswith("/leaderboard"):
            self._respond(*_compute_leaderboard()); return

        self._respond(404, {"error": "not found"})

    def do_POST(self):
        try:
            self._do_POST_inner()
        except Exception as _top_e:
            log.error("[do_POST] Top-level crash on %s: %s", self.path, _top_e, exc_info=True)
            try:
                self._respond(500, {"error": "server error", "detail": str(_top_e)})
            except Exception:
                pass

    def _do_POST_inner(self):
        # Original Bifrost routes
        bifrost_routes = ("/request", "/propose-command", "/receive-files", "/fetch-file", "/execute", "/proposal-result", "/self-update", "/hook", "/notify", "/memory-sync", "/node-status", "/execute-code")
        # War Room routes
        war_room_routes = ("/war-room/post", "/war-room/task", "/war-room/claim",
                           "/war-room/complete", "/war-room/status", "/ask",
                           "/war-room/delete-task", "/war-room/delete-message",
                           "/war-room/clear-messages", "/war-room/summon",
                           "/war-room/progress")
        all_routes = bifrost_routes + war_room_routes

        if self.path not in all_routes:
            self._respond(404, {"error": "not found"}); return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except Exception:
            self._respond(400, {"error": "invalid JSON"}); return

        # --- War Room POST routes ---
        if self.path in war_room_routes and _war_room_routes:
            # Use string names + getattr so missing optional methods only error
            # if that specific path is called — not on every other request
            wr_map = {
                "/war-room/post": "handle_post_message",
                "/war-room/task": "handle_post_task",
                "/war-room/claim": "handle_claim_task",
                "/war-room/complete": "handle_complete_task",
                "/war-room/status": "handle_update_status",
                "/ask": "handle_ask",
                "/war-room/delete-task": "handle_delete_task",
                "/war-room/delete-message": "handle_delete_message",
                "/war-room/clear-messages": "handle_clear_messages",
                "/war-room/summon": "handle_summon",
                "/war-room/progress": "handle_progress",
            }
            method_name = wr_map.get(self.path)
            wr_handler = getattr(_war_room_routes, method_name, None) if method_name else None
            if wr_handler:
                try:
                    code, data = wr_handler(body)
                    self._respond(code, data)
                except Exception as _e:
                    log.error("[war-room] POST %s handler crashed: %s", self.path, _e, exc_info=True)
                    self._respond(500, {"error": "internal handler error", "detail": str(_e)})
                return

        # --- Original Bifrost POST routes ---
        handler = {
            "/request": self._handle_request,
            "/propose-command": self._handle_propose,
            "/receive-files": self._handle_receive,
            "/fetch-file": self._handle_fetch_file,
            "/execute": self._handle_execute,
            "/proposal-result": self._handle_proposal_result,
            "/self-update": self._handle_self_update,
            "/hook":        self._handle_hook,
            "/notify":      self._handle_notify,
            "/memory-sync": self._handle_memory_sync,
            "/node-status": self._handle_node_status_post,
            "/execute-code": self._handle_execute_code,
        }.get(self.path)
        if handler:
            handler(body)
        else:
            self._respond(404, {"error": "not found"})

    def _handle_hook(self, body: dict):
        """Accept a hook event from any node and dispatch it through HookEngine."""
        event = body.get("event", "")
        if not event:
            self._respond(400, {"error": "event field required"}); return
        payload = body.get("payload", body)
        source  = body.get("node") or THIS_NODE
        _hooks.emit(event, payload, source_node=source)
        self._respond(200, {"status": "ok", "event": event, "source": source})

    def _handle_notify(self, body: dict):
        """Any agent can ping the user directly via Telegram.
        Body: { "from": "heimdall", "message": "...", "type": "tattle|praise|alert|note|idea|question" }
        """
        sender  = body.get("from", "unknown")
        message = body.get("message", "").strip()
        mtype   = body.get("type", "note").lower()
        if not message:
            self._respond(400, {"error": "message required"}); return
        emoji = _NOTIFY_EMOJI.get(mtype, "💬")
        target = body.get("about", "")  # optional — who they're tattling/praising
        header = f"{emoji} *{sender.upper()}*"
        if target:
            header += f" → about *{target.upper()}*"
        text = f"{header}\n\n{message}"
        ok = _send_telegram_rest(text)
        self._respond(200 if ok else 502, {"status": "sent" if ok else "failed", "from": sender})

    def _handle_node_status_post(self, body: dict):
        """Update this node's status.
        Body: { "status": "working", "last_task": "Fix CSS bug", "detail": "..." }
        """
        status = body.get("status", "idle")
        last_task = body.get("last_task")
        detail = body.get("detail")
        _write_node_status(status, last_task, detail)
        self._respond(200, _read_node_status())

    def _handle_memory_sync(self, body: dict):
        """Write a memory to the canonical shared store (Freya by default).
        Body: { "node": "thor", "text": "...", "importance": 0.8, "tags": [...], "decay": true }
        Non-master nodes proxy to the master transparently.
        """
        # Stamp the originating node if not set
        if "node" not in body:
            body["node"] = THIS_NODE
        if THIS_NODE == MEMORY_MASTER:
            # Master node — bifrost_local.py handles the actual write
            self._respond(503, {"error": "memory master: install bifrost_local.py with write handler"})
        else:
            result = _proxy_memory_write(body)
            if "error" in result:
                self._respond(502, result)
            else:
                self._respond(200, result)

    def _handle_self_update(self, body: dict):
        """Pull latest codebase via git and re-exec this process."""
        try:
            import subprocess
            repo_root = str(BASE.parent)
            log.info("self-update: repo at %s", repo_root)

            # Auto-detect the git remote name (origin, github, etc.)
            try:
                remotes = subprocess.check_output(
                    ["git", "remote"], cwd=repo_root, text=True, timeout=5
                ).strip().split("\n")
                # Prefer 'origin', then 'github', then first available
                remote = "origin"
                if "origin" in remotes:
                    remote = "origin"
                elif "github" in remotes:
                    remote = "github"
                elif remotes and remotes[0]:
                    remote = remotes[0]
            except Exception:
                remote = "origin"

            # Stash any local changes to prevent "uncommitted changes" errors
            subprocess.run(
                ["git", "stash", "--include-untracked"],
                cwd=repo_root, capture_output=True, text=True, timeout=10
            )

            # Pull latest
            result = subprocess.run(
                ["git", "pull", "--rebase", remote, "main"],
                cwd=repo_root,
                capture_output=True, text=True, timeout=60
            )
            out = result.stdout.strip() or result.stderr.strip()

            # If rebase failed, try plain pull
            if result.returncode != 0:
                subprocess.run(
                    ["git", "rebase", "--abort"],
                    cwd=repo_root, capture_output=True, timeout=10
                )
                result = subprocess.run(
                    ["git", "pull", remote, "main"],
                    cwd=repo_root,
                    capture_output=True, text=True, timeout=60
                )
                out = result.stdout.strip() or result.stderr.strip()

            log.info("self-update result: %s", out)
            self._respond(200, {"status": "ok", "output": out, "note": "restarting"})
            
            # Restart: re-exec current interpreter with same args
            def _restart():
                import time as _t; _t.sleep(0.5)
                if sys.platform == "win32":
                    subprocess.Popen([sys.executable] + sys.argv)
                    os._exit(0)
                else:
                    os.execv(sys.executable, [sys.executable] + sys.argv)
            threading.Thread(target=_restart, daemon=True).start()
        except Exception as e:
            log.error("self-update failed: %s", e)
            self._respond(500, {"error": str(e)})

    def _handle_receive(self, body: dict):
        dst_path = body.get("dst_path", "")
        filename = body.get("filename", "")
        data_b64 = body.get("data_b64") or body.get("data_hex")  # support both for backwards compat
        if not dst_path or not filename or not data_b64:
            self._respond(400, {"error": "dst_path, filename, data_b64 required"}); return
        try:
            out_dir = Path(dst_path)
            out_dir.mkdir(parents=True, exist_ok=True)
            # Detect encoding: base64 or legacy hex
            if body.get("data_b64"):
                raw = base64.b64decode(data_b64)
            else:
                raw = bytes.fromhex(data_b64)
            (out_dir / filename).write_bytes(raw)
            log.info("Received file: %s/%s", dst_path, filename)
            self._respond(200, {"status": "ok", "file": filename})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _handle_fetch_file(self, body: dict):
        """Let another node pull a file FROM this node."""
        file_path = body.get("path", "")
        if not file_path:
            self._respond(400, {"error": "'path' required"}); return
        try:
            p = Path(file_path)
            if not p.exists() or not p.is_file():
                self._respond(404, {"error": f"file not found: {file_path}"}); return
            data = base64.b64encode(p.read_bytes()).decode()
            self._respond(200, {"filename": p.name, "data_b64": data, "size": p.stat().st_size})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _handle_execute(self, body: dict):
        """Called by the polling node when user taps Approve/Deny."""
        request_id = body.get("request_id", "")
        action = body.get("action", "")
        req = pending_requests.pop(request_id, None)
        _save_pending()
        if req is None:
            self._respond(404, {"message": "Request expired or already handled."}); return
        if action == "deny":
            log.info("Request %s denied by user", request_id)
            _audit("request", req.get("caller", "?"), req["command"], "deny")
            self._respond(200, {"message": f"Denied: `{req['command']}`"}); return
        log.info("Request %s approved -- executing %s", request_id, req["command"])
        try:
            result = execute_command(req["command"], req.get("params", {}))
        except Exception as e:
            result = f"Error: {e}"
        _audit("request", req.get("caller", "?"), req["command"], "approve", result)
        self._respond(200, {"result": result})

    def _handle_execute_code(self, body: dict):
        """POST /execute-code — run code in sandboxed subprocess with human approval."""
        code = body.get("code", "")
        language = body.get("language", "python")
        timeout = body.get("timeout", 30)
        task_id = body.get("task_id", "")
        require_approval = body.get("require_approval", True)
        if not code:
            self._respond(400, {"error": "'code' field required"}); return
        # Run in thread to avoid blocking (approval can take minutes)
        import threading
        result_holder = {}
        def _run():
            try:
                from war_room.code_executor import execute_code
                result_holder["result"] = execute_code(
                    code, language=language, timeout=timeout,
                    task_id=task_id, require_approval=require_approval)
            except Exception as e:
                result_holder["result"] = {"ok": False, "error": str(e)}
        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=360)  # 6 min max (5 min approval + 1 min execution)
        if t.is_alive():
            self._respond(504, {"error": "execution timed out"}); return
        self._respond(200, result_holder.get("result", {"error": "no result"}))

    def _handle_proposal_result(self, body: dict):
        """Called by the polling node when user approves/denies a command proposal."""
        proposal_id = body.get("proposal_id", "")
        action = body.get("action", "")
        prop = pending_proposals.pop(proposal_id, None)
        _save_proposals()
        if prop is None:
            self._respond(404, {"message": "Proposal expired or already handled."}); return
        if action == "deny":
            _audit("proposal", prop.get("caller", "?"), prop["name"], "deny")
            self._respond(200, {"message": f"Denied proposal: `{prop['name']}`"}); return
        cmds = _load_commands()
        cmds[prop["name"]] = prop["definition"]
        _save_commands(cmds)
        log.info("Command '%s' added to whitelist by remote approval", prop["name"])
        _audit("proposal", prop.get("caller", "?"), prop["name"], "approve", "added to whitelist")
        self._respond(200, {"message": f"Added `{prop['name']}` to whitelist."})

    def _handle_propose(self, body: dict):
        caller = body.get("caller", "unknown")
        name = body.get("name", "")
        defn = body.get("definition")
        if not name or not defn:
            self._respond(400, {"error": "'name' and 'definition' required"}); return
        cmds = _load_commands()
        if name in cmds:
            self._respond(409, {"error": f"'{name}' already exists"}); return
        proposal_id = uuid.uuid4().hex[:8]
        prop = {"caller": caller, "name": name, "definition": defn}
        pending_proposals[proposal_id] = prop
        _save_proposals()
        log.info("Queued proposal %s: '%s' from %s", proposal_id, name, caller)
        asyncio.run_coroutine_threadsafe(send_proposal_approval(proposal_id, prop), _event_loop)
        self._respond(200, {"status": "pending", "proposal_id": proposal_id})

    def _handle_request(self, req: dict):
        caller = req.get("caller", "unknown")
        command = req.get("command", "")
        cmds = _load_commands()
        if command not in cmds:
            self._respond(403, {"error": f"'{command}' not whitelisted"}); return
        if caller not in cmds[command].get("allowed_callers", []):
            self._respond(403, {"error": f"'{caller}' not allowed for '{command}'"}); return
        request_id = uuid.uuid4().hex[:8]
        pending_requests[request_id] = req
        _save_pending()
        log.info("Queued %s: %s from %s", request_id, command, caller)
        asyncio.run_coroutine_threadsafe(send_approval_request(request_id, req), _event_loop)
        self._respond(200, {"status": "pending", "request_id": request_id})

    def _respond(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Bifrost-Node, X-Bifrost-Signature")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

async def on_startup(app: Application):
    global _event_loop, _bot
    _event_loop = asyncio.get_running_loop()
    _bot = app.bot
    threading.Thread(target=run_http_server, daemon=True).start()
    # Start War Room daemons
    if _gossip_sync:
        _gossip_sync.start()
    if _overseer:
        _overseer.start()
    if _workspace_sync:
        _workspace_sync.start()
    # Start task poller
    if WAR_ROOM_AVAILABLE:
        global _task_poller
        _task_poller = TaskPoller(THIS_NODE)
        _task_poller.start()
    if _philosopher:
        _philosopher.start()
    log.info("Bifrost v5 FULL mode ready on '%s' (war_room=%s)", THIS_NODE, WAR_ROOM_AVAILABLE)

def _load_local_extensions():
    """Load node-local route extensions from bifrost_local.py if it exists.
    This file is NEVER pushed by Odin — each node owns it permanently.
    It must define: register_routes(handler_class, config) -> None
    """
    local_path = BASE / "bifrost_local.py"
    if not local_path.exists():
        backup_path = BASE / f"bifrost_local.{THIS_NODE}.py"
        if backup_path.exists():
            try:
                import shutil
                shutil.copy2(backup_path, local_path)
                log.info("Auto-restored missing bifrost_local.py from %s", backup_path.name)
            except Exception as e:
                log.error("Failed to auto-restore bifrost_local.py: %s", e)
                return
        else:
            return
            
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("bifrost_local", local_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "register_routes"):
            mod.register_routes(BifrostHandler, CONFIG)
            log.info("Loaded local extensions from bifrost_local.py")
    except Exception as e:
        log.error("Failed to load bifrost_local.py: %s", e)

def run_http_server():
    _load_local_extensions()
    server = ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), BifrostHandler)
    log.info("HTTP listening on port %d", LISTEN_PORT)
    server.serve_forever()

def _check_single_instance():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", LISTEN_PORT))
        s.close()
    except OSError:
        log.error("Port %d in use -- exiting.", LISTEN_PORT)
        raise SystemExit(1)

# ---------------------------------------------------------------------------
# Task Poller — auto-process assigned tasks from War Room
# ---------------------------------------------------------------------------

class TaskPoller:
    """Background daemon that polls War Room for tasks assigned to this node."""

    POLL_INTERVAL = 60  # 1 minute — responsive task pickup
    _active_tasks: set  # track in-flight task IDs

    def __init__(self, node_name: str, port: int = LISTEN_PORT):
        self.node = node_name
        self.base = f"http://127.0.0.1:{port}"
        self._active_tasks = set()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name="task-poller")
        self._thread.start()
        log.info("[task-poller] Started for '%s' (every %ds)", self.node, self.POLL_INTERVAL)

    def _loop(self):
        import time
        time.sleep(30)  # initial delay — let server finish starting
        while True:
            try:
                self._poll()
            except Exception as e:
                log.error("[task-poller] Error: %s", e)
            time.sleep(self.POLL_INTERVAL)

    def _poll(self):
        """Check for open tasks assigned to this node."""
        import urllib.request
        url = f"{self.base}/war-room/tasks?assigned_to={self.node}&status=open"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as r:
                tasks = json.loads(r.read())
        except Exception:
            return  # server not ready or no war room

        if isinstance(tasks, dict):
            tasks = list(tasks.values())

        for task in tasks:
            tid = task.get("id", "")
            if not tid or tid in self._active_tasks:
                continue
            # Don't auto-process decompose parent tasks (octopus handles those)
            if task.get("decompose"):
                continue
            self._active_tasks.add(tid)
            threading.Thread(
                target=self._process_task, args=(task,), daemon=True,
                name=f"task-worker-{tid[:8]}"
            ).start()

    def _process_task(self, task: dict):
        """Claim → progress ping → process via /ask → complete."""
        import urllib.request
        tid = task["id"]
        title = task.get("title", "untitled")
        desc = task.get("description", title)
        log.info("[task-poller] Processing: %s (%s)", title, tid[:8])

        def _ping(note, pct=-1):
            try:
                self._post(f"{self.base}/war-room/progress", {
                    "task_id": tid, "agent": self.node,
                    "note": note, "percent": pct
                })
            except Exception:
                pass

        try:
            # 1. Claim the task
            _ping("Claiming task...")
            self._post(f"{self.base}/war-room/claim", {
                "task_id": tid, "agent_id": self.node
            })

            # 2. Update status to in_progress
            self._post(f"{self.base}/war-room/status", {
                "task_id": tid, "agent_id": self.node, "status": "in_progress"
            })

            # 3. Process via /ask — use cloud model for "deep" tier tasks
            tier = task.get("tier", "fast")
            model = "cloud" if tier == "deep" else "local"
            _ping(f"Thinking ({tier})...", 25)
            prompt = (
                f"You have been assigned a task from the War Room.\n"
                f"Task: {title}\n"
                f"Description: {desc}\n\n"
                f"Complete this task thoroughly. Provide your result."
            )
            result_data = self._post(f"{self.base}/ask", {
                "prompt": prompt, "model": model
            })
            result_text = result_data.get("response", result_data.get("answer", str(result_data)))

            # 4. Complete the task
            _ping("Submitting result...", 90)
            self._post(f"{self.base}/war-room/complete", {
                "task_id": tid,
                "agent_id": self.node,
                "result": result_text[:2000]  # cap result size
            })
            _ping("Done ✓", 100)
            log.info("[task-poller] Completed: %s (%s)", title, tid[:8])

        except Exception as e:
            log.error("[task-poller] Failed task %s: %s", tid[:8], e)
            _ping(f"Blocked: {str(e)[:80]}")
            # Mark blocked so it shows up in Guild Hall
            try:
                self._post(f"{self.base}/war-room/status", {
                    "task_id": tid, "agent_id": self.node,
                    "status": "blocked", "reason": str(e)[:200]
                })
            except Exception:
                pass
        finally:
            self._active_tasks.discard(tid)

    def _post(self, url: str, body: dict) -> dict:
        import urllib.request
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

_task_poller = None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _event_loop, _bot
    _check_single_instance()
    log.info("Starting Bifrost v5 on '%s' (polling=%s)", THIS_NODE, TELEGRAM_POLLING)

    if not TELEGRAM_POLLING:
        log.info("Send-only mode (no callback handling)")
        _event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_event_loop)
        # HTTP first — always reachable regardless of Telegram state
        threading.Thread(target=run_http_server, daemon=True, name="http-server").start()
        try:
            _bot = Application.builder().token(BOT_TOKEN).build().bot
        except Exception as _tg_e:
            log.warning("Telegram bot init failed (non-fatal): %s", _tg_e)
        # Start War Room daemons
        if _gossip_sync:
            _gossip_sync.start()
        if _overseer:
            _overseer.start()
        if _workspace_sync:
            _workspace_sync.start()
        # Start task poller
        if WAR_ROOM_AVAILABLE:
            global _task_poller
            _task_poller = TaskPoller(THIS_NODE)
            _task_poller.start()
        log.info("Bifrost v5 SEND-ONLY ready on '%s' (war_room=%s)", THIS_NODE, WAR_ROOM_AVAILABLE)
        _event_loop.run_forever()  # asyncio owns main thread
        return

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

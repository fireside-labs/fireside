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
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each request in a new thread so /ask doesn't freeze the node."""
    daemon_threads = True


from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bifrost")

# Sparse-checkout path fix: on Freya/sparse-checkout, war_room lives in bot/ subdirectory
_wr_sub = __import__('pathlib').Path(__file__).parent / 'bot'
if _wr_sub.exists() and str(_wr_sub) not in __import__('sys').path:
    __import__('sys').path.insert(0, str(_wr_sub))

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
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent
CONFIG = json.loads((BASE / "config.json").read_text())
COMMANDS_FILE = BASE / "commands.json"

def _load_commands() -> dict:
    return json.loads(COMMANDS_FILE.read_text())

def _save_commands(cmds: dict):
    COMMANDS_FILE.write_text(json.dumps(cmds, indent=2))

BOT_TOKEN = CONFIG["telegram_bot_token"]
CHAT_ID = CONFIG["telegram_chat_id"]
LISTEN_PORT = CONFIG.get("listen_port", 8765)
THIS_NODE = CONFIG.get("this_node", "unknown")
NODES = CONFIG.get("nodes", {})
TELEGRAM_POLLING = CONFIG.get("telegram_polling", True)
AGENT_CONFIG = CONFIG.get("agent", {"id": THIS_NODE, "role": "general", "local_model": "qwen3.5:27b"})
WAR_ROOM_CONFIG = CONFIG.get("war_room", {})

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
        result = subprocess.run([python, cmd["script"]], capture_output=True, text=True, timeout=120)
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
    desc = cmds.get(req["command"], {}).get("description", req["command"])
    params_str = json.dumps(req.get("params", {}), indent=2) or "(none)"
    text = (
        f"*Bifrost - Action Request*\n\n"
        f"Node:    `{THIS_NODE}`\n"
        f"From:    `{req['caller']}`\n"
        f"Action:  `{req['command']}`\n"
        f"Details: {desc}\n"
        f"Params:\n```\n{params_str}\n```"
    )
    # Callback data encodes: action:node:request_id
    # so the polling node knows where to route the callback
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
# HTTP server
# ---------------------------------------------------------------------------

class BifrostHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): log.debug(fmt, *args)

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {
                "status": "ok", "node": THIS_NODE, "platform": sys.platform,
                "war_room": WAR_ROOM_AVAILABLE,
            })
        elif self.path == "/commands":
            self._respond(200, _load_commands())
        elif self.path == "/cluster-status":
            self._respond(200, _cluster_status())
        # --- Valhalla War Room GET routes ---
        elif self.path.startswith("/war-room/read") and _war_room_routes:
            code, data = _war_room_routes.handle_read(self.path)
            self._respond(code, data)
        elif self.path.startswith("/war-room/tasks") and _war_room_routes:
            code, data = _war_room_routes.handle_get_tasks(self.path)
            self._respond(code, data)
        elif self.path == "/war-room/summary" and _war_room_routes:
            code, data = _war_room_routes.handle_summary()
            self._respond(code, data)
        elif self.path == "/ask/info" and _war_room_routes:
            code, data = _war_room_routes.handle_ask_info()
            self._respond(code, data)
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        # Original Bifrost routes
        bifrost_routes = ("/request", "/propose-command", "/receive-files", "/fetch-file", "/execute", "/proposal-result")
        # War Room routes
        war_room_routes = ("/war-room/post", "/war-room/task", "/war-room/claim",
                           "/war-room/complete", "/war-room/status", "/ask")
        all_routes = bifrost_routes + war_room_routes

        if self.path not in all_routes:
            self._respond(404, {"error": "not found"}); return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except Exception:
            self._respond(400, {"error": "invalid JSON"}); return

        # --- War Room POST routes ---
        if self.path in war_room_routes and _war_room_routes:
            wr_handler = {
                "/war-room/post": _war_room_routes.handle_post_message,
                "/war-room/task": _war_room_routes.handle_post_task,
                "/war-room/claim": _war_room_routes.handle_claim_task,
                "/war-room/complete": _war_room_routes.handle_complete_task,
                "/war-room/status": _war_room_routes.handle_update_status,
                "/ask": _war_room_routes.handle_ask,
            }.get(self.path)
            if wr_handler:
                code, data = wr_handler(body)
                self._respond(code, data)
                return

        # --- Original Bifrost POST routes ---
        handler = {
            "/request": self._handle_request,
            "/propose-command": self._handle_propose,
            "/receive-files": self._handle_receive,
            "/fetch-file": self._handle_fetch_file,
            "/execute": self._handle_execute,
            "/proposal-result": self._handle_proposal_result,
        }.get(self.path)
        if handler:
            handler(body)
        else:
            self._respond(404, {"error": "not found"})

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
            self._respond(200, {"message": f"Denied: `{req['command']}`"}); return
        log.info("Request %s approved -- executing %s", request_id, req["command"])
        try:
            result = execute_command(req["command"], req.get("params", {}))
        except Exception as e:
            result = f"Error: {e}"
        self._respond(200, {"result": result})

    def _handle_proposal_result(self, body: dict):
        """Called by the polling node when user approves/denies a command proposal."""
        proposal_id = body.get("proposal_id", "")
        action = body.get("action", "")
        prop = pending_proposals.pop(proposal_id, None)
        _save_proposals()
        if prop is None:
            self._respond(404, {"message": "Proposal expired or already handled."}); return
        if action == "deny":
            self._respond(200, {"message": f"Denied proposal: `{prop['name']}`"}); return
        cmds = _load_commands()
        cmds[prop["name"]] = prop["definition"]
        _save_commands(cmds)
        log.info("Command '%s' added to whitelist by remote approval", prop["name"])
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
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
    log.info("Bifrost v5 FULL mode ready on '%s' (war_room=%s)", THIS_NODE, WAR_ROOM_AVAILABLE)

def run_http_server():
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
        _bot = Application.builder().token(BOT_TOKEN).build().bot
        threading.Thread(target=run_http_server, daemon=True).start()
        # Start War Room daemons
        if _gossip_sync:
            _gossip_sync.start()
        if _overseer:
            _overseer.start()
        log.info("Bifrost v5 SEND-ONLY ready on '%s' (war_room=%s)", THIS_NODE, WAR_ROOM_AVAILABLE)
        _event_loop.run_forever()
        return

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

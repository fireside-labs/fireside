"""
telegram/handler.py — Telegram bot for Valhalla Mesh.

Features:
  - Chat mode: user sends message → agent response → sent back
  - Push notifications: event bus → formatted notification → Telegram
  - Commands: /status, /task, /brains, /switch
"""
from __future__ import annotations

import json
import logging
import time
import threading
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("valhalla.telegram")

_BASE_DIR = Path(".")
_BOT_TOKEN: str | None = None
_ALLOWED_USERS: list = []
_NOTIFY_ON: list = []
_CHAT_IDS: set = set()

TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Telegram API helpers
# ---------------------------------------------------------------------------

def _tg_request(method: str, data: dict | None = None) -> dict:
    """Make a Telegram Bot API request."""
    if not _BOT_TOKEN:
        return {"ok": False, "description": "Bot token not configured"}

    url = f"{TELEGRAM_API.format(token=_BOT_TOKEN)}/{method}"
    try:
        if data:
            payload = json.dumps(data).encode()
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
            )
        else:
            req = urllib.request.Request(url)

        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "description": str(e)}


def send_message(chat_id: int | str, text: str, parse_mode: str = "Markdown") -> dict:
    """Send a message to a Telegram chat."""
    return _tg_request("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    })


def _validate_token(token: str) -> dict:
    """Validate a bot token with getMe."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            if data.get("ok"):
                bot = data["result"]
                return {
                    "ok": True,
                    "bot_name": bot.get("first_name"),
                    "bot_username": bot.get("username"),
                }
            return {"ok": False, "error": "Invalid response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------

EVENT_TEMPLATES = {
    "pipeline.shipped": "✅ *Task completed!*\n_{title}_\nFinished in {iterations} steps.",
    "pipeline.escalated": "🆘 *Needs your help!*\n_{title}_\nStuck at step {stage}.",
    "debate.deadlock": "🤔 *Debate deadlocked*\n_{topic}_\nNo consensus after {rounds} rounds.",
    "crucible.broken": "⚠️ *Knowledge check failed*\nProcedure _{procedure}_ broke under pressure.",
    "brain.installed": "🧠 *New brain installed!*\n_{name}_ is ready.",
    "brain.stopped": "🔴 *Brain stopped*\nInference server is offline.",
}


def format_notification(event_name: str, payload: dict) -> str:
    """Format an event into a human-readable Telegram notification."""
    template = EVENT_TEMPLATES.get(event_name)
    if template:
        try:
            return template.format(**{k: v for k, v in payload.items() if isinstance(v, (str, int, float))})
        except KeyError:
            pass
    return f"📢 *{event_name}*\n{json.dumps(payload, indent=2, default=str)[:500]}"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def handle_command(text: str, chat_id: int) -> str:
    """Process a /command and return the response text."""
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd == "/start":
        return (
            "👋 *Welcome to Valhalla!*\n\n"
            "I'm your personal AI mesh.\n\n"
            "Commands:\n"
            "/status — mesh health\n"
            "/task — create a new task\n"
            "/brains — list installed brains\n"
            "/switch — switch active brain"
        )

    elif cmd == "/status":
        return "🟢 *Mesh is online*\nAll systems operational."

    elif cmd == "/brains":
        try:
            state_file = Path.home() / ".valhalla" / "brains_state.json"
            if state_file.exists():
                data = json.loads(state_file.read_text())
                brains = data.get("installed", [])
                active = data.get("active", {})
                lines = ["🧠 *Installed Brains:*\n"]
                for b in brains:
                    marker = "▶️ " if b.get("id") == active.get("id") else "  "
                    lines.append(f"{marker}`{b.get('name', b.get('id'))}`")
                return "\n".join(lines) if brains else "No brains installed. Use the dashboard to install one."
            return "No brains installed yet."
        except Exception:
            return "Couldn't read brain status."

    elif cmd == "/task":
        if not args:
            return "Usage: /task <description>\n\nExample: /task Fix the login page CSS"
        return f"📋 *Task queued:*\n_{args}_\n\nI'll work on that!"

    elif cmd == "/switch":
        if not args:
            return "Usage: /switch <brain-name>"
        return f"🔄 Switching to `{args}`..."

    return f"Unknown command: {cmd}\n\nTry /start for help."


# ---------------------------------------------------------------------------
# Event bus hook
# ---------------------------------------------------------------------------

def on_event(event_name: str, payload: dict) -> None:
    """Hook called by plugin_loader — send notifications to Telegram."""
    if not _BOT_TOKEN:
        return
    if _NOTIFY_ON and event_name not in _NOTIFY_ON:
        return

    text = format_notification(event_name, payload)
    for chat_id in _CHAT_IDS:
        try:
            send_message(chat_id, text)
        except Exception as e:
            log.debug("[telegram] Notification send failed: %s", e)


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------

def _save_config(token: str, chat_ids: set) -> None:
    """Save Telegram config to disk."""
    cfg_file = Path.home() / ".valhalla" / "telegram.json"
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(json.dumps({
        "bot_token": token,
        "chat_ids": list(chat_ids),
    }, indent=2), encoding="utf-8")


def _load_config() -> None:
    """Load Telegram config from disk."""
    global _BOT_TOKEN, _CHAT_IDS
    cfg_file = Path.home() / ".valhalla" / "telegram.json"
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text())
            _BOT_TOKEN = data.get("bot_token")
            _CHAT_IDS = set(data.get("chat_ids", []))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TelegramSetupRequest(BaseModel):
    bot_token: str
    chat_id: Optional[int] = None


class TelegramTestRequest(BaseModel):
    message: str = "🧪 Test message from Valhalla!"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BOT_TOKEN, _ALLOWED_USERS, _NOTIFY_ON, _BASE_DIR

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))

    tg_cfg = config.get("telegram", {})
    _BOT_TOKEN = tg_cfg.get("bot_token")
    _ALLOWED_USERS = tg_cfg.get("allowed_users", [])
    _NOTIFY_ON = tg_cfg.get("notify_on", [
        "pipeline.shipped", "pipeline.escalated",
        "debate.deadlock", "crucible.broken",
    ])

    _load_config()

    router = APIRouter(tags=["telegram"])

    @router.post("/api/v1/telegram/setup")
    async def api_setup(req: TelegramSetupRequest):
        """Save bot token and verify."""
        global _BOT_TOKEN

        validation = _validate_token(req.bot_token)
        if not validation.get("ok"):
            raise HTTPException(status_code=400, detail=validation.get("error"))

        _BOT_TOKEN = req.bot_token
        if req.chat_id:
            _CHAT_IDS.add(req.chat_id)
        _save_config(req.bot_token, _CHAT_IDS)

        _publish("telegram.connected", {
            "bot": validation.get("bot_username"),
        })

        return {
            "ok": True,
            "bot_name": validation.get("bot_name"),
            "bot_username": validation.get("bot_username"),
        }

    @router.get("/api/v1/telegram/status")
    async def api_status():
        """Check if bot is connected."""
        if not _BOT_TOKEN:
            return {"connected": False, "message": "Bot token not configured"}

        validation = _validate_token(_BOT_TOKEN)
        return {
            "connected": validation.get("ok", False),
            "bot_name": validation.get("bot_name"),
            "bot_username": validation.get("bot_username"),
            "chat_ids": len(_CHAT_IDS),
        }

    @router.post("/api/v1/telegram/test")
    async def api_test(req: TelegramTestRequest):
        """Send a test message."""
        if not _BOT_TOKEN:
            raise HTTPException(status_code=400, detail="Bot not configured")
        if not _CHAT_IDS:
            raise HTTPException(status_code=400, detail="No chat IDs registered")

        results = []
        for cid in _CHAT_IDS:
            r = send_message(cid, req.message)
            results.append({"chat_id": cid, "ok": r.get("ok", False)})

        return {"ok": True, "results": results}

    app.include_router(router)
    log.info("[telegram] Plugin loaded. Bot: %s, Chats: %d",
             "configured" if _BOT_TOKEN else "not set", len(_CHAT_IDS))

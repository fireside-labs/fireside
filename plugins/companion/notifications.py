"""
companion/notifications.py — Expo Push Notification infrastructure.

Sprint 3: Sends push notifications via Expo's push service.
No Firebase/APNs setup required — Expo handles routing.

Push token stored in ~/.valhalla/push_token.json
Notification state (rate limit timestamps) in ~/.valhalla/notification_state.json
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.companion.notifications")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# Rate limit: max 1 notification per trigger type per hour
_NOTIFICATION_COOLDOWN = 3600  # seconds


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def _token_file() -> Path:
    return Path.home() / ".valhalla" / "push_token.json"


def _state_file() -> Path:
    return Path.home() / ".valhalla" / "notification_state.json"


def save_push_token(expo_token: str) -> dict:
    """Store the Expo push token from the mobile app."""
    token_dir = Path.home() / ".valhalla"
    token_dir.mkdir(parents=True, exist_ok=True)
    _token_file().write_text(
        json.dumps({"token": expo_token, "registered_at": time.time()}),
        encoding="utf-8",
    )
    log.info("[notifications] Push token registered: %s…", expo_token[:20])
    return {"ok": True, "token": expo_token}


def get_push_token() -> Optional[str]:
    """Retrieve the stored Expo push token, or None."""
    f = _token_file()
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return data.get("token")
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Rate limiting per notification type
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    f = _state_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    f = _state_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state), encoding="utf-8")


def _can_send(trigger_type: str) -> bool:
    """Check if we can send a notification for this trigger type (1/hour)."""
    state = _load_state()
    last_sent = state.get(trigger_type, 0)
    return (time.time() - last_sent) >= _NOTIFICATION_COOLDOWN


def _mark_sent(trigger_type: str) -> None:
    """Record that we sent a notification for this trigger type."""
    state = _load_state()
    state[trigger_type] = time.time()
    _save_state(state)


# ---------------------------------------------------------------------------
# Send push notification
# ---------------------------------------------------------------------------

async def send_push(token: str, title: str, body: str, data: dict = None) -> dict:
    """Send a push notification via Expo's push service."""
    try:
        import httpx
    except ImportError:
        log.warning("[notifications] httpx not installed — push notifications disabled")
        return {"ok": False, "error": "httpx not installed"}

    message = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
    }
    if data:
        message["data"] = data

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(EXPO_PUSH_URL, json=message)
            result = resp.json()
            log.info("[notifications] Push sent: %s → %s", title, result)
            return {"ok": True, **result}
    except Exception as e:
        log.error("[notifications] Push failed: %s", e)
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Companion-initiated notification triggers (Sprint 3 Task 2)
# ---------------------------------------------------------------------------

async def check_and_notify(state: dict) -> list[str]:
    """Check companion state and send relevant push notifications.

    Called periodically (e.g., during apply_decay or on state change).
    Returns list of trigger types that fired.

    Triggers:
    1. happiness < 30 → "Your companion misses you!"
    2. daily gift ready → "(Name) has a surprise for you!"
    3. task completed → "Your task is done!"
    4. companion leveled up → "(Name) reached level N!"
    """
    token = get_push_token()
    if not token:
        return []

    fired = []
    name = state.get("name", "Companion")

    # --- Trigger 1: Low happiness ---
    happiness = state.get("happiness", 100)
    if happiness < 30 and _can_send("low_happiness"):
        await send_push(
            token,
            f"{name} misses you! 🥺",
            "Come say hi — your companion's happiness is low.",
            {"trigger": "low_happiness", "happiness": happiness},
        )
        _mark_sent("low_happiness")
        fired.append("low_happiness")

    # --- Trigger 2: Daily gift ready ---
    last_gift = state.get("last_daily_gift", 0)
    if (time.time() - last_gift) > 86400 and _can_send("daily_gift"):  # 24 hours
        await send_push(
            token,
            f"{name} has a surprise for you! 🎁",
            "Your daily gift is ready — come collect it!",
            {"trigger": "daily_gift"},
        )
        _mark_sent("daily_gift")
        fired.append("daily_gift")

    # --- Trigger 3: Task completed ---
    try:
        from plugins.companion.queue import get_queue
        completed = get_queue(status="completed")
        if completed and _can_send("task_completed"):
            task = completed[0]
            task_type = task.get("task_type", "task")
            await send_push(
                token,
                "Your task is done! ✅",
                f"{task_type} — check the results.",
                {"trigger": "task_completed", "task_type": task_type},
            )
            _mark_sent("task_completed")
            fired.append("task_completed")
    except Exception:
        pass

    # --- Trigger 4: Level up ---
    level = state.get("level", 1)
    if state.get("_just_leveled_up") and _can_send("level_up"):
        await send_push(
            token,
            f"🎉 {name} reached level {level}!",
            f"Your companion is getting stronger!",
            {"trigger": "level_up", "level": level},
        )
        _mark_sent("level_up")
        fired.append("level_up")

    return fired

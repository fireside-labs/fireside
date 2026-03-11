"""
alerts/handler.py — Proactive alert engine.

Subscribes to event bus, detects patterns, pushes alerts.

Triggers:
  - Crucible failure spike
  - Pipeline stuck >20min
  - Auth failures >3/hour
  - Self-model accuracy drop
  - Agent leveled up
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.alerts")


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Alert rules
# ---------------------------------------------------------------------------

ALERT_RULES = {
    "crucible_spike": {
        "name": "Knowledge check failing",
        "desc": "Your AI forgot how to do something",
        "icon": "⚠️",
        "threshold_events": 3,
        "window_seconds": 3600,
        "trigger_event": "crucible.broken",
    },
    "pipeline_stuck": {
        "name": "Task stuck",
        "desc": "Task hasn't progressed — needs attention",
        "icon": "🔴",
        "threshold_events": 1,
        "window_seconds": 1200,  # 20 minutes
        "trigger_event": "pipeline.stuck",
    },
    "auth_failures": {
        "name": "Suspicious access",
        "desc": "Unknown device tried to connect",
        "icon": "🔒",
        "threshold_events": 3,
        "window_seconds": 3600,
        "trigger_event": "auth.failed",
    },
    "accuracy_drop": {
        "name": "Accuracy dropping",
        "desc": "Your AI is struggling this week",
        "icon": "📉",
        "threshold_events": 5,
        "window_seconds": 86400,
        "trigger_event": "prediction.wrong",
    },
    "agent_levelup": {
        "name": "Level up!",
        "desc": "Agent reached a new level",
        "icon": "🎉",
        "threshold_events": 1,
        "window_seconds": 0,  # Instant
        "trigger_event": "agent.levelup",
    },
}

# Track event counts per rule
_event_log: dict[str, list[float]] = defaultdict(list)
_alerts_history: list = []
_settings: dict = {
    "enabled": True,
    "push_telegram": True,
    "push_desktop": True,
    "push_mobile": True,
    "muted_rules": [],
}


def _alerts_file() -> Path:
    f = Path.home() / ".valhalla" / "alerts.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def _settings_file() -> Path:
    f = Path.home() / ".valhalla" / "alert_settings.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def _load_alerts():
    global _alerts_history
    f = _alerts_file()
    if f.exists():
        try:
            _alerts_history = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass


def _save_alerts():
    _alerts_file().write_text(
        json.dumps(_alerts_history[-200:], indent=2, default=str),
        encoding="utf-8",
    )


def _load_settings():
    global _settings
    f = _settings_file()
    if f.exists():
        try:
            _settings = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass


def _save_settings():
    _settings_file().write_text(
        json.dumps(_settings, indent=2), encoding="utf-8",
    )


def _trigger_alert(rule_id: str, rule: dict, payload: dict) -> None:
    """Fire an alert."""
    alert = {
        "id": f"{rule_id}_{int(time.time())}",
        "rule": rule_id,
        "name": rule["name"],
        "desc": rule["desc"],
        "icon": rule["icon"],
        "payload": {k: v for k, v in payload.items() if isinstance(v, (str, int, float, bool))},
        "timestamp": time.time(),
        "read": False,
    }
    _alerts_history.append(alert)
    _save_alerts()

    _publish("alert.triggered", alert)

    # Push to Telegram
    if _settings.get("push_telegram"):
        try:
            from plugins.telegram.handler import send_message, _CHAT_IDS
            text = f"{rule['icon']} *{rule['name']}*\n{rule['desc']}"
            for cid in _CHAT_IDS:
                send_message(cid, text)
        except Exception:
            pass

    log.info("[alerts] %s: %s", rule["icon"], rule["name"])


# ---------------------------------------------------------------------------
# Event bus hook
# ---------------------------------------------------------------------------

def on_event(event_name: str, payload: dict) -> None:
    """Process events and check alert rules."""
    if not _settings.get("enabled", True):
        return

    now = time.time()

    for rule_id, rule in ALERT_RULES.items():
        if rule_id in _settings.get("muted_rules", []):
            continue

        if event_name != rule["trigger_event"]:
            continue

        # Log event
        _event_log[rule_id].append(now)

        # Clean old events
        window = rule["window_seconds"]
        if window > 0:
            _event_log[rule_id] = [t for t in _event_log[rule_id] if now - t < window]
        else:
            _event_log[rule_id] = [now]

        # Check threshold
        if len(_event_log[rule_id]) >= rule["threshold_events"]:
            _trigger_alert(rule_id, rule, payload)
            _event_log[rule_id] = []  # Reset after alert


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AlertSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    push_telegram: Optional[bool] = None
    push_desktop: Optional[bool] = None
    push_mobile: Optional[bool] = None
    muted_rules: Optional[list] = None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    _load_alerts()
    _load_settings()

    router = APIRouter(tags=["alerts"])

    @router.get("/api/v1/alerts")
    async def api_alerts(limit: int = 50, unread_only: bool = False):
        """Recent alerts."""
        alerts = _alerts_history
        if unread_only:
            alerts = [a for a in alerts if not a.get("read")]
        recent = sorted(alerts, key=lambda a: a.get("timestamp", 0), reverse=True)[:limit]
        return {
            "alerts": recent,
            "count": len(recent),
            "unread": sum(1 for a in _alerts_history if not a.get("read")),
        }

    @router.put("/api/v1/alerts/settings")
    async def api_settings(req: AlertSettingsRequest):
        """Update notification preferences."""
        updates = req.dict(exclude_none=True)
        _settings.update(updates)
        _save_settings()
        return {"ok": True, "settings": _settings}

    app.include_router(router)
    log.info("[alerts] Plugin loaded. Rules: %d, History: %d",
             len(ALERT_RULES), len(_alerts_history))

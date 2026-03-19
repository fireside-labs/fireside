"""
heartbeat/handler.py — Proactive intelligence engine for Fireside.

Background loop that periodically:
  - Generates morning briefings (weather, news, reminders)
  - Suggests tasks when user is idle
  - Monitors scheduled items and nudges
  - Links observations across conversations

Routes:
  GET  /api/v1/heartbeat/status     — Heartbeat status + last pulse
  GET  /api/v1/heartbeat/briefing   — Get current/latest briefing
  PUT  /api/v1/heartbeat/settings   — Configure briefing preferences
  POST /api/v1/heartbeat/pulse      — Manually trigger a pulse
"""
from __future__ import annotations

import json
import logging
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.heartbeat")

_BASE_DIR = Path(".")
_heartbeat_thread: Optional[threading.Thread] = None
_running = False
_last_pulse: dict = {}
_briefing: dict = {}

_settings: dict = {
    "enabled": True,
    "morning_briefing": True,
    "briefing_hour": 8,        # 8 AM
    "idle_suggestions": True,
    "idle_threshold_min": 60,  # suggest after 60 min idle
    "pulse_interval_min": 15,  # check every 15 min
}


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    d = Path.home() / ".valhalla" / "heartbeat"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_settings():
    (_data_dir() / "settings.json").write_text(
        json.dumps(_settings, indent=2), encoding="utf-8",
    )


def _load_settings():
    global _settings
    f = _data_dir() / "settings.json"
    if f.exists():
        try:
            _settings.update(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass


def _save_briefing():
    (_data_dir() / "briefing.json").write_text(
        json.dumps(_briefing, indent=2, default=str), encoding="utf-8",
    )


def _load_briefing():
    global _briefing
    f = _data_dir() / "briefing.json"
    if f.exists():
        try:
            _briefing = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Intelligence functions
# ---------------------------------------------------------------------------

def _get_last_chat_time() -> float:
    """When was the last chat interaction?"""
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:8765/api/v1/companion",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("last_interaction", 0)
    except Exception:
        return 0


def _get_pending_tasks() -> list:
    """Check scheduled tasks that are pending."""
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:8765/api/v1/scheduler",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [t for t in data.get("tasks", [])
                    if t.get("status") == "active"]
    except Exception:
        return []


def _get_active_pipelines() -> list:
    """Check for running/stuck pipelines."""
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:8765/api/v1/pipeline",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [p for p in data.get("pipelines", [])
                    if p.get("status") in ("active", "error", "escalated")]
    except Exception:
        return []


def _get_recent_memories(n: int = 3) -> list:
    """Recall recent memories for context."""
    try:
        import orchestrator as orch
        return orch.recall_memories("recent important observations", top_k=n)
    except Exception:
        return []


def _generate_briefing() -> dict:
    """Generate a morning briefing."""
    global _briefing

    now = datetime.now()
    sections = []

    # 1. Time greeting
    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    sections.append(f"## {greeting}! 🌅\n*{now.strftime('%A, %B %d, %Y')}*")

    # 2. Pending tasks
    tasks = _get_pending_tasks()
    if tasks:
        sections.append(f"### 📋 Scheduled Tasks ({len(tasks)} active)")
        for t in tasks[:5]:
            sched = t.get("schedule", {}).get("description", "")
            sections.append(f"- {t.get('task', '')[:80]} — *{sched}*")

    # 3. Active pipelines
    pipelines = _get_active_pipelines()
    if pipelines:
        sections.append(f"### ⚡ Active Pipelines ({len(pipelines)})")
        for p in pipelines:
            status = p.get("status", "unknown")
            emoji = "🔴" if status in ("error", "escalated") else "🟢"
            sections.append(
                f"- {emoji} {p.get('title', 'Untitled')[:60]} — "
                f"Stage {p.get('current_stage', 0)}/{p.get('total_stages', 0)}"
            )

    # 4. Recent memories / observations
    memories = _get_recent_memories(3)
    if memories:
        sections.append("### 💭 Recent Observations")
        for m in memories:
            content = m.get("content", "")[:100]
            sections.append(f"- {content}")

    # 5. Weather (via web search — non-blocking attempt)
    try:
        from plugins.browse.handler import web_search
        import asyncio
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(web_search("weather today", max_results=1))
        loop.close()
        if result.get("ok") and result.get("results"):
            weather = result["results"][0]
            sections.append(f"### 🌤️ Weather\n{weather.get('snippet', '')[:200]}")
    except Exception:
        pass

    _briefing = {
        "generated_at": int(time.time()),
        "date": now.strftime("%Y-%m-%d"),
        "greeting": greeting,
        "content": "\n\n".join(sections),
        "tasks_count": len(tasks),
        "pipelines_count": len(pipelines),
    }

    _save_briefing()
    _publish("heartbeat.briefing", {"date": _briefing["date"]})
    log.info("[heartbeat] Briefing generated for %s", _briefing["date"])

    return _briefing


def _check_idle() -> Optional[str]:
    """Check if user has been idle and generate a suggestion."""
    last_chat = _get_last_chat_time()
    if not last_chat:
        return None

    idle_min = (time.time() - last_chat) / 60
    threshold = _settings.get("idle_threshold_min", 60)

    if idle_min < threshold:
        return None

    # Generate idle suggestion based on context
    tasks = _get_pending_tasks()
    pipelines = _get_active_pipelines()

    if pipelines:
        stuck = [p for p in pipelines if p.get("status") in ("error", "escalated")]
        if stuck:
            return f"Hey! You have {len(stuck)} pipeline(s) that need attention."

    if tasks:
        return f"You've been away for {int(idle_min)} minutes. You have {len(tasks)} scheduled task(s) running."

    return None


# ---------------------------------------------------------------------------
# Background pulse loop
# ---------------------------------------------------------------------------

def _heartbeat_loop():
    """Background loop — runs periodically to check state and act."""
    global _running, _last_pulse

    log.info("[heartbeat] Background loop started")
    _last_briefing_date = ""

    while _running:
        try:
            now = datetime.now()
            pulse_interval = _settings.get("pulse_interval_min", 15) * 60

            # 1. Morning briefing (once per day at configured hour)
            if (_settings.get("morning_briefing") and
                    now.hour == _settings.get("briefing_hour", 8) and
                    now.strftime("%Y-%m-%d") != _last_briefing_date):
                _generate_briefing()
                _last_briefing_date = now.strftime("%Y-%m-%d")

            # 2. Idle check
            if _settings.get("idle_suggestions"):
                suggestion = _check_idle()
                if suggestion:
                    _publish("heartbeat.idle_suggestion", {
                        "message": suggestion,
                        "timestamp": int(time.time()),
                    })
                    log.info("[heartbeat] Idle suggestion: %s", suggestion[:60])

            # 3. Pipeline health check
            pipelines = _get_active_pipelines()
            stuck = [p for p in pipelines
                     if p.get("status") == "active"
                     and p.get("created_at", 0)
                     and (time.time() - p["created_at"]) > 1200]  # >20 min
            if stuck:
                _publish("alert.pipeline_stuck", {
                    "count": len(stuck),
                    "pipelines": [p.get("id", "") for p in stuck],
                })

            # Record pulse
            _last_pulse = {
                "timestamp": int(time.time()),
                "checks": {
                    "briefing": now.strftime("%Y-%m-%d") == _last_briefing_date,
                    "idle_checked": _settings.get("idle_suggestions", False),
                    "pipelines_active": len(pipelines),
                },
            }

        except Exception as e:
            log.debug("[heartbeat] Pulse error: %s", e)

        time.sleep(pulse_interval if 'pulse_interval' in dir() else 900)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class HeartbeatSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    morning_briefing: Optional[bool] = None
    briefing_hour: Optional[int] = None
    idle_suggestions: Optional[bool] = None
    idle_threshold_min: Optional[int] = None
    pulse_interval_min: Optional[int] = None


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _running

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _load_settings()
    _load_briefing()

    router = APIRouter(tags=["heartbeat"])

    @router.get("/api/v1/heartbeat/status")
    async def api_status():
        """Heartbeat status."""
        return {
            "enabled": _settings.get("enabled", True),
            "last_pulse": _last_pulse,
            "settings": _settings,
            "briefing_available": bool(_briefing),
        }

    @router.get("/api/v1/heartbeat/briefing")
    async def api_briefing():
        """Get the latest briefing. Generates one if none exists today."""
        today = datetime.now().strftime("%Y-%m-%d")
        if _briefing.get("date") != today:
            _generate_briefing()
        return _briefing

    @router.put("/api/v1/heartbeat/settings")
    async def api_settings(req: HeartbeatSettingsRequest):
        """Update heartbeat preferences."""
        updates = req.dict(exclude_none=True)
        _settings.update(updates)
        _save_settings()
        return {"ok": True, "settings": _settings}

    @router.post("/api/v1/heartbeat/pulse")
    async def api_pulse():
        """Manually trigger a heartbeat pulse."""
        briefing = _generate_briefing()
        suggestion = _check_idle()
        return {
            "ok": True,
            "briefing": briefing,
            "idle_suggestion": suggestion,
            "timestamp": int(time.time()),
        }

    app.include_router(router)

    # Start background loop
    if _settings.get("enabled", True):
        _running = True
        _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        _heartbeat_thread.start()

    log.info("[heartbeat] Plugin loaded. Enabled: %s, Briefing hour: %d, Pulse: every %d min",
             _settings.get("enabled"), _settings.get("briefing_hour", 8),
             _settings.get("pulse_interval_min", 15))

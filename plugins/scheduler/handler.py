"""
scheduler/handler.py — Cron-style task scheduler for Fireside.

Enables:
  - "Remind me about X on Friday"
  - "Every morning, check the weather and tell me"
  - "Every hour, check this stock price"
  - Recurring pipeline execution

Routes:
  POST /api/v1/scheduler/create   — Create a scheduled task
  GET  /api/v1/scheduler          — List all scheduled tasks
  GET  /api/v1/scheduler/{id}     — Get task details
  DELETE /api/v1/scheduler/{id}   — Cancel a task
  POST /api/v1/scheduler/run/{id} — Manually trigger a task
"""
from __future__ import annotations

import json
import logging
import re
import time
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

log = logging.getLogger("valhalla.scheduler")

_BASE_DIR = Path(".")
_scheduler_thread: Optional[threading.Thread] = None
_running = False
_tasks: dict[str, dict] = {}


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
    d = Path.home() / ".fireside" / "scheduler"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_tasks():
    path = _data_dir() / "tasks.json"
    path.write_text(
        json.dumps(_tasks, indent=2, default=str),
        encoding="utf-8",
    )


def _load_tasks():
    global _tasks
    path = _data_dir() / "tasks.json"
    if path.exists():
        try:
            _tasks = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            _tasks = {}


# ---------------------------------------------------------------------------
# Natural language → schedule parsing
# ---------------------------------------------------------------------------

def parse_schedule(text: str) -> dict:
    """Parse a natural language schedule description into an interval dict.

    Supports:
      "every 5 minutes", "every hour", "every day at 9am"
      "in 30 minutes", "tomorrow at 3pm"
      "every morning", "every evening"

    Returns: {type: "interval"|"once", seconds: N, description: str}
    """
    text_lower = text.lower().strip()

    # "every X minutes/hours/days"
    m = re.search(r'every\s+(\d+)\s*(minute|min|hour|hr|day|second|sec)s?', text_lower)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        multipliers = {"second": 1, "sec": 1, "minute": 60, "min": 60,
                       "hour": 3600, "hr": 3600, "day": 86400}
        seconds = n * multipliers.get(unit, 60)
        seconds = max(seconds, 60)  # Minimum 60s to prevent CPU spin
        return {"type": "interval", "seconds": seconds,
                "description": f"Every {n} {unit}(s)"}

    # "every morning" / "every evening" / "every night"
    if "every morning" in text_lower:
        return {"type": "daily", "hour": 8, "minute": 0,
                "description": "Every morning at 8:00 AM"}
    if "every evening" in text_lower or "every night" in text_lower:
        return {"type": "daily", "hour": 20, "minute": 0,
                "description": "Every evening at 8:00 PM"}
    if "every day" in text_lower:
        # Try to parse time
        time_match = re.search(r'at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            ampm = time_match.group(3)
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            # Clamp hour to valid range
            hour = hour % 24
            desc_hour = hour % 12 or 12
            desc_ampm = "AM" if hour < 12 else "PM"
            return {"type": "daily", "hour": hour, "minute": minute,
                    "description": f"Every day at {desc_hour}:{minute:02d} {desc_ampm}"}
        return {"type": "daily", "hour": 9, "minute": 0,
                "description": "Every day at 9:00 AM"}

    # "every hour"
    if "every hour" in text_lower:
        return {"type": "interval", "seconds": 3600,
                "description": "Every hour"}

    # "in X minutes/hours"
    m = re.search(r'in\s+(\d+)\s*(minute|min|hour|hr|day|second|sec)s?', text_lower)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        multipliers = {"second": 1, "sec": 1, "minute": 60, "min": 60,
                       "hour": 3600, "hr": 3600, "day": 86400}
        seconds = n * multipliers.get(unit, 60)
        seconds = max(seconds, 30)  # Minimum 30s for one-shot
        return {"type": "once", "seconds": seconds,
                "description": f"In {n} {unit}(s)"}

    # "tomorrow"
    if "tomorrow" in text_lower:
        return {"type": "once", "seconds": 86400,
                "description": "Tomorrow"}

    # Default: one hour from now
    return {"type": "once", "seconds": 3600,
            "description": "In 1 hour (default)"}


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------

def _execute_task(task: dict) -> None:
    """Execute a scheduled task by sending it to the chat/orchestration system."""
    task_text = task.get("task", "")
    task_type = task.get("action", "chat")  # chat, pipeline, browse, terminal

    log.info("[scheduler] Executing: %s (type=%s)", task_text[:60], task_type)

    try:
        import urllib.request
        port = 8765

        if task_type == "pipeline":
            # Create a pipeline
            payload = json.dumps({"task": task_text}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/v1/pipeline/start",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                task["last_result"] = result

        elif task_type == "browse":
            # Fetch a URL
            payload = json.dumps({"url": task_text}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/v1/browse",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                task["last_result"] = {"ok": result.get("ok", False),
                                       "title": result.get("title", ""),
                                       "preview": result.get("text", "")[:200]}

        else:
            # Default: send as chat message
            payload = json.dumps({
                "message": f"[Scheduled task] {task_text}",
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/v1/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                task["last_result"] = {"ok": True,
                                       "preview": str(result)[:300]}

        task["last_run"] = int(time.time())
        task["run_count"] = task.get("run_count", 0) + 1

        _publish("scheduler.task_executed", {
            "task_id": task.get("id", ""),
            "task": task_text[:80],
            "run_count": task["run_count"],
        })

    except Exception as e:
        log.warning("[scheduler] Execution failed: %s — %s", task_text[:50], e)
        task["last_error"] = str(e)
        task["last_run"] = int(time.time())


def _scheduler_loop():
    """Background loop that checks and runs scheduled tasks."""
    global _running
    log.info("[scheduler] Background loop started")

    while _running:
        try:
            now = time.time()
            now_dt = datetime.now()

            for task_id, task in list(_tasks.items()):
                if task.get("status") != "active":
                    continue

                schedule = task.get("schedule", {})
                stype = schedule.get("type", "once")
                last_run = task.get("last_run", 0)

                should_run = False

                if stype == "interval":
                    interval = schedule.get("seconds", 3600)
                    if now - last_run >= interval:
                        should_run = True

                elif stype == "daily":
                    hour = schedule.get("hour", 9)
                    minute = schedule.get("minute", 0)
                    if now_dt.hour == hour and abs(now_dt.minute - minute) <= 1:
                        # Don't run if already ran in the last 30 min
                        if last_run == 0 or (now - last_run) > 1800:
                            should_run = True

                elif stype == "once":
                    fire_at = task.get("fire_at", 0)
                    if fire_at and now >= fire_at and not task.get("fired"):
                        should_run = True
                        task["fired"] = True

                if should_run:
                    _execute_task(task)
                    _save_tasks()

                    # One-time tasks: mark completed
                    if stype == "once":
                        task["status"] = "completed"
                        _save_tasks()

        except Exception as e:
            log.debug("[scheduler] Loop error: %s", e)

        # Check every 30 seconds
        time.sleep(30)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    task: str = Field(max_length=4096, description="What to do")
    schedule: str = Field(max_length=256, description="When to do it, e.g. 'every hour', 'in 30 minutes'")
    action: str = "chat"  # chat, pipeline, browse, terminal


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _running

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _load_tasks()

    router = APIRouter(tags=["scheduler"])

    @router.post("/api/v1/scheduler/create")
    async def api_create_task(req: CreateTaskRequest):
        """Create a scheduled task."""
        schedule = parse_schedule(req.schedule)
        task_id = f"sched_{uuid.uuid4().hex[:8]}"

        task = {
            "id": task_id,
            "task": req.task,
            "action": req.action,
            "schedule": schedule,
            "status": "active",
            "created_at": int(time.time()),
            "last_run": 0,
            "run_count": 0,
        }

        # For "once" tasks, calculate fire time
        if schedule["type"] == "once":
            task["fire_at"] = int(time.time()) + schedule.get("seconds", 3600)

        _tasks[task_id] = task
        _save_tasks()

        _publish("scheduler.created", {"task_id": task_id, "task": req.task[:80]})
        log.info("[scheduler] Created: %s — %s", task_id, schedule["description"])

        return {
            "ok": True,
            "task_id": task_id,
            "schedule": schedule,
            "status": "active",
        }

    @router.get("/api/v1/scheduler")
    async def api_list_tasks():
        """List all scheduled tasks."""
        return {
            "tasks": [
                {
                    "id": tid,
                    "task": t.get("task", "")[:100],
                    "schedule": t.get("schedule", {}),
                    "status": t.get("status", "unknown"),
                    "run_count": t.get("run_count", 0),
                    "last_run": t.get("last_run", 0),
                    "created_at": t.get("created_at", 0),
                }
                for tid, t in _tasks.items()
            ],
            "count": len(_tasks),
            "active": sum(1 for t in _tasks.values() if t.get("status") == "active"),
        }

    @router.get("/api/v1/scheduler/{task_id}")
    async def api_get_task(task_id: str):
        """Get task details."""
        if task_id not in _tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        return _tasks[task_id]

    @router.delete("/api/v1/scheduler/{task_id}")
    async def api_cancel_task(task_id: str):
        """Cancel a scheduled task."""
        if task_id not in _tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        _tasks[task_id]["status"] = "cancelled"
        _tasks[task_id]["cancelled_at"] = int(time.time())
        _save_tasks()
        return {"ok": True, "cancelled": task_id}

    @router.post("/api/v1/scheduler/run/{task_id}")
    async def api_run_task(task_id: str):
        """Manually trigger a scheduled task."""
        if task_id not in _tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        task = _tasks[task_id]
        threading.Thread(target=_execute_task, args=(task,), daemon=True).start()
        return {"ok": True, "triggered": task_id}

    app.include_router(router)

    # Start the background scheduler loop
    _running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()

    log.info("[scheduler] Plugin loaded. %d tasks (%d active). Background loop started.",
             len(_tasks), sum(1 for t in _tasks.values() if t.get("status") == "active"))

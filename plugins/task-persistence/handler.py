"""
task-persistence/handler.py — Crash-resilient task management.

Checkpoint pattern:
  1. Create task → writes state to data/tasks/{task_id}.json
  2. At each step, checkpoint → updates progress
  3. On crash/restart → scan for in_progress tasks → resume from last checkpoint
  4. Notify user via Telegram on resume

This is the biological equivalent of waking from unconsciousness
and remembering what you were doing.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("valhalla.task-persistence")


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

_TASKS_DIR: Path = Path.home() / ".valhalla" / "tasks"


def _ensure_dir():
    _TASKS_DIR.mkdir(parents=True, exist_ok=True)


def _task_file(task_id: str) -> Path:
    return _TASKS_DIR / f"{task_id}.json"


def save_task(task: dict) -> None:
    """Write task state to disk."""
    _ensure_dir()
    _task_file(task["id"]).write_text(
        json.dumps(task, indent=2, default=str), encoding="utf-8",
    )


def load_task(task_id: str) -> dict | None:
    """Load a task from disk."""
    f = _task_file(task_id)
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def list_tasks(status: str = "", limit: int = 50) -> list:
    """List all tasks, optionally filtered by status."""
    _ensure_dir()
    tasks = []
    for f in sorted(_TASKS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
            if status and t.get("status") != status:
                continue
            tasks.append(t)
            if len(tasks) >= limit:
                break
        except Exception:
            pass
    return tasks


def create_task(
    title: str,
    description: str = "",
    agent: str = "unknown",
    total_steps: int = 1,
) -> dict:
    """Create a new task with initial checkpoint."""
    task = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "description": description,
        "agent": agent,
        "status": "in_progress",
        "current_step": 0,
        "total_steps": total_steps,
        "checkpoints": [],
        "created_at": time.time(),
        "updated_at": time.time(),
        "completed_at": None,
        "resumed_count": 0,
    }
    save_task(task)
    _publish("task.created", task)
    return task


def checkpoint(task_id: str, step: int, data: dict | None = None) -> dict:
    """Save a checkpoint for a task."""
    task = load_task(task_id)
    if not task:
        return {"ok": False, "error": f"Task {task_id} not found"}

    task["current_step"] = step
    task["updated_at"] = time.time()
    task["checkpoints"].append({
        "step": step,
        "timestamp": time.time(),
        "data": data or {},
    })
    # Keep only last 20 checkpoints
    task["checkpoints"] = task["checkpoints"][-20:]
    save_task(task)
    _publish("task.checkpoint", {"task_id": task_id, "step": step})
    return {"ok": True, "step": step}


def complete_task(task_id: str, result: str = "") -> dict:
    """Mark a task as completed."""
    task = load_task(task_id)
    if not task:
        return {"ok": False, "error": f"Task {task_id} not found"}

    task["status"] = "completed"
    task["current_step"] = task["total_steps"]
    task["completed_at"] = time.time()
    task["result"] = result
    save_task(task)
    _publish("task.completed", task)
    return {"ok": True, "task": task}


def scan_interrupted() -> list:
    """Find tasks that were interrupted (in_progress). Called on restart."""
    return list_tasks(status="in_progress")


def resume_task(task_id: str) -> dict:
    """Resume a task from last checkpoint."""
    task = load_task(task_id)
    if not task:
        return {"ok": False, "error": f"Task {task_id} not found"}

    if task["status"] != "in_progress":
        return {"ok": False, "error": f"Task {task_id} is {task['status']}"}

    task["resumed_count"] += 1
    task["updated_at"] = time.time()

    # Calculate offline duration
    last_update = task.get("updated_at", task["created_at"])
    offline_mins = round((time.time() - last_update) / 60)

    save_task(task)

    last_checkpoint = task["checkpoints"][-1] if task["checkpoints"] else None
    resume_step = last_checkpoint["step"] if last_checkpoint else 0

    _publish("task.resumed", {
        "task_id": task_id,
        "resume_step": resume_step,
        "total_steps": task["total_steps"],
        "offline_minutes": offline_mins,
    })

    # Notify via Telegram
    try:
        from plugins.telegram.handler import send_message, _CHAT_IDS
        text = (
            f"🔄 *I'm back.* Picking up where I left off.\n"
            f"Task: _{task['title']}_\n"
            f"Step {resume_step}/{task['total_steps']}\n"
            f"Offline for {offline_mins} minutes."
        )
        for cid in _CHAT_IDS:
            send_message(cid, text)
    except Exception:
        pass

    return {
        "ok": True,
        "task_id": task_id,
        "resume_from_step": resume_step,
        "total_steps": task["total_steps"],
        "offline_minutes": offline_mins,
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    agent: str = "unknown"
    total_steps: int = 1


class CheckpointRequest(BaseModel):
    step: int
    data: Optional[dict] = None


# ---------------------------------------------------------------------------
# On startup: scan for interrupted tasks
# ---------------------------------------------------------------------------

def on_startup() -> list:
    """Called on server start. Resumes any interrupted tasks."""
    interrupted = scan_interrupted()
    resumed = []
    for task in interrupted:
        r = resume_task(task["id"])
        if r.get("ok"):
            resumed.append(r)
            log.info("[task-persistence] Resumed: %s (step %d/%d)",
                     task["title"], r["resume_from_step"], r["total_steps"])
    return resumed


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _TASKS_DIR

    tasks_cfg = config.get("tasks", {})
    data_dir = Path(tasks_cfg.get("data_dir", str(Path.home() / ".valhalla" / "tasks")))
    _TASKS_DIR = data_dir
    _ensure_dir()

    router = APIRouter(tags=["task-persistence"])

    @router.post("/api/v1/tasks")
    async def api_create(req: TaskCreateRequest):
        """Create a new persistent task."""
        task = create_task(req.title, req.description, req.agent, req.total_steps)
        return task

    @router.get("/api/v1/tasks")
    async def api_list(status: str = "", limit: int = 50):
        """List tasks."""
        tasks = list_tasks(status, limit)
        return {"tasks": tasks, "count": len(tasks)}

    @router.get("/api/v1/tasks/{task_id}")
    async def api_get(task_id: str):
        """Get task detail."""
        task = load_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @router.put("/api/v1/tasks/{task_id}/checkpoint")
    async def api_checkpoint(task_id: str, req: CheckpointRequest):
        """Save a checkpoint."""
        result = checkpoint(task_id, req.step, req.data)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result

    @router.post("/api/v1/tasks/{task_id}/complete")
    async def api_complete(task_id: str):
        """Mark task as completed."""
        return complete_task(task_id)

    app.include_router(router)

    # Auto-resume interrupted tasks
    resumed = on_startup()
    log.info("[task-persistence] Plugin loaded. Resumed %d interrupted task(s).", len(resumed))

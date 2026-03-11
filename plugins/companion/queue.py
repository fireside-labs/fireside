"""
companion/queue.py — Task queue for phone → home PC routing.

Phone adds tasks → Home PC agents process them → Results synced back.
Tasks processed in order received.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

log = logging.getLogger("valhalla.companion.queue")


def _queue_file() -> Path:
    f = Path.home() / ".valhalla" / "companion_queue.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def _load_queue() -> list:
    f = _queue_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_queue(queue: list) -> None:
    _queue_file().write_text(
        json.dumps(queue, indent=2, default=str), encoding="utf-8",
    )


# Task types the companion can queue
TASK_TYPES = {
    "clean_photos": {
        "label": "Clean Photos",
        "desc": "Find and suggest duplicate/blurry photos to delete",
        "emoji": "📷",
    },
    "organize_apps": {
        "label": "Organize Apps",
        "desc": "Suggest folder groups for phone apps",
        "emoji": "📱",
    },
    "draft_text": {
        "label": "Draft Text",
        "desc": "Write a message for you",
        "emoji": "✏️",
    },
    "set_reminder": {
        "label": "Set Reminder",
        "desc": "Schedule a reminder",
        "emoji": "⏰",
    },
    "quick_math": {
        "label": "Quick Math",
        "desc": "Calculate something",
        "emoji": "🔢",
    },
    "weather": {
        "label": "Check Weather",
        "desc": "Get weather forecast",
        "emoji": "🌤️",
    },
}


def add_task(task_type: str, payload: dict | None = None) -> dict:
    """Add a task to the queue from the phone."""
    if task_type not in TASK_TYPES:
        return {
            "ok": False,
            "error": f"Unknown task type: {task_type}. Options: {list(TASK_TYPES.keys())}",
        }

    task = {
        "id": str(uuid.uuid4())[:8],
        "type": task_type,
        "label": TASK_TYPES[task_type]["label"],
        "emoji": TASK_TYPES[task_type]["emoji"],
        "payload": payload or {},
        "status": "pending",  # pending → sent → completed
        "result": None,
        "queued_at": time.time(),
        "completed_at": None,
    }

    queue = _load_queue()
    queue.append(task)
    _save_queue(queue)

    log.info("[queue] Task queued: %s (%s)", task_type, task["id"])
    return {"ok": True, "task": task}


def get_queue(status: str = "") -> list:
    """Get tasks, optionally filtered by status."""
    queue = _load_queue()
    if status:
        queue = [t for t in queue if t.get("status") == status]
    return queue


def complete_task(task_id: str, result: str) -> dict:
    """Mark a task as completed with result."""
    queue = _load_queue()
    for task in queue:
        if task["id"] == task_id:
            task["status"] = "completed"
            task["result"] = result
            task["completed_at"] = time.time()
            _save_queue(queue)
            log.info("[queue] Task completed: %s", task_id)
            return {"ok": True, "task": task}
    return {"ok": False, "error": f"Task {task_id} not found"}


def mark_sent(task_id: str) -> dict:
    """Mark a task as sent to the home PC for processing."""
    queue = _load_queue()
    for task in queue:
        if task["id"] == task_id:
            task["status"] = "sent"
            _save_queue(queue)
            return {"ok": True}
    return {"ok": False, "error": f"Task {task_id} not found"}


def clear_completed() -> dict:
    """Clear completed tasks from queue."""
    queue = _load_queue()
    remaining = [t for t in queue if t.get("status") != "completed"]
    removed = len(queue) - len(remaining)
    _save_queue(remaining)
    return {"ok": True, "removed": removed}


def get_stats() -> dict:
    """Get queue statistics."""
    queue = _load_queue()
    return {
        "total": len(queue),
        "pending": sum(1 for t in queue if t.get("status") == "pending"),
        "sent": sum(1 for t in queue if t.get("status") == "sent"),
        "completed": sum(1 for t in queue if t.get("status") == "completed"),
    }

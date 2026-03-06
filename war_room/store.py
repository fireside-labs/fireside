"""
store.py — Thread-safe JSON-backed store for the Valhalla War Room.

Messages: append-only log with optional filters.
Tasks: lifecycle-managed board with role-based affinity.
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class WarRoomStore:
    """Thread-safe JSON file store for war room messages and tasks."""

    def __init__(self, data_dir: Path, max_messages: int = 500):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.max_messages = max_messages

        self._msg_file = self.data_dir / "messages.json"
        self._task_file = self.data_dir / "tasks.json"
        self._lock = threading.Lock()
        self._archive_lock = threading.Lock()  # serialises concurrent archive file writes

        self._messages: list[dict] = self._load(self._msg_file, default=[])
        self._tasks: dict[str, dict] = self._load(self._task_file, default={})

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _load(path: Path, default):
        try:
            if path.exists():
                return json.loads(path.read_text())
        except Exception:
            pass
        return default

    def _save_messages(self):
        """Atomic write: write to temp file then rename to avoid corruption."""
        tmp = self._msg_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._messages, indent=2))
        tmp.replace(self._msg_file)

    def _save_tasks(self):
        """Atomic write: write to temp file then rename to avoid corruption."""
        tmp = self._task_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._tasks, indent=2))
        tmp.replace(self._task_file)

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def post_message(
        self,
        from_agent: str,
        to: str = "all",
        msg_type: str = "update",
        subject: str = "",
        body: str = "",
        thread_id: Optional[str] = None,
    ) -> dict:
        """Post a message to the war room. Returns the created message."""
        now = datetime.now(timezone.utc).isoformat()
        msg = {
            "id": uuid.uuid4().hex[:12],
            "from": from_agent,
            "to": to,
            "type": msg_type,
            "subject": subject,
            "body": body,
            "timestamp": now,
            "thread_id": thread_id or uuid.uuid4().hex[:8],
        }
        with self._lock:
            self._messages.append(msg)
            # Prune oldest if over cap
            if len(self._messages) > self.max_messages:
                self._messages = self._messages[-self.max_messages:]
            self._save_messages()
        return msg

    def read_messages(
        self,
        since: Optional[str] = None,
        from_agent: Optional[str] = None,
        to: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> list[dict]:
        """Read messages with optional filters."""
        with self._lock:
            msgs = list(self._messages)

        if since:
            msgs = [m for m in msgs if m["timestamp"] > since]
        if from_agent:
            msgs = [m for m in msgs if m["from"] == from_agent]
        if to:
            msgs = [m for m in msgs if m["to"] in (to, "all")]
        if thread_id:
            msgs = [m for m in msgs if m["thread_id"] == thread_id]
        return msgs

    @staticmethod
    def _is_valid_message(m: dict) -> bool:
        """Reject garbage during gossip merge."""
        required = ("id", "from", "to", "body", "timestamp")
        return all(k in m and isinstance(m[k], str) for k in required)

    def merge_messages(self, remote_messages: list[dict]) -> int:
        """Merge messages from a remote node (gossip sync). Returns count of new messages."""
        # Validate and sanitize before touching the lock
        valid = [m for m in remote_messages if self._is_valid_message(m)]
        with self._lock:
            existing_ids = {m["id"] for m in self._messages}
            new_msgs = [m for m in valid if m["id"] not in existing_ids]
            if not new_msgs:
                return 0
            self._messages.extend(new_msgs)
            # Sort by timestamp for consistent ordering
            self._messages.sort(key=lambda m: m["timestamp"])
            if len(self._messages) > self.max_messages:
                self._messages = self._messages[-self.max_messages:]
            self._save_messages()
            return len(new_msgs)

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    VALID_STATUSES = {"open", "claimed", "in_progress", "done", "blocked"}
    TERMINAL_STATUSES = {"done"}
    ARCHIVE_AFTER_DAYS = 7

    def post_task(
        self,
        title: str,
        description: str,
        posted_by: str,
        assigned_to: Optional[str] = None,
        affinity: Optional[list[str]] = None,
    ) -> dict:
        """Post a new task to the board. Returns the created task."""
        now = datetime.now(timezone.utc).isoformat()
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "posted_by": posted_by,
            "assigned_to": assigned_to,
            "affinity": affinity or [],
            "status": "open",
            "result": None,
            "created": now,
            "updated": now,
        }
        with self._lock:
            self._tasks[task_id] = task
            self._save_tasks()
        return task

    def claim_task(self, task_id: str, agent_id: str) -> dict:
        """Claim a task. Enforces affinity and status transitions."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise KeyError(f"Task {task_id} not found")
            if task["status"] in self.TERMINAL_STATUSES:
                raise ValueError(f"Task {task_id} is already {task['status']}")
            if task["status"] == "claimed" and task["assigned_to"] != agent_id:
                raise ValueError(f"Task {task_id} already claimed by {task['assigned_to']}")
            # Check affinity
            affinity = task.get("affinity", [])
            if affinity and "any" not in affinity and agent_id not in affinity:
                raise PermissionError(
                    f"Agent '{agent_id}' cannot claim this task. "
                    f"Affinity restricted to: {affinity}"
                )
            task["status"] = "claimed"
            task["assigned_to"] = agent_id
            task["updated"] = datetime.now(timezone.utc).isoformat()
            self._save_tasks()
            return task

    def update_task_status(self, task_id: str, status: str, agent_id: str) -> dict:
        """Update a task's status (e.g., in_progress, blocked)."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise KeyError(f"Task {task_id} not found")
            if task["status"] in self.TERMINAL_STATUSES:
                raise ValueError(f"Task {task_id} is already {task['status']}")
            task["status"] = status
            task["updated"] = datetime.now(timezone.utc).isoformat()
            self._save_tasks()
            return task

    def complete_task(self, task_id: str, agent_id: str, result: str) -> dict:
        """Mark a task as done with results."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise KeyError(f"Task {task_id} not found")
            if task["status"] == "done":
                raise ValueError(f"Task {task_id} is already done")
            task["status"] = "done"
            task["result"] = result
            task["assigned_to"] = agent_id
            task["updated"] = datetime.now(timezone.utc).isoformat()
            self._save_tasks()
            return task

    def get_tasks(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        since: Optional[str] = None,
    ) -> list[dict]:
        """Get all tasks, optionally filtered by status, assignee, or update time."""
        with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        if assigned_to:
            tasks = [t for t in tasks if t["assigned_to"] == assigned_to]
        if since:
            tasks = [t for t in tasks if t.get("updated", "") > since]
        return tasks

    def merge_tasks(self, remote_tasks: dict[str, dict]) -> int:
        """Merge tasks from a remote node. Latest 'updated' wins. Returns count of updates."""
        updated_count = 0
        with self._lock:
            for tid, remote_task in remote_tasks.items():
                local = self._tasks.get(tid)
                if not local or remote_task.get("updated", "") > local.get("updated", ""):
                    self._tasks[tid] = remote_task
                    updated_count += 1
            if updated_count:
                self._save_tasks()
        # Housekeeping: archive stale done tasks
        self.archive_stale_tasks()
        return updated_count

    def archive_stale_tasks(self) -> int:
        """Move done tasks older than ARCHIVE_AFTER_DAYS to an archive file."""
        now = datetime.now(timezone.utc)
        archive_file = self.data_dir / "tasks_archive.json"
        archived_count = 0

        with self._lock:
            to_archive = []
            for tid, task in self._tasks.items():
                if task["status"] != "done":
                    continue
                try:
                    updated = datetime.fromisoformat(task["updated"])
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    age_days = (now - updated).total_seconds() / 86400
                    if age_days > self.ARCHIVE_AFTER_DAYS:
                        to_archive.append(tid)
                except (KeyError, ValueError):
                    continue

            if not to_archive:
                return 0

            # Load existing archive, append, save
            archive: dict = self._load(archive_file, default={})
            for tid in to_archive:
                archive[tid] = self._tasks.pop(tid)
                archived_count += 1

            self._save_tasks()

        # Write archive outside the main lock but inside the archive lock
        # so concurrent callers don't clobber each other's writes
        if archived_count:
            with self._archive_lock:
                # Re-load to pick up anything another thread may have written
                archive_on_disk: dict = self._load(archive_file, default={})
                archive_on_disk.update(archive)
                tmp = archive_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(archive_on_disk, indent=2))
                tmp.replace(archive_file)

        return archived_count

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Generate a human-readable summary of war room activity."""
        with self._lock:
            total_messages = len(self._messages)
            recent = list(self._messages[-10:]) if self._messages else []
            tasks = list(self._tasks.values())
            # Count talkers inside the lock so we read a consistent snapshot
            talkers: dict[str, int] = {}
            for m in self._messages[-50:]:
                talkers[m["from"]] = talkers.get(m["from"], 0) + 1

        active_tasks = [t for t in tasks if t["status"] not in ("done",)]
        blocked_tasks = [t for t in tasks if t["status"] == "blocked"]
        done_tasks = [t for t in tasks if t["status"] == "done"]

        return {
            "total_messages": total_messages,
            "recent_messages": recent,
            "active_tasks": len(active_tasks),
            "blocked_tasks": len(blocked_tasks),
            "done_tasks": len(done_tasks),
            "task_list": tasks,
            "active_agents": talkers,
        }

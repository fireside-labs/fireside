"""
store.py ΓÇö Thread-safe JSON-backed store for the Valhalla War Room.

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
        self._tombstone_file = self.data_dir / "tombstones.json"
        self._lock = threading.Lock()
        self._archive_lock = threading.Lock()  # serialises concurrent archive file writes

        self._messages: list[dict] = self._load(self._msg_file, default=[])
        self._tasks: dict[str, dict] = self._load(self._task_file, default={})
        # tombstones: {id: iso_timestamp} ΓÇö propagated to peers so deletes replicate
        self._tombstones: dict[str, str] = self._load(self._tombstone_file, default={})
        # Progress: {task_id: {agent, note, ts, percent}} — runtime only, not persisted
        self._progress: dict[str, dict] = {}

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

    def _save_tombstones(self):
        tmp = self._tombstone_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._tombstones, indent=2))
        tmp.replace(self._tombstone_file)

    def get_tombstones(self, since: Optional[str] = None) -> dict:
        """Return tombstones (deleted IDs) optionally filtered by timestamp."""
        with self._lock:
            if not since:
                return dict(self._tombstones)
            return {k: v for k, v in self._tombstones.items() if v >= since}

    def apply_tombstones(self, tombstones: dict):
        """Apply tombstones received from a peer ΓÇö delete matching local tasks/messages."""
        with self._lock:
            changed = False
            for obj_id, ts in tombstones.items():
                if obj_id in self._tombstones:
                    continue  # already know about this deletion
                self._tombstones[obj_id] = ts
                # Remove from tasks or messages
                if obj_id in self._tasks:
                    del self._tasks[obj_id]
                    changed = True
                else:
                    self._messages = [m for m in self._messages if m.get("id") != obj_id]
            if changed:
                self._save_tasks()
                self._save_messages()
            if tombstones:
                self._save_tombstones()

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
            new_msgs = [m for m in valid if m["id"] not in existing_ids
                        and m["id"] not in self._tombstones]
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
        decompose: bool = False,
        parent_id: Optional[str] = None,
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
            "decompose": decompose,
            "parent_id": parent_id,
            "subtask_ids": [],
            "created": now,
            "updated": now,
        }
        with self._lock:
            self._tasks[task_id] = task
            # If this is a subtask, register it on the parent
            if parent_id and parent_id in self._tasks:
                self._tasks[parent_id].setdefault("subtask_ids", []).append(task_id)
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
            # Octopus: if subtask, check if all siblings done ΓåÆ auto-complete parent
            parent_id = task.get("parent_id")
            if parent_id and parent_id in self._tasks:
                parent = self._tasks[parent_id]
                sibling_ids = parent.get("subtask_ids", [])
                if all(self._tasks.get(s, {}).get("status") == "done" for s in sibling_ids):
                    sub_results = []
                    for sid in sibling_ids:
                        sub = self._tasks.get(sid, {})
                        sub_results.append(f"- {sub.get('title','?')}: {sub.get('result','done')}")
                    parent["status"] = "done"
                    parent["result"] = "Subtasks completed:\n" + "\n".join(sub_results)
                    parent["updated"] = datetime.now(timezone.utc).isoformat()
            self._save_tasks()
            return task

    def delete_task(self, task_id: str) -> dict:
        """Permanently remove a task. Records tombstone for gossip propagation."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            task = self._tasks.pop(task_id, None)
            if task is None:
                raise KeyError(f"Task {task_id} not found")
            parent_id = task.get("parent_id")
            if parent_id and parent_id in self._tasks:
                subs = self._tasks[parent_id].setdefault("subtask_ids", [])
                if task_id in subs:
                    subs.remove(task_id)
            self._tombstones[task_id] = now
            self._save_tasks()
            self._save_tombstones()
            return task

    def delete_message(self, msg_id: str) -> dict:
        """Permanently remove a message. Records tombstone for gossip propagation."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            # messages is a list ΓÇö find and remove by id
            msg = next((m for m in self._messages if m.get("id") == msg_id), None)
            if msg is None:
                raise KeyError(f"Message {msg_id} not found")
            self._messages = [m for m in self._messages if m.get("id") != msg_id]
            self._tombstones[msg_id] = now
            self._save_messages()
            self._save_tombstones()
            return msg

    def clear_messages(self) -> int:
        """Delete all messages. Records tombstones for gossip propagation."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            count = len(self._messages)
            for m in self._messages:
                self._tombstones[m.get("id", "")] = now
            self._messages.clear()
            self._save_messages()
            self._save_tombstones()
            return count

    # ------------------------------------------------------------------
    # Task Progress
    # ------------------------------------------------------------------

    def update_progress(self, task_id: str, agent: str, note: str,
                        percent: int = -1) -> dict:
        """Record a progress ping for a task. Runtime only — not persisted."""
        from datetime import datetime, timezone
        entry = {
            "task_id": task_id,
            "agent": agent,
            "note": note[:200],
            "percent": max(-1, min(100, percent)),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._progress[task_id] = entry
            # Cap at 200 entries
            if len(self._progress) > 200:
                oldest = sorted(self._progress, key=lambda k: self._progress[k]["ts"])
                for k in oldest[:50]:
                    del self._progress[k]
        return entry

    def get_progress(self, task_id: str = ""):
        """Get progress for one task or all tasks."""
        with self._lock:
            if task_id:
                return self._progress.get(task_id, {})
            return list(self._progress.values())

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

    def delete_task(self, task_id: str) -> dict:
        """Delete a task by ID. Returns the deleted task."""
        with self._lock:
            task = self._tasks.pop(task_id, None)
            if not task:
                raise KeyError(f"Task {task_id} not found")
            self._save_tasks()
            return task

    def delete_message(self, msg_id: str) -> dict:
        """Delete a message by ID. Returns the deleted message."""
        with self._lock:
            for i, m in enumerate(self._messages):
                if m.get("id") == msg_id:
                    msg = self._messages.pop(i)
                    self._save_messages()
                    return msg
            raise KeyError(f"Message {msg_id} not found")

    def clear_messages(self) -> int:
        """Clear all messages. Returns count deleted."""
        with self._lock:
            count = len(self._messages)
            self._messages = []
            self._save_messages()
            return count

    def merge_tasks(self, remote_tasks: dict) -> int:
        """Merge tasks from a remote node. Latest 'updated' wins. Returns count of updates."""
        updated_count = 0
        newly_done = []
        with self._lock:
            for tid, remote_task in remote_tasks.items():
                local = self._tasks.get(tid)
                if not local or remote_task.get("updated", "") > local.get("updated", ""):
                    # Detect transition to "done"
                    old_status = local.get("status", "") if local else ""
                    new_status = remote_task.get("status", "")
                    if new_status == "done" and old_status != "done":
                        newly_done.append(remote_task)
                    self._tasks[tid] = remote_task
                    updated_count += 1
            if updated_count:
                self._save_tasks()
        # Housekeeping: archive stale done tasks
        self.archive_stale_tasks()
        # Telegram notification for newly completed tasks (Odin only)
        if newly_done:
            self._notify_task_completions(newly_done)
        return updated_count

    def _notify_task_completions(self, tasks: list) -> None:
        """Send Telegram notifications for completed tasks (orchestrator only)."""
        try:
            import json as _json, urllib.request as _urlreq
            from pathlib import Path as _Path
            _cfg_path = _Path(__file__).parent.parent / "config.json"
            if not _cfg_path.exists():
                return
            _cfg = _json.loads(_cfg_path.read_text())
            if _cfg.get("node_id", "") != "odin":
                return
            _token = _cfg.get("telegram_bot_token", "")
            _chat = _cfg.get("telegram_chat_id", "")
            if not _token or not _chat:
                return
            for t in tasks:
                agent = t.get("assigned_to", t.get("claimed_by", "unknown"))
                title = t.get("title", t.get("id", "?"))
                # Extract readable text from dispatch result JSON
                # Format: {runId, status, result: {payloads: [{text: "..."}]}}
                raw_result = (t.get("result", "") or "")
                try:
                    _rj = _json.loads(raw_result)
                    # Try double-nested (dispatch wrapper -> openclaw result)
                    _inner = _rj.get("result", _rj)
                    if isinstance(_inner, dict):
                        _payloads = _inner.get("payloads", [])
                    else:
                        _payloads = _rj.get("payloads", [])
                    result = _payloads[0].get("text", "")[:600] if _payloads else (_rj.get("summary", raw_result))[:600]
                except Exception:
                    result = raw_result[:600]
                text = f"\u2705 {agent.upper()} completed task:\n\U0001f4cb {title}\n\n{result}"
                body = _json.dumps({
                    "chat_id": _chat, "text": text
                }).encode()
                req = _urlreq.Request(
                    f"https://api.telegram.org/bot{_token}/sendMessage",
                    data=body,
                    headers={"Content-Type": "application/json"}, method="POST"
                )
                _urlreq.urlopen(req, timeout=5)
        except Exception as e:
            import logging
            logging.getLogger("war-room.store").warning("[store] Telegram notify failed: %s", e)

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
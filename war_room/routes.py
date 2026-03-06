"""
routes.py — HTTP request handlers for War Room endpoints.

These functions are called by BifrostHandler in bifrost.py.
They take the parsed body (dict) and return (status_code, response_dict).
"""

import logging
from urllib.parse import parse_qs, urlparse

from .store import WarRoomStore
from .ask import AskHandler

log = logging.getLogger("war-room.routes")


class WarRoomRoutes:
    """HTTP route handlers for the Valhalla War Room."""

    def __init__(self, store: WarRoomStore, ask_handler: AskHandler):
        self.store = store
        self.ask = ask_handler

    # ------------------------------------------------------------------
    # GET handlers — return (status_code, response_dict)
    # ------------------------------------------------------------------

    def handle_read(self, path: str) -> tuple[int, object]:
        """GET /war-room/read?since=...&from_agent=...&to=...&thread_id=..."""
        parsed = urlparse(path)
        params = parse_qs(parsed.query)
        messages = self.store.read_messages(
            since=params.get("since", [None])[0],
            from_agent=params.get("from_agent", [None])[0],
            to=params.get("to", [None])[0],
            thread_id=params.get("thread_id", [None])[0],
        )
        return 200, messages

    def handle_get_tasks(self, path: str) -> tuple[int, object]:
        """GET /war-room/tasks?status=...&assigned_to=..."""
        parsed = urlparse(path)
        params = parse_qs(parsed.query)

        # For gossip sync: return raw task dict (keyed by id) when ?raw=true
        raw = params.get("raw", ["false"])[0].lower() == "true"

        tasks = self.store.get_tasks(
            status=params.get("status", [None])[0],
            assigned_to=params.get("assigned_to", [None])[0],
        )

        if raw:
            return 200, {t["id"]: t for t in tasks}
        return 200, tasks

    def handle_summary(self) -> tuple[int, dict]:
        """GET /war-room/summary"""
        return 200, self.store.summary()

    def handle_ask_info(self) -> tuple[int, dict]:
        """GET /ask/info — returns this node's model capabilities."""
        return 200, self.ask.info()

    # ------------------------------------------------------------------
    # POST handlers — take body dict, return (status_code, response_dict)
    # ------------------------------------------------------------------

    def handle_post_message(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/post"""
        required = ["from", "body"]
        missing = [f for f in required if not body.get(f)]
        if missing:
            return 400, {"error": f"Missing required fields: {missing}"}

        msg = self.store.post_message(
            from_agent=body["from"],
            to=body.get("to", "all"),
            msg_type=body.get("type", "update"),
            subject=body.get("subject", ""),
            body=body["body"],
            thread_id=body.get("thread_id"),
        )
        log.info("Message posted: %s -> %s [%s] %s",
                 msg["from"], msg["to"], msg["type"], msg["subject"])
        return 200, msg

    def handle_post_task(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/task"""
        required = ["title", "posted_by"]
        missing = [f for f in required if not body.get(f)]
        if missing:
            return 400, {"error": f"Missing required fields: {missing}"}

        task = self.store.post_task(
            title=body["title"],
            description=body.get("description", ""),
            posted_by=body["posted_by"],
            assigned_to=body.get("assigned_to"),
            affinity=body.get("affinity"),
        )
        log.info("Task posted: %s by %s (affinity: %s)",
                 task["title"], task["posted_by"], task.get("affinity"))
        return 200, task

    def handle_claim_task(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/claim"""
        task_id = body.get("task_id", "")
        agent_id = body.get("agent_id", "")
        if not task_id or not agent_id:
            return 400, {"error": "task_id and agent_id required"}

        try:
            task = self.store.claim_task(task_id, agent_id)
            log.info("Task %s claimed by %s", task_id, agent_id)
            return 200, task
        except KeyError as e:
            return 404, {"error": str(e)}
        except PermissionError as e:
            return 403, {"error": str(e)}
        except ValueError as e:
            return 409, {"error": str(e)}

    def handle_complete_task(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/complete"""
        task_id = body.get("task_id", "")
        agent_id = body.get("agent_id", "")
        result = body.get("result", "")
        if not task_id or not agent_id:
            return 400, {"error": "task_id and agent_id required"}

        try:
            task = self.store.complete_task(task_id, agent_id, result)
            log.info("Task %s completed by %s", task_id, agent_id)
            return 200, task
        except (KeyError, ValueError) as e:
            return 400, {"error": str(e)}

    def handle_update_status(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/status — update task status (in_progress, blocked, etc.)"""
        task_id = body.get("task_id", "")
        agent_id = body.get("agent_id", "")
        status = body.get("status", "")
        if not task_id or not agent_id or not status:
            return 400, {"error": "task_id, agent_id, and status required"}

        try:
            task = self.store.update_task_status(task_id, status, agent_id)
            log.info("Task %s status -> %s by %s", task_id, status, agent_id)
            return 200, task
        except (KeyError, ValueError) as e:
            return 400, {"error": str(e)}

    def handle_ask(self, body: dict) -> tuple[int, dict]:
        """POST /ask — direct inference via local/cloud model"""
        result = self.ask.handle(body)
        if "error" in result:
            return 500, result
        return 200, result

"""
routes.py ΓÇö HTTP request handlers for War Room endpoints.

These functions are called by BifrostHandler in bifrost.py.
They take the parsed body (dict) and return (status_code, response_dict).
"""

import logging
from urllib.parse import parse_qs, urlparse

from .store import WarRoomStore
from .ask import AskHandler

from .node_state import write_node_status


log = logging.getLogger("war-room.routes")


class WarRoomRoutes:
    """HTTP route handlers for the Valhalla War Room."""

    def __init__(self, store: WarRoomStore, ask_handler: AskHandler):
        self.store = store
        self.ask = ask_handler

    # ------------------------------------------------------------------
    # GET handlers ΓÇö return (status_code, response_dict)
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
        """GET /ask/info ΓÇö returns this node's model capabilities."""
        return 200, self.ask.info()

    def handle_tombstones(self, path: str) -> tuple[int, dict]:
        """GET /war-room/tombstones?since=<iso> ΓÇö returns deleted IDs since timestamp."""
        from urllib.parse import urlparse, parse_qs
        params = parse_qs(urlparse(path).query)
        since = params.get("since", [None])[0]
        return 200, self.store.get_tombstones(since=since)

    # ------------------------------------------------------------------
    # POST handlers ΓÇö take body dict, return (status_code, response_dict)
    # ------------------------------------------------------------------

    def handle_post_message(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/post"""
        required = ["from", "body"]
        missing = [f for f in required if not body.get(f)]
        if missing:
            return 400, {"error": f"Missing required fields: {missing}"}

        # --- Semantic routing via Thor's /route-message ---
        # If sender didn't specify a `to` target, ask Thor's router
        # which agents should receive this message based on semantic match.
        to_field = body.get("to", "")
        if not to_field or to_field == "all":
            to_field = self._semantic_route(body)

        msg = self.store.post_message(
            from_agent=body["from"],
            to=to_field,
            msg_type=body.get("type", "update"),
            subject=body.get("subject", ""),
            body=body["body"],
            thread_id=body.get("thread_id"),
        )
        log.info("Message posted: %s -> %s [%s] %s",
                 msg["from"], msg["to"], msg["type"], msg["subject"])
        return 200, msg

    def _semantic_route(self, body: dict) -> str:
        """Ask Thor's semantic router for the best target agents.
        Returns comma-separated agent names, or 'all' on failure."""
        import json
        import urllib.request
        THOR_ROUTE_URL = "http://100.117.255.38:8765/route-message"
        try:
            payload = json.dumps({
                "from": body.get("from", "unknown"),
                "body": body.get("body", ""),
                "subject": body.get("subject", ""),
            }).encode()
            req = urllib.request.Request(
                THOR_ROUTE_URL, data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=3) as r:
                result = json.loads(r.read())
                targets = result.get("targets", [])
                if targets:
                    routed = ",".join(targets)
                    log.info("[semantic-route] %s -> %s", body.get("from"), routed)
                    return routed
        except Exception as e:
            log.debug("[semantic-route] Thor unreachable, broadcasting: %s", e)
        return "all"


    def handle_post_task(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/task"""
        required = ["title", "posted_by"]
        missing = [f for f in required if not body.get(f)]
        if missing:
            return 400, {"error": f"Missing required fields: {missing}"}

        decompose = body.get("decompose", False)
        task = self.store.post_task(
            title=body["title"],
            description=body.get("description", ""),
            posted_by=body["posted_by"],
            assigned_to=body.get("assigned_to"),
            affinity=body.get("affinity"),
            decompose=decompose,
            parent_id=body.get("parent_id"),
        )
        log.info("Task posted: %s by %s (decompose: %s)",
                 task["title"], task["posted_by"], decompose)

        # Octopus: if decompose=true, auto-generate subtasks in background
        if decompose and not body.get("parent_id"):
            import threading
            threading.Thread(
                target=self._auto_decompose,
                args=(task,),
                daemon=True,
                name=f"decompose-{task['id']}"
            ).start()

        return 200, task

    def _auto_decompose(self, parent_task: dict):
        """Break a task into 3-5 subtasks using /ask, then post them as children."""
        import json
        import urllib.request
        prompt = (
            f"Break this task into 3-5 concrete subtasks. "
            f"Return ONLY a JSON array of objects with 'title' and 'description' fields.\n\n"
            f"Task: {parent_task['title']}\n"
            f"Description: {parent_task.get('description', 'No description')}\n\n"
            f"Example: [{{'title':'Step 1','description':'Do X'}},{{'title':'Step 2','description':'Do Y'}}]"
        )
        try:
            ask_body = json.dumps({
                "from": parent_task["posted_by"],
                "prompt": prompt,
                "system": "You are a task planner. Return only valid JSON. No markdown, no explanation.",
                "model": "local",
                "max_tokens": 1000,
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8765/ask",
                data=ask_body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                result = json.loads(r.read())
                response_text = result.get("response", "[]")
                # Extract JSON array from response
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                if start >= 0 and end > start:
                    subtasks = json.loads(response_text[start:end])
                else:
                    subtasks = []

            for sub in subtasks[:5]:
                self.store.post_task(
                    title=sub.get("title", "Subtask"),
                    description=sub.get("description", ""),
                    posted_by=parent_task["posted_by"],
                    assigned_to=parent_task.get("assigned_to"),
                    affinity=parent_task.get("affinity", []),
                    parent_id=parent_task["id"],
                )
            log.info("[octopus] Decomposed '%s' into %d subtasks",
                     parent_task["title"], len(subtasks[:5]))
        except Exception as e:
            log.error("[octopus] Failed to decompose task '%s': %s",
                      parent_task["title"], e)


    def handle_claim_task(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/claim"""
        task_id = body.get("task_id", "")
        agent_id = body.get("agent_id", "")
        if not task_id or not agent_id:
            return 400, {"error": "task_id and agent_id required"}

        try:
            task = self.store.claim_task(task_id, agent_id)
            log.info("Task %s claimed by %s", task_id, agent_id)
            try:
                write_node_status("working", last_task=task.get("title", task_id), detail=f"Claimed task: {task.get('title', '')}")
            except Exception as _e:
                log.debug("node_status update failed: %s", _e)
            return 200, task
        except KeyError as e:
            return 404, {"error": str(e)}
        except PermissionError as e:
            return 403, {"error": str(e)}
        except ValueError as e:
            return 409, {"error": str(e)}

    def handle_complete_task(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/complete

        Required: task_id, agent_id
        Optional: result, task_type, approach
          task_type  - category of skill used (e.g. "debugging", "crispr_prompt")
          approach   - 1-3 sentence methodology summary
          These two fields are passed through in the response so that
          Freya's bifrost_local.py can intercept them for procedural memory.
        """
        task_id = body.get("task_id", "")
        agent_id = body.get("agent_id", "")
        result = body.get("result", "")
        if not task_id or not agent_id:
            return 400, {"error": "task_id and agent_id required"}

        try:
            task = self.store.complete_task(task_id, agent_id, result)
            log.info("Task %s completed by %s", task_id, agent_id)
            # Attach procedural fields so bifrost_local intercepts can learn
            if body.get("task_type"):
                task["task_type"] = body["task_type"]
            if body.get("approach"):
                task["approach"] = body["approach"]
            # --- Auto-procedural-record (Odin task, 2026-03-07) ---
            # Fire-and-forget: record what was done and how into procedural memory.
            # Uses task_type + approach if provided; falls back to task title as type.
            try:
                from war_room import procedures as _proc
                _proc.auto_record(
                    task_type  = body.get("task_type") or task.get("title", "general"),
                    approach   = body.get("approach") or result or task.get("description", ""),
                    outcome    = "success",
                    confidence = 0.75,
                    tags       = ["auto-recorded", "task-complete", agent_id],
                )
            except Exception as _pe:
                log.debug("[routes] auto_record skipped: %s", _pe)
            # --- end auto-record ---
            try:
                write_node_status("idle", last_task=task.get("title", task_id), detail=f"Completed: {result[:200] if result else ''}")
            except Exception as _e:
                log.debug("node_status update failed: %s", _e)
            # --- Telegram notification (only from orchestrator) ---
            try:
                import json as _json, urllib.request as _urlreq
                from pathlib import Path as _Path
                _cfg_path = _Path(__file__).parent.parent / "config.json"
                if _cfg_path.exists():
                    _cfg = _json.loads(_cfg_path.read_text())
                    _tg_token = _cfg.get("telegram_bot_token", "")
                    _tg_chat  = _cfg.get("telegram_chat_id", "")
                    _node     = _cfg.get("node_id", "")
                    if _tg_token and _tg_chat and _node == "odin":
                        _preview = (result or "")[:300]
                        _tg_text = (
                            f"\u2705 {agent_id.upper()} completed task:\n"
                            f"\U0001f4cb {task.get('title', task_id)}\n\n"
                            f"{_preview}"
                        )
                        _tg_body = _json.dumps({
                            "chat_id": _tg_chat, "text": _tg_text
                        }).encode()
                        _tg_req = _urlreq.Request(
                            f"https://api.telegram.org/bot{_tg_token}/sendMessage",
                            data=_tg_body,
                            headers={"Content-Type": "application/json"}, method="POST"
                        )
                        _urlreq.urlopen(_tg_req, timeout=5)
            except Exception as _te:
                log.warning("[routes] Telegram notify failed: %s", _te)
            # --- end Telegram ---
            return 200, task
        except (KeyError, ValueError) as e:
            return 400, {"error": str(e)}


    def handle_update_status(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/status ΓÇö update task status (in_progress, blocked, etc.)"""
        task_id = body.get("task_id", "")
        agent_id = body.get("agent_id", "")
        status = body.get("status", "")
        if not task_id or not agent_id or not status:
            return 400, {"error": "task_id, agent_id, and status required"}

        try:
            task = self.store.update_task_status(task_id, status, agent_id)
            log.info("Task %s status -> %s by %s", task_id, status, agent_id)
            try:
                write_node_status(status, last_task=task.get("title", task_id))
            except Exception as _e:
                log.debug("node_status update failed: %s", _e)
            return 200, task
        except (KeyError, ValueError) as e:
            return 400, {"error": str(e)}

    def handle_ask(self, body: dict) -> tuple[int, dict]:
        """POST /ask ΓÇö direct inference via local/cloud model"""
        result = self.ask.handle(body)
        if "error" in result:
            return 500, result
        return 200, result

    def handle_delete_task(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/delete-task"""
        task_id = body.get("task_id", "")
        if not task_id:
            return 400, {"error": "task_id required"}
        try:
            task = self.store.delete_task(task_id)
            log.info("Task deleted: %s (%s)", task_id, task.get("title", "?"))
            return 200, {"deleted": task}
        except KeyError as e:
            return 404, {"error": str(e)}

    def handle_delete_message(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/delete-message"""
        msg_id = body.get("msg_id", "")
        if not msg_id:
            return 400, {"error": "msg_id required"}
        try:
            msg = self.store.delete_message(msg_id)
            log.info("Message deleted: %s", msg_id)
            return 200, {"deleted": msg}
        except KeyError as e:
            return 404, {"error": str(e)}

    def handle_clear_messages(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/clear-messages"""
        count = self.store.clear_messages()
        log.info("Cleared %d messages", count)
        return 200, {"cleared": count}

    def handle_summon(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/summon ΓÇö notify all agents to check the board."""
        import json
        import urllib.request
        message = body.get("message", "Check the War Room board ΓÇö new tasks posted.")
        nodes = {
            "thor": "100.117.255.38",
            "freya": "100.102.105.3",
            "heimdall": "100.108.153.23",
        }
        results = {}
        for name, ip in nodes.items():
            try:
                payload = json.dumps({
                    "from": "odin",
                    "message": f"[SUMMON] {message}",
                    "urgency": "high",
                }).encode()
                req = urllib.request.Request(
                    f"http://{ip}:8765/notify",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    results[name] = "notified"
            except Exception as e:
                results[name] = f"unreachable: {e}"
        log.info("[summon] Results: %s", results)
        return 200, {"summoned": results, "message": message}

    def handle_progress(self, body: dict) -> tuple[int, dict]:
        """POST /war-room/progress — agent reports progress on a task."""
        task_id = body.get("task_id", "")
        agent = body.get("agent", body.get("agent_id", "unknown"))
        note = body.get("note", body.get("status", ""))
        percent = body.get("percent", -1)
        if not task_id:
            return 400, {"error": "task_id required"}
        entry = self.store.update_progress(task_id, agent, note, percent)
        log.info("[progress] %s → %s: %s", agent, task_id, note[:60])
        return 200, {"ok": True, "progress": entry}

    # POST /dispatch — run a full OpenClaw agent session on this node.
    #
    #     This is the bridge endpoint. When Odin's dispatcher sends a task
    #     here, the node runs `openclaw agent` with full tool access using
    #     its own local GPU and filesystem.
    #
    #     Body: {"task_id": "...", "description": "...", "timeout": 300}
    #     Returns: {"status": "ok", "result": "<agent output>"}
    #
    def handle_dispatch(self, body: dict) -> tuple[int, dict]:
        """POST /dispatch — execute a full OpenClaw agent turn locally."""
        import subprocess
        import shutil

        description = body.get("description", "")
        task_id = body.get("task_id", "")
        timeout = int(body.get("timeout", 300))

        if not description:
            return 400, {"error": "description required"}

        # Check that openclaw CLI is available
        openclaw_bin = shutil.which("openclaw")
        if not openclaw_bin:
            log.error("[dispatch] openclaw binary not found in PATH")
            return 503, {"error": "openclaw not installed on this node"}

        log.info("[dispatch] Running agent turn for task %s (timeout=%ds)",
                 task_id[:14] if task_id else "adhoc", timeout)

<<<<<<< Updated upstream
        # Pre-seed SOUL.md before each agent run.
        # OpenClaw's agent framework can overwrite SOUL.md with its generic
        # default during a session. Re-copy from the repo to ensure the
        # node's real identity is always active.
        try:
            import os as _os
            _here = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            _node = _os.environ.get("OPENCLAW_NODE", "")
            if not _node:
                _cfg_path = _os.path.join(_here, "config.json")
                if _os.path.isfile(_cfg_path):
                    with open(_cfg_path) as _f:
                        _node = json.loads(_f.read()).get("this_node", "")
            if _node:
                _soul_src = _os.path.join(_here, "mesh", "souls", f"SOUL.{_node}.md")
                if _os.path.isfile(_soul_src):
                    _ws = str(__import__("pathlib").Path(
                        _os.environ.get("USERPROFILE", _os.environ.get("HOME", ""))
                    ) / ".openclaw" / "workspace" / "SOUL.md")
                    shutil.copy2(_soul_src, _ws)
                    log.info("[dispatch] Pre-seeded SOUL.md from %s", _soul_src)
        except Exception as _se:
            log.warning("[dispatch] SOUL pre-seed failed: %s", _se)
=======
        # Pre-seed SOUL.md with this node's identity before every dispatch.
        # OpenClaw may overwrite SOUL.md with a generic version — this ensures
        # the correct node soul is always in place before the agent runs.
        try:
            import pathlib
            script_dir = pathlib.Path(__file__).parent.parent
            node_soul = script_dir / "mesh" / "souls" / f"SOUL.{self.store.this_node}.md"
            workspace_soul = pathlib.Path.home() / ".openclaw" / "workspace" / "SOUL.md"
            if node_soul.exists() and workspace_soul.parent.exists():
                import shutil as _shutil
                workspace_soul.chmod(0o644)  # ensure writable before copy
                _shutil.copy2(str(node_soul), str(workspace_soul))
                log.info("[dispatch] Pre-seeded SOUL.md from %s", node_soul.name)
        except Exception as _e:
            log.warning("[dispatch] Could not pre-seed SOUL.md: %s", _e)
>>>>>>> Stashed changes

        try:
            # --session-id: dedicated session per dispatch task
            # --agent main: explicit agent target (required on Windows)
            session_id = f"dispatch-{task_id}" if task_id else "dispatch-adhoc"
            result = subprocess.run(
                [openclaw_bin, "agent", "-m", description, "--json",
                 "--session-id", session_id, "--agent", "main",
                 "--timeout", str(timeout)],
                capture_output=True, text=True, timeout=timeout + 30,
            )


            if result.returncode != 0:
                log.warning("[dispatch] Agent exited %d: %s",
                            result.returncode, result.stderr[:200])
                return 500, {
                    "status": "error",
                    "task_id": task_id,
                    "error": result.stderr[:500] or "agent exited non-zero",
                    "returncode": result.returncode,
                }

            # Parse JSON output if possible
            output = result.stdout.strip()
            try:
                import json as _json
                parsed = _json.loads(output)
                agent_response = parsed.get("response", parsed.get("content", output))
            except Exception:
                agent_response = output

            log.info("[dispatch] Task %s completed (%d chars)",
                     task_id[:14] if task_id else "adhoc", len(agent_response))

            return 200, {
                "status": "ok",
                "task_id": task_id,
                "result": agent_response,
            }

        except subprocess.TimeoutExpired:
            log.error("[dispatch] Task %s timed out after %ds", task_id[:14], timeout)
            return 504, {
                "status": "timeout",
                "task_id": task_id,
                "error": f"agent turn timed out after {timeout}s",
            }
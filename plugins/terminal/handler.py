"""
terminal — Plugin: AI terminal access with approval workflow.

Allows the AI to request command execution on the user's machine.
All commands require explicit user approval before running (unless
the user has whitelisted specific safe commands).
"""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

log = logging.getLogger("valhalla.plugins.terminal")

# In-memory state
_pending_commands: dict[str, dict[str, Any]] = {}
_command_history: list[dict[str, Any]] = []
_config: dict = {}


def register_routes(app, config: dict) -> None:
    """Register terminal plugin routes."""
    global _config
    _config = config

    from fastapi import HTTPException
    from pydantic import BaseModel, Field

    class ExecRequest(BaseModel):
        command: str = Field(max_length=2048)
        reason: str = ""
        working_dir: str = ""

    class ApproveRequest(BaseModel):
        command_id: str
        approved: bool

    @app.post("/api/v1/terminal/exec")
    async def request_exec(req: ExecRequest):
        """Request command execution — queued for user approval."""
        terminal_cfg = _config.get("terminal", {})
        require_approval = terminal_cfg.get("require_approval", True)
        allowed = terminal_cfg.get("allowed_commands", [])

        # Check if command is pre-approved
        cmd_base = req.command.split()[0] if req.command.strip() else ""
        auto_approved = not require_approval or cmd_base in allowed

        import secrets
        cmd_id = f"cmd-{secrets.token_urlsafe(6)}"

        entry = {
            "id": cmd_id,
            "command": req.command,
            "reason": req.reason,
            "working_dir": req.working_dir or ".",
            "status": "approved" if auto_approved else "pending",
            "requested_at": time.time(),
            "result": None,
        }

        if auto_approved:
            # Execute immediately
            entry = _execute_command(entry)
            _command_history.append(entry)
            log.info("[terminal] Auto-approved and executed: %s", cmd_base)
        else:
            _pending_commands[cmd_id] = entry
            log.info("[terminal] Command queued for approval: %s", req.command[:80])

            # Emit event for dashboard notification
            try:
                from plugin_loader import emit_event
                emit_event("terminal.command_requested", {
                    "id": cmd_id,
                    "command": req.command,
                    "reason": req.reason,
                })
            except Exception:
                pass

        return {
            "ok": True,
            "command_id": cmd_id,
            "status": entry["status"],
            "result": entry.get("result"),
            "message": "Executed" if auto_approved else "Awaiting user approval",
        }

    @app.get("/api/v1/terminal/status")
    async def get_terminal_status():
        """Get pending commands and terminal configuration."""
        terminal_cfg = _config.get("terminal", {})
        return {
            "pending": list(_pending_commands.values()),
            "pending_count": len(_pending_commands),
            "require_approval": terminal_cfg.get("require_approval", True),
            "sandbox": terminal_cfg.get("sandbox", True),
            "allowed_commands": terminal_cfg.get("allowed_commands", []),
        }

    @app.post("/api/v1/terminal/approve")
    async def approve_command(req: ApproveRequest):
        """Approve or deny a pending command."""
        if req.command_id not in _pending_commands:
            raise HTTPException(404, f"Command '{req.command_id}' not found or already processed")

        entry = _pending_commands.pop(req.command_id)

        if req.approved:
            entry["status"] = "approved"
            entry = _execute_command(entry)
            log.info("[terminal] Command approved and executed: %s", entry["command"][:80])

            try:
                from plugin_loader import emit_event
                emit_event("terminal.command_approved", {
                    "id": entry["id"],
                    "command": entry["command"],
                })
            except Exception:
                pass
        else:
            entry["status"] = "denied"
            entry["result"] = {"stdout": "", "stderr": "", "returncode": -1}
            log.info("[terminal] Command denied: %s", entry["command"][:80])

            try:
                from plugin_loader import emit_event
                emit_event("terminal.command_denied", {
                    "id": entry["id"],
                    "command": entry["command"],
                })
            except Exception:
                pass

        _command_history.append(entry)
        return {
            "ok": True,
            "command_id": entry["id"],
            "status": entry["status"],
            "result": entry.get("result"),
        }

    @app.get("/api/v1/terminal/history")
    async def get_history():
        """Get recent command execution history."""
        return {
            "history": _command_history[-50:],
            "total": len(_command_history),
        }


def _execute_command(entry: dict) -> dict:
    """Execute a command in a subprocess with timeout and size limits."""
    terminal_cfg = _config.get("terminal", {})
    timeout = terminal_cfg.get("timeout", 30)
    max_output = terminal_cfg.get("max_output_bytes", 65536)

    try:
        result = subprocess.run(
            entry["command"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=entry.get("working_dir") or None,
        )
        entry["status"] = "completed"
        entry["result"] = {
            "stdout": result.stdout[:max_output],
            "stderr": result.stderr[:max_output],
            "returncode": result.returncode,
        }
        entry["completed_at"] = time.time()

        try:
            from plugin_loader import emit_event
            emit_event("terminal.command_executed", {
                "id": entry["id"],
                "command": entry["command"],
                "returncode": result.returncode,
            })
        except Exception:
            pass

    except subprocess.TimeoutExpired:
        entry["status"] = "timeout"
        entry["result"] = {
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "returncode": -1,
        }
    except Exception as e:
        entry["status"] = "error"
        entry["result"] = {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }

    return entry

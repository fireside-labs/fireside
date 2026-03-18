"""
terminal — Plugin: AI terminal access with configurable permissions.

Allows the AI to execute commands on the user's machine.
Permission levels (configurable in valhalla.yaml under terminal.mode):
  - "open"     : commands run immediately (default)
  - "approve"  : commands queue for user approval first
  - "blocklist": everything runs except blocked commands
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
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
        """Execute a command — runs immediately unless approval mode is on."""
        terminal_cfg = _config.get("terminal", {})
        mode = terminal_cfg.get("mode", "open")  # open | approve | blocklist
        blocked = terminal_cfg.get("blocked_commands", [])  # for blocklist mode

        cmd_base = req.command.split()[0] if req.command.strip() else ""

        # Determine if command runs immediately
        if mode == "approve":
            auto_approved = False
        elif mode == "blocklist" and cmd_base in blocked:
            auto_approved = False
        else:
            auto_approved = True  # "open" mode — just run it

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
            "mode": terminal_cfg.get("mode", "open"),
            "blocked_commands": terminal_cfg.get("blocked_commands", []),
            "timeout": terminal_cfg.get("timeout", 30),
        }

    @app.put("/api/v1/terminal/permissions")
    async def set_permissions(request):
        """Change terminal permission mode (open/approve/blocklist)."""
        import json
        body = await request.json()
        mode = body.get("mode", "open")
        if mode not in ("open", "approve", "blocklist"):
            raise HTTPException(400, "Mode must be: open, approve, or blocklist")

        # Update in-memory config
        if "terminal" not in _config:
            _config["terminal"] = {}
        _config["terminal"]["mode"] = mode

        if "blocked_commands" in body:
            _config["terminal"]["blocked_commands"] = body["blocked_commands"]

        log.info("[terminal] Permission mode set to: %s", mode)
        return {"ok": True, "mode": mode}

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

    # ===================================================================
    # FILE OPERATIONS — structured file access (safer than shell pipes)
    # ===================================================================

    class FileReadRequest(BaseModel):
        path: str
        encoding: str = "utf-8"
        max_bytes: int = 1_048_576  # 1MB default limit

    class FileWriteRequest(BaseModel):
        path: str
        content: str
        mode: str = "w"  # 'w' = overwrite, 'a' = append
        encoding: str = "utf-8"
        create_dirs: bool = True

    class FileListRequest(BaseModel):
        path: str = "."
        recursive: bool = False
        pattern: str = "*"
        max_results: int = 500

    class FileSearchRequest(BaseModel):
        path: str = "."
        query: str
        extensions: list = []  # e.g. [".py", ".js"]
        max_results: int = 100
        case_sensitive: bool = False

    class FileCopyRequest(BaseModel):
        source: str
        destination: str
        overwrite: bool = False

    class FileMkdirRequest(BaseModel):
        path: str

    class FileDeleteRequest(BaseModel):
        path: str
        confirm: bool = False  # must be True to actually delete

    def _safe_path(p: str) -> Path:
        """Resolve a path, ensuring it doesn't escape sandbox if configured."""
        resolved = Path(p).resolve()
        terminal_cfg = _config.get("terminal", {})
        sandbox_root = terminal_cfg.get("sandbox_root")
        if sandbox_root:
            root = Path(sandbox_root).resolve()
            if not str(resolved).startswith(str(root)):
                raise ValueError(
                    f"Path '{p}' is outside sandbox root '{root}'"
                )
        return resolved

    @app.post("/api/v1/files/read")
    async def file_read(req: FileReadRequest):
        """Read the contents of a file."""
        try:
            path = _safe_path(req.path)
            if not path.exists():
                raise HTTPException(404, f"File not found: {req.path}")
            if not path.is_file():
                raise HTTPException(400, f"Not a file: {req.path}")

            size = path.stat().st_size
            if size > req.max_bytes:
                raise HTTPException(413, f"File too large: {size} bytes (max {req.max_bytes})")

            content = path.read_text(encoding=req.encoding)
            return {
                "ok": True,
                "path": str(path),
                "size": size,
                "content": content,
                "lines": content.count("\n") + 1,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Read failed: {e}")

    @app.post("/api/v1/files/write")
    async def file_write(req: FileWriteRequest):
        """Write content to a file. Creates parent directories if needed."""
        try:
            path = _safe_path(req.path)

            if req.create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)

            if req.mode == "a":
                with open(path, "a", encoding=req.encoding) as f:
                    f.write(req.content)
            else:
                path.write_text(req.content, encoding=req.encoding)

            log.info("[terminal] File written: %s (%d bytes)", path, len(req.content))

            try:
                from plugin_loader import emit_event
                emit_event("terminal.file_written", {
                    "path": str(path),
                    "size": len(req.content),
                    "mode": req.mode,
                })
            except Exception:
                pass

            return {
                "ok": True,
                "path": str(path),
                "size": len(req.content),
                "mode": req.mode,
            }
        except Exception as e:
            raise HTTPException(500, f"Write failed: {e}")

    @app.post("/api/v1/files/list")
    async def file_list(req: FileListRequest):
        """List files and directories at a path."""
        import fnmatch as _fnmatch

        try:
            path = _safe_path(req.path)
            if not path.exists():
                raise HTTPException(404, f"Path not found: {req.path}")

            entries = []
            count = 0

            if req.recursive:
                for item in path.rglob(req.pattern):
                    if count >= req.max_results:
                        break
                    try:
                        stat = item.stat()
                        entries.append({
                            "name": item.name,
                            "path": str(item),
                            "relative": str(item.relative_to(path)),
                            "type": "dir" if item.is_dir() else "file",
                            "size": stat.st_size if item.is_file() else None,
                            "modified": stat.st_mtime,
                        })
                        count += 1
                    except (PermissionError, OSError):
                        continue
            else:
                for item in sorted(path.iterdir()):
                    if count >= req.max_results:
                        break
                    if req.pattern != "*" and not _fnmatch.fnmatch(item.name, req.pattern):
                        continue
                    try:
                        stat = item.stat()
                        entries.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "dir" if item.is_dir() else "file",
                            "size": stat.st_size if item.is_file() else None,
                            "modified": stat.st_mtime,
                        })
                        count += 1
                    except (PermissionError, OSError):
                        continue

            return {
                "ok": True,
                "path": str(path),
                "count": len(entries),
                "entries": entries,
                "truncated": count >= req.max_results,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"List failed: {e}")

    @app.post("/api/v1/files/search")
    async def file_search(req: FileSearchRequest):
        """Search for text inside files (grep-like)."""
        try:
            path = _safe_path(req.path)
            if not path.exists():
                raise HTTPException(404, f"Path not found: {req.path}")

            matches = []
            count = 0
            query = req.query if req.case_sensitive else req.query.lower()

            for item in path.rglob("*"):
                if count >= req.max_results:
                    break
                if not item.is_file():
                    continue
                if req.extensions and item.suffix not in req.extensions:
                    continue

                try:
                    text = item.read_text(encoding="utf-8", errors="ignore")
                    search_text = text if req.case_sensitive else text.lower()

                    for line_num, line in enumerate(search_text.split("\n"), 1):
                        if count >= req.max_results:
                            break
                        if query in line:
                            # Get the original line (not lowered)
                            orig_lines = text.split("\n")
                            orig_line = orig_lines[line_num - 1] if line_num <= len(orig_lines) else line
                            matches.append({
                                "file": str(item),
                                "relative": str(item.relative_to(path)) if str(item).startswith(str(path)) else str(item),
                                "line": line_num,
                                "content": orig_line.strip()[:200],
                            })
                            count += 1
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue

            return {
                "ok": True,
                "query": req.query,
                "path": str(path),
                "total_matches": len(matches),
                "matches": matches,
                "truncated": count >= req.max_results,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Search failed: {e}")

    @app.post("/api/v1/files/mkdir")
    async def file_mkdir(req: FileMkdirRequest):
        """Create a directory (and parents if needed)."""
        try:
            path = _safe_path(req.path)
            path.mkdir(parents=True, exist_ok=True)
            log.info("[terminal] Directory created: %s", path)
            return {"ok": True, "path": str(path)}
        except Exception as e:
            raise HTTPException(500, f"Mkdir failed: {e}")

    @app.post("/api/v1/files/copy")
    async def file_copy(req: FileCopyRequest):
        """Copy a file or directory."""
        import shutil as _shutil
        try:
            src = _safe_path(req.source)
            dst = _safe_path(req.destination)

            if not src.exists():
                raise HTTPException(404, f"Source not found: {req.source}")
            if dst.exists() and not req.overwrite:
                raise HTTPException(409, f"Destination exists: {req.destination}")

            if src.is_dir():
                _shutil.copytree(str(src), str(dst), dirs_exist_ok=req.overwrite)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                _shutil.copy2(str(src), str(dst))

            log.info("[terminal] Copied: %s → %s", src, dst)
            return {"ok": True, "source": str(src), "destination": str(dst)}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Copy failed: {e}")

    @app.post("/api/v1/files/delete")
    async def file_delete(req: FileDeleteRequest):
        """Delete a file or empty directory. Requires confirm=True."""
        import shutil as _shutil
        if not req.confirm:
            raise HTTPException(400, "Set confirm=true to delete")
        try:
            path = _safe_path(req.path)
            if not path.exists():
                raise HTTPException(404, f"Not found: {req.path}")

            if path.is_file():
                size = path.stat().st_size
                path.unlink()
                log.info("[terminal] File deleted: %s (%d bytes)", path, size)
            elif path.is_dir():
                item_count = sum(1 for _ in path.rglob("*"))
                _shutil.rmtree(str(path))
                log.info("[terminal] Directory deleted: %s (%d items)", path, item_count)
            else:
                raise HTTPException(400, f"Cannot delete: {req.path}")

            try:
                from plugin_loader import emit_event
                emit_event("terminal.file_deleted", {
                    "path": str(path),
                })
            except Exception:
                pass

            return {"ok": True, "path": str(path), "deleted": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Delete failed: {e}")


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


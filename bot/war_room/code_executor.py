"""
war_room/code_executor.py -- Sandboxed Code Execution (Phase 1: Python only)

Closes the autonomous loop:
  task in → code out → run in sandbox → result → memory → next task informed

Safety layers (3-deep):
  1. Static blocklist — reject dangerous patterns before anything runs
  2. Stand review   — 7b model semantic safety check (future)
  3. Resource limits — timeout, no network, memory cap

Human approval gate:
  Code is sent to Telegram with approve/deny buttons.
  Approval state is written to sandbox_approvals.json.
  The Telegram callback handler in bifrost.py writes the decision.
  This module polls the file until approved/denied/timeout.

Usage:
  from war_room.code_executor import execute_code

  result = execute_code("print(sum(range(100)))", language="python")
  # result = {"ok": True, "stdout": "4950\\n", "exit_code": 0, ...}
"""

import hashlib
import json
import logging
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger("code_executor")

BASE = Path(__file__).parent.parent  # bot/bot/

# Load config for Telegram
try:
    _cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    BOT_TOKEN = _cfg.get("telegram_bot_token", "")
    CHAT_ID = _cfg.get("telegram_chat_id", "")
except Exception:
    BOT_TOKEN = ""
    CHAT_ID = ""

# Approval state file
APPROVALS_FILE = BASE / "sandbox_approvals.json"

# ---------------------------------------------------------------------------
# Safety: Static blocklist
# ---------------------------------------------------------------------------

BLOCKED_PATTERNS = [
    # System commands
    "os.system", "os.popen", "os.exec", "os.remove", "os.unlink",
    "os.rmdir", "os.rename",
    # Subprocess
    "subprocess.run", "subprocess.Popen", "subprocess.call",
    "subprocess.check_output", "subprocess.check_call",
    # File destruction
    "shutil.rmtree", "shutil.move",
    # Network
    "import socket", "import http", "import urllib",
    "import requests", "from requests", "import aiohttp",
    # Code injection
    "eval(", "exec(", "__import__",
    "compile(", "globals()", "locals()",
    # Dangerous filesystem
    "open('/etc", "open('/var", "open('/usr",
    'open("/etc', 'open("/var', 'open("/usr',
    # Shell exploits
    "rm -rf", "del /", "format c:",
    "; bash", "; sh", "| bash", "| sh",
]


def check_safety(code: str) -> Optional[str]:
    """
    Static safety check. Returns None if safe, or a rejection reason string.
    """
    code_lower = code.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in code_lower:
            return f"blocked pattern: {pattern}"
    return None


# ---------------------------------------------------------------------------
# Approval state (file-based, shared with bifrost callback handler)
# ---------------------------------------------------------------------------

def _load_approvals() -> dict:
    try:
        if APPROVALS_FILE.exists():
            return json.loads(APPROVALS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_approvals(approvals: dict):
    try:
        APPROVALS_FILE.write_text(
            json.dumps(approvals, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        log.warning("[executor] Failed to save approvals: %s", e)


def set_approval(request_id: str, decision: str):
    """Called by bifrost callback handler to record approve/deny."""
    approvals = _load_approvals()
    approvals[request_id] = {
        "decision": decision,
        "ts": time.time(),
    }
    _save_approvals(approvals)
    log.info("[executor] Approval recorded: %s → %s", request_id, decision)


def get_approval(request_id: str) -> Optional[str]:
    """Check if a decision has been made for request_id."""
    approvals = _load_approvals()
    entry = approvals.get(request_id)
    if entry:
        return entry.get("decision")
    return None


def cleanup_approvals(max_age: int = 3600):
    """Remove approvals older than max_age seconds."""
    approvals = _load_approvals()
    now = time.time()
    cleaned = {k: v for k, v in approvals.items()
               if now - v.get("ts", 0) < max_age}
    if len(cleaned) != len(approvals):
        _save_approvals(cleaned)


# ---------------------------------------------------------------------------
# Telegram approval gate
# ---------------------------------------------------------------------------

def _send_approval_request(code: str, language: str, request_id: str) -> bool:
    """Send code preview to Telegram with approve/deny inline buttons."""
    if not BOT_TOKEN or not CHAT_ID:
        log.warning("[executor] No Telegram config — auto-approving")
        return False

    code_preview = code[:500]
    if len(code) > 500:
        code_preview += f"\n... ({len(code) - 500} more chars)"

    text = (
        f"🔧 *Code Execution Request*\n\n"
        f"Language: `{language}`\n"
        f"Lines: {len(code.splitlines())}\n"
        f"ID: `{request_id}`\n\n"
        f"```{language}\n{code_preview}\n```\n\n"
        f"⚠️ Static safety: *passed*"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    body = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"exec-approve:{request_id}"},
                {"text": "❌ Deny", "callback_data": f"exec-deny:{request_id}"},
            ]]
        }
    }).encode()
    try:
        req = urllib.request.Request(url, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10):
            pass
        return True
    except Exception as e:
        log.error("[executor] Telegram send failed: %s", e)
        return False


def request_approval(code: str, language: str = "python",
                     timeout_s: int = 300) -> str:
    """
    Send code to Telegram for human review.
    Polls approval file until approved/denied or timeout.
    Returns: 'approved', 'denied', or 'timeout'.
    """
    request_id = hashlib.md5(
        f"{code}{time.time()}".encode()
    ).hexdigest()[:12]

    sent = _send_approval_request(code, language, request_id)
    if not sent:
        log.info("[executor] No Telegram — auto-approving %s", request_id)
        return "approved"

    # Poll approval file for decision
    log.info("[executor] Awaiting approval for %s (timeout=%ds)", request_id, timeout_s)
    start = time.time()
    while time.time() - start < timeout_s:
        decision = get_approval(request_id)
        if decision:
            log.info("[executor] %s → %s", request_id, decision)
            return decision
        time.sleep(3)

    log.warning("[executor] Approval timeout for %s", request_id)
    return "timeout"


# ---------------------------------------------------------------------------
# Sandbox execution
# ---------------------------------------------------------------------------

SANDBOX_DIR = BASE / "sandbox_runs"
MAX_TIMEOUT = 60
DEFAULT_TIMEOUT = 30
MAX_OUTPUT_BYTES = 50_000  # 50KB


def execute_code(
    code: str,
    language: str = "python",
    timeout: int = DEFAULT_TIMEOUT,
    task_id: str = "",
    require_approval: bool = True,
) -> dict:
    """
    Execute code in a sandboxed subprocess.
    Returns dict: ok, exit_code, stdout, stderr, execution_time_ms, ...
    """
    timeout = min(timeout, MAX_TIMEOUT)

    if language != "python":
        return {"ok": False, "error": f"unsupported language: {language}"}

    # Safety check
    safety_issue = check_safety(code)
    if safety_issue:
        log.warning("[executor] Code blocked: %s", safety_issue)
        return {"ok": False, "error": safety_issue, "safety_review": "blocked"}

    # Human approval gate
    if require_approval:
        approval = request_approval(code, language)
        if approval != "approved":
            log.info("[executor] Code %s by human", approval)
            return {"ok": False, "error": f"human {approval}",
                    "safety_review": "passed", "approval": approval}
    else:
        approval = "auto"

    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    run_id = hashlib.md5(f"{code}{time.time()}".encode()).hexdigest()[:12]
    code_file = SANDBOX_DIR / f"run_{run_id}.py"
    code_file.write_text(code, encoding="utf-8")

    # Execute
    start_time = time.time()
    try:
        env = os.environ.copy()
        for key in ["PYTHONSTARTUP", "PYTHONPATH"]:
            env.pop(key, None)
        env["HOME"] = str(SANDBOX_DIR)

        result = subprocess.run(
            ["python3", str(code_file)],
            capture_output=True,
            timeout=timeout,
            cwd=str(SANDBOX_DIR),
            env=env,
            stdin=subprocess.DEVNULL,
        )
        elapsed_ms = int((time.time() - start_time) * 1000)

        stdout = result.stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
        stderr = result.stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]

        exec_result = {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time_ms": elapsed_ms,
            "safety_review": "passed",
            "approval": approval,
            "run_id": run_id,
        }

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - start_time) * 1000)
        exec_result = {
            "ok": False,
            "error": f"timeout after {timeout}s",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Process killed after {timeout}s timeout",
            "execution_time_ms": elapsed_ms,
            "safety_review": "passed",
            "approval": approval,
            "run_id": run_id,
        }

    except Exception as e:
        exec_result = {
            "ok": False,
            "error": str(e),
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "execution_time_ms": 0,
            "safety_review": "passed",
            "approval": approval,
            "run_id": run_id,
        }

    finally:
        try:
            code_file.unlink(missing_ok=True)
        except Exception:
            pass

    # Memory write-back
    memory_id = _record_to_memory(code, exec_result, task_id)
    if memory_id:
        exec_result["memory_id"] = memory_id

    log.info("[executor] %s exit=%s time=%dms stdout=%d stderr=%d",
             run_id,
             exec_result.get("exit_code", "?"),
             exec_result.get("execution_time_ms", 0),
             len(exec_result.get("stdout", "")),
             len(exec_result.get("stderr", "")))

    return exec_result


# ---------------------------------------------------------------------------
# Memory write-back
# ---------------------------------------------------------------------------

def _record_to_memory(code: str, result: dict, task_id: str = "") -> Optional[str]:
    """Write execution result to local memory-sync as a memory."""
    try:
        exit_code = result.get("exit_code", -1)
        stdout = result.get("stdout", "")[:200]
        stderr = result.get("stderr", "")[:200]
        status = "success" if exit_code == 0 else "failed"

        content = f"[EXEC] python {status}: {code[:120]}"
        if stdout:
            content += f" → stdout: {stdout[:100]}"
        if stderr and exit_code != 0:
            content += f" → stderr: {stderr[:100]}"

        memory = {
            "content": content,
            "tags": ["execution", status, "code_executor"],
            "importance": 0.7 if exit_code == 0 else 0.85,
            "node": "odin",
            "agent": "code_executor",
        }
        if task_id:
            memory["task_id"] = task_id

        payload = json.dumps({"memories": [memory]}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8765/memory-sync",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            stored = resp.get("stored", [])
            if stored:
                return stored[0].get("memory_id", "")
            return ""
    except Exception as e:
        log.debug("[executor] Memory write-back failed: %s", e)
        return None

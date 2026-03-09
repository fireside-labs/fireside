"""
dispatcher.py -- Bifrost <-> OpenClaw Dispatch Bridge

Standalone script that bridges the War Room task board with OpenClaw's
full agent dispatch system.  When a task is assigned to thor/freya/heimdall
and has status "open", this script:
  1. Claims ALL dispatchable tasks immediately (prevents gossip race)
  2. Dispatches to nodes in PARALLEL (one thread per node)
  3. Posts results back to the War Room
  4. Recovers stuck tasks that stay "claimed" past the timeout

Run:  python dispatcher.py
Kill:  Ctrl-C (or launchd: launchctl unload)
"""

import json
import logging
import os
import socket
import time
import threading
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [dispatcher] %(message)s",
)
log = logging.getLogger("dispatcher")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
POLL_INTERVAL = int(os.environ.get("DISPATCH_POLL_INTERVAL", "30"))
LOCAL_BIFROST = os.environ.get("DISPATCH_LOCAL_BIFROST", "http://127.0.0.1:8765")
DISPATCH_TIMEOUT = int(os.environ.get("DISPATCH_TIMEOUT", "300"))
# How long a task can stay "claimed" before we consider it stuck (seconds)
STUCK_TIMEOUT = int(os.environ.get("DISPATCH_STUCK_TIMEOUT", "600"))

# Node registry -- use Tailscale hostnames (resolve dynamically)
# Falls back to IPs if hostname resolution fails
NODE_HOSTS = {
    "thor":     os.environ.get("NODE_THOR",     "thor:8765"),
    "freya":    os.environ.get("NODE_FREYA",    "freya:8765"),
    "heimdall": os.environ.get("NODE_HEIMDALL", "heimdall:8765"),
}

# ---------------------------------------------------------------------------
# Hostname resolution with fallback
# ---------------------------------------------------------------------------
_IP_CACHE: dict = {}
_IP_CACHE_TTL = 300  # re-resolve every 5 minutes

def _resolve_node(name: str) -> str:
    """Resolve a node hostname:port to http://ip:port. Caches for 5 minutes."""
    host_port = NODE_HOSTS.get(name, "")
    if not host_port:
        raise ValueError(f"Unknown node: {name}")

    # If already an IP, use directly
    if host_port.startswith("http"):
        return host_port

    now = time.time()
    cached = _IP_CACHE.get(name)
    if cached and (now - cached[1]) < _IP_CACHE_TTL:
        return cached[0]

    host, _, port = host_port.partition(":")
    port = port or "8765"
    try:
        ip = socket.gethostbyname(host)
        url = f"http://{ip}:{port}"
        _IP_CACHE[name] = (url, now)
        return url
    except socket.gaierror:
        # Hostname resolution failed -- try cached value or raise
        if cached:
            log.warning("DNS failed for %s, using cached IP: %s", name, cached[0])
            return cached[0]
        raise ValueError(f"Cannot resolve hostname for node '{name}' ({host_port})")

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _post(url: str, data: dict, timeout: int = 30) -> dict:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

# ---------------------------------------------------------------------------
# Dispatch a single task (runs in its own thread for parallel dispatch)
# ---------------------------------------------------------------------------
def _dispatch_one(task: dict):
    """Dispatch a single claimed task to its node. Thread-safe."""
    assigned = (task.get("assigned_to") or "").lower()
    task_id = task.get("id", task.get("task_id", ""))
    title = task.get("title", "untitled")[:60]
    description = task.get("description", task.get("title", ""))
    # Append standard dispatch instructions
    description += (
        "\n\n---\n"
        "DISPATCH RULES: When you finish, report a brief summary of what "
        "you did and the file paths you created or modified. Do NOT paste "
        "file contents or code in your response. If there are bugs or "
        "errors, describe them briefly."
    )

    try:
        node_url = _resolve_node(assigned)
    except ValueError as e:
        log.error("  X Cannot resolve %s: %s", assigned, e)
        _try_block(task_id, assigned, str(e))
        return

    log.info("> Dispatching %s to %s (%s): %s", task_id[:14], assigned, node_url, title)

    # Dispatch to the remote node's /dispatch endpoint
    try:
        result = _post(f"{node_url}/dispatch", {
            "task_id": task_id,
            "description": description,
            "timeout": DISPATCH_TIMEOUT,
        }, timeout=DISPATCH_TIMEOUT + 60)
    except urllib.error.URLError as e:
        log.error("  X Node %s unreachable: %s", assigned, e)
        _try_block(task_id, assigned, f"Node unreachable: {e}")
        return
    except Exception as e:
        log.error("  X Dispatch to %s failed: %s", assigned, e)
        _try_block(task_id, assigned, str(e))
        return

    # Post result back to War Room
    dispatch_status = result.get("status", "error")
    if dispatch_status == "ok":
        agent_result = result.get("result", "completed (no output)")
        try:
            _post(f"{LOCAL_BIFROST}/war-room/complete", {
                "task_id": task_id,
                "agent_id": assigned,
                "result": agent_result[:2000],
            })
            log.info("  OK Task %s completed by %s (%d chars)",
                     task_id[:14], assigned, len(agent_result))
        except Exception as e:
            log.error("  X Failed to post result for %s: %s", task_id[:14], e)
    else:
        error_msg = result.get("error", "unknown error")
        log.warning("  X Task %s failed on %s: %s", task_id[:14], assigned, error_msg)
        _try_block(task_id, assigned, error_msg)

# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------
def poll_and_dispatch():
    """One poll cycle: find open tasks -> claim ALL -> dispatch in parallel."""
    try:
        tasks = _get(f"{LOCAL_BIFROST}/war-room/tasks")
    except Exception as e:
        log.warning("Failed to fetch tasks: %s", e)
        return

    # Handle both list and dict-wrapped responses
    if isinstance(tasks, dict):
        tasks = tasks.get("tasks", [])
    if not isinstance(tasks, list):
        return

    # Phase 1: Claim ALL dispatchable tasks immediately
    claimed = []
    for task in tasks:
        status = task.get("status", "")
        assigned = (task.get("assigned_to") or "").lower()
        task_id = task.get("id", task.get("task_id", ""))

        if status != "open" or assigned not in NODE_HOSTS:
            continue

        try:
            _post(f"{LOCAL_BIFROST}/war-room/claim", {
                "task_id": task_id,
                "agent_id": assigned,
            })
            log.info("  Claimed %s for %s", task_id[:14], assigned)
            claimed.append(task)
        except Exception as e:
            log.warning("  X Failed to claim %s: %s", task_id[:14], e)

    if not claimed:
        # No new tasks -- check for stuck ones
        _recover_stuck(tasks)
        return

    log.info("> Dispatching %d claimed task(s) in parallel", len(claimed))

    # Phase 2: Dispatch in parallel (one thread per task)
    threads = []
    for task in claimed:
        t = threading.Thread(target=_dispatch_one, args=(task,), daemon=True)
        t.start()
        threads.append(t)

    # Wait for all dispatches to complete (with timeout)
    for t in threads:
        t.join(timeout=DISPATCH_TIMEOUT + 120)


# Track recovery attempts per task to prevent infinite re-dispatch loops
_recovery_count: dict = {}  # task_id -> count
MAX_RECOVERY = 2  # block after this many recoveries


def _recover_stuck(tasks: list):
    """Find tasks stuck in 'claimed' past STUCK_TIMEOUT.

    First recovery: re-open the task so the dispatcher can retry.
    After MAX_RECOVERY attempts: mark as blocked (stops the loop).
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for task in tasks:
        if task.get("status") != "claimed":
            continue
        updated = task.get("updated", "")
        try:
            task_time = datetime.fromisoformat(updated)
            if task_time.tzinfo is None:
                task_time = task_time.replace(tzinfo=timezone.utc)
            age = (now - task_time).total_seconds()
            if age > STUCK_TIMEOUT:
                task_id = task.get("id", "")
                agent = task.get("assigned_to", "unknown")
                count = _recovery_count.get(task_id, 0) + 1
                _recovery_count[task_id] = count

                if count > MAX_RECOVERY:
                    log.warning("  Blocking stuck task %s (claimed by %s, %d recovery attempts)",
                                task_id[:14], agent, count)
                    _try_block(task_id, agent,
                               f"Stuck after {count} recovery attempts ({int(age)}s)")
                    _recovery_count.pop(task_id, None)
                else:
                    log.warning("  Recovering stuck task %s (claimed by %s, %ds ago, attempt %d/%d)",
                                task_id[:14], agent, int(age), count, MAX_RECOVERY)
                    try:
                        _post(f"{LOCAL_BIFROST}/war-room/status", {
                            "task_id": task_id,
                            "status": "open",
                        })
                    except Exception:
                        pass
        except (ValueError, TypeError):
            continue


def _try_block(task_id: str, agent: str, reason: str):
    """Mark a task as blocked with an error reason."""
    try:
        _post(f"{LOCAL_BIFROST}/war-room/status", {
            "task_id": task_id,
            "status": "blocked",
            "reason": f"[dispatcher] {agent}: {reason}",
        })
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("Bifrost <-> OpenClaw dispatcher starting")
    log.info("  Poll interval: %ds  |  Timeout: %ds  |  Stuck: %ds",
             POLL_INTERVAL, DISPATCH_TIMEOUT, STUCK_TIMEOUT)
    log.info("  Nodes: %s", ", ".join(f"{k}={v}" for k, v in NODE_HOSTS.items()))
    log.info("  Local Bifrost: %s", LOCAL_BIFROST)

    while True:
        try:
            poll_and_dispatch()
        except KeyboardInterrupt:
            log.info("Dispatcher stopped (Ctrl-C)")
            break
        except Exception as e:
            log.error("Unexpected error in poll loop: %s", e)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

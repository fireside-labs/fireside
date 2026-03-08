"""
dispatcher.py — Bifrost ↔ OpenClaw Dispatch Bridge

Standalone script that bridges the War Room task board with OpenClaw's
full agent dispatch system.  When a task is assigned to thor/freya/heimdall
and has status "open", this script:
  1. Claims the task
  2. POSTs to that node's /dispatch endpoint
  3. Posts the result back to the War Room

Run:  python dispatcher.py
Kill:  Ctrl-C (or launchd: launchctl unload)

This script is fully standalone — if it crashes, Bifrost and OpenClaw
continue to work independently.
"""

import json
import logging
import os
import time
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

# Node registry — only dispatch to these agents
NODES = {
    "thor":     "http://100.117.255.38:8765",
    "freya":    "http://100.102.105.3:8765",
    "heimdall": "http://100.108.153.23:8765",
}

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
# Core loop
# ---------------------------------------------------------------------------
def poll_and_dispatch():
    """One poll cycle: find open tasks → claim → dispatch → complete."""
    try:
        tasks = _get(f"{LOCAL_BIFROST}/war-room/tasks")
    except Exception as e:
        log.warning("Failed to fetch tasks: %s", e)
        return

    for task in tasks:
        status = task.get("status", "")
        assigned = task.get("assigned_to", "").lower()
        task_id = task.get("id", task.get("task_id", ""))

        # Only process open tasks assigned to known remote nodes
        if status != "open" or assigned not in NODES:
            continue

        node_url = NODES[assigned]
        title = task.get("title", "untitled")[:60]
        description = task.get("description", task.get("title", ""))

        log.info("▶ Dispatching task %s to %s: %s", task_id[:14], assigned, title)

        # 1. Claim the task
        try:
            _post(f"{LOCAL_BIFROST}/war-room/claim", {
                "task_id": task_id,
                "agent_id": assigned,
            })
        except Exception as e:
            log.warning("  ✗ Failed to claim %s: %s", task_id[:14], e)
            continue

        # 2. Dispatch to the remote node's /dispatch endpoint
        try:
            result = _post(f"{node_url}/dispatch", {
                "task_id": task_id,
                "description": description,
                "timeout": DISPATCH_TIMEOUT,
            }, timeout=DISPATCH_TIMEOUT + 60)  # extra buffer for HTTP overhead
        except urllib.error.URLError as e:
            log.error("  ✗ Node %s unreachable: %s", assigned, e)
            _try_block(task_id, assigned, f"Node unreachable: {e}")
            continue
        except Exception as e:
            log.error("  ✗ Dispatch to %s failed: %s", assigned, e)
            _try_block(task_id, assigned, str(e))
            continue

        # 3. Post result back to War Room
        dispatch_status = result.get("status", "error")
        if dispatch_status == "ok":
            agent_result = result.get("result", "completed (no output)")
            try:
                _post(f"{LOCAL_BIFROST}/war-room/complete", {
                    "task_id": task_id,
                    "agent_id": assigned,
                    "result": agent_result[:2000],
                })
                log.info("  ✓ Task %s completed by %s (%d chars)",
                         task_id[:14], assigned, len(agent_result))
            except Exception as e:
                log.error("  ✗ Failed to post result for %s: %s", task_id[:14], e)
        else:
            error_msg = result.get("error", "unknown error")
            log.warning("  ✗ Task %s failed on %s: %s", task_id[:14], assigned, error_msg)
            _try_block(task_id, assigned, error_msg)


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
    log.info("Bifrost ↔ OpenClaw dispatcher starting")
    log.info("  Poll interval: %ds  |  Timeout: %ds", POLL_INTERVAL, DISPATCH_TIMEOUT)
    log.info("  Nodes: %s", ", ".join(f"{k}={v}" for k, v in NODES.items()))
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

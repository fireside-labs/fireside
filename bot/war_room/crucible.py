"""
war_room/crucible.py -- THE CRUCIBLE: Adversarial Dream Cycle for Procedures

Scheduled at 4:45 AM (before normal consolidation at 5:00 AM).
For each procedure in the mesh, Odin generates adversarial edge cases
where the procedure would fail. If a procedure breaks under scrutiny,
its confidence is downgraded and the owning node is notified.

Only battle-tested procedures survive.

Usage:
  python -m war_room.crucible [--dry-run] [--limit N]

  # Or triggered via POST /crucible
"""

import json
import logging
import time
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger("crucible")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

BASE = Path(__file__).parent.parent   # bot/bot/

OLLAMA_BASE = "http://127.0.0.1:11434"
MODEL = "qwen3.5:9b"

ADVERSARIAL_PROMPT = """\
You are a red-team stress tester. Your job is to BREAK procedures by finding edge cases.

Given this procedure that a node uses to complete tasks:

Task Type: {task_type}
Approach: {approach}
Confidence: {confidence}
Uses: {uses}

Generate exactly 3 edge cases where this procedure would FAIL or produce wrong results.
For each, explain:
1. The specific input/scenario that breaks it
2. WHY the procedure fails in this case
3. How severe the failure would be (low/medium/high)

Format each edge case as:
EDGE_CASE: <scenario>
FAILURE: <why it breaks>
SEVERITY: <low|medium|high>

If the procedure is robust and you genuinely cannot break it, say: UNBREAKABLE
Be ruthless. Find real weaknesses, not hypothetical ones.
"""


def _call_model(prompt: str, timeout: int = 60) -> Optional[str]:
    """Call Ollama generate API."""
    try:
        payload = json.dumps({
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.8,  # creative adversarial thinking
                "num_predict": 500,
            },
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            return data.get("response", "").strip()
    except Exception as e:
        log.error("[crucible] Model call failed: %s", e)
        return None


def _fetch_procedures(limit: int = 50) -> list[dict]:
    """Fetch procedures from local Bifrost."""
    try:
        url = f"http://127.0.0.1:8765/procedures?limit={limit}"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        procs = data.get("procedures", [])
        log.info("[crucible] Fetched %d procedures", len(procs))
        return procs
    except Exception as e:
        log.warning("[crucible] Cannot fetch procedures: %s", e)
        return []


def _downgrade_procedure(proc_id: str, reason: str, proc: dict,
                          dry_run: bool = False) -> bool:
    """Reduce procedure confidence via stand_downgrade."""
    if dry_run:
        log.info("[crucible] [DRY RUN] Would downgrade %s: %s", proc_id, reason)
        return True
    try:
        from war_room.procedures import stand_downgrade
        task_type = proc.get("task_type", "")
        approach = proc.get("approach", reason)
        stand_downgrade(task_type, approach)
        log.info("[crucible] Downgraded procedure %s: %s", proc_id, reason[:80])
        return True
    except Exception as e:
        log.debug("[crucible] Downgrade failed: %s", e)
        return False


def _notify_node(node_ip: str, proc: dict, edge_cases: str):
    """Notify the owning node that their procedure failed the crucible."""
    try:
        payload = json.dumps({
            "from": "odin",
            "message": (
                f"🔥 [CRUCIBLE] Your procedure failed stress-testing:\n"
                f"Task: {proc.get('task_type', '?')}\n"
                f"Edge cases found:\n{edge_cases[:500]}\n\n"
                f"Confidence has been reduced. Consider rewriting this procedure."
            ),
            "type": "alert",
        }).encode()
        req = urllib.request.Request(
            f"http://{node_ip}:8765/notify",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception:
        pass  # best effort


NODE_IPS = {
    "odin": "100.105.27.121",
    "freya": "100.102.105.3",
    "thor": "100.117.255.38",
    "heimdall": "100.108.153.23",
}


def run_crucible(dry_run: bool = False, limit: int = 20) -> dict:
    """
    Run the adversarial procedure stress-test.
    Returns stats: tested, broken, unbreakable.
    """
    log.info("=== THE CRUCIBLE — Adversarial Procedure Test ===")
    stats = {"tested": 0, "broken": 0, "unbreakable": 0, "skipped": 0}

    procs = _fetch_procedures(limit=limit)
    if not procs:
        log.info("[crucible] No procedures to test")
        return stats

    # Sort by confidence descending — test the most trusted first
    procs.sort(key=lambda p: p.get("confidence", 0.5), reverse=True)

    for proc in procs[:limit]:
        task_type = proc.get("task_type", "unknown")
        approach = proc.get("approach", "")
        confidence = proc.get("confidence", 0.5)
        uses = proc.get("uses", 0)
        proc_id = proc.get("id", "")
        node = proc.get("node", "unknown")

        if not approach or len(approach) < 20:
            stats["skipped"] += 1
            continue

        log.info("[crucible] Testing: [%s] %s (conf=%.2f, uses=%d)",
                 task_type, approach[:60], confidence, uses)

        # Generate adversarial edge cases
        prompt = ADVERSARIAL_PROMPT.format(
            task_type=task_type,
            approach=approach[:500],
            confidence=confidence,
            uses=uses,
        )
        result = _call_model(prompt)
        if not result:
            stats["skipped"] += 1
            continue

        stats["tested"] += 1

        # Parse result
        if "UNBREAKABLE" in result.upper():
            log.info("[crucible] ✅ UNBREAKABLE: %s", task_type)
            stats["unbreakable"] += 1
            continue

        # Count severity
        high_count = result.upper().count("SEVERITY: HIGH")
        medium_count = result.upper().count("SEVERITY: MEDIUM")
        edge_count = result.upper().count("EDGE_CASE:")

        if edge_count == 0:
            stats["unbreakable"] += 1
            continue

        # Only downgrade if high-severity edges found
        if high_count > 0:
            stats["broken"] += 1
            _downgrade_procedure(proc_id, f"Crucible found {high_count} high-severity edge cases", proc, dry_run)
            # Notify owning node
            node_ip = NODE_IPS.get(node)
            if node_ip and not dry_run:
                _notify_node(node_ip, proc, result)
            log.warning("[crucible] ❌ BROKEN: %s (%d high, %d medium edge cases)",
                        task_type, high_count, medium_count)
        else:
            log.info("[crucible] ⚠️ STRESSED: %s (%d medium edge cases, no high)",
                     task_type, medium_count)

    log.info("[crucible] Done: %s", stats)
    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="THE CRUCIBLE — Procedure Stress Test")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    run_crucible(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()

"""
crucible plugin — Adversarial stress-testing of learned procedures.

Ported from V1 bot/war_room/crucible.py (239 lines).
"Only battle-tested procedures survive."

For each procedure, generates adversarial edge cases and downgrades
confidence of procedures that break under scrutiny.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.crucible")

# Heimdall security: detect prompt injection in procedure text
try:
    from middleware.pipeline_guard import check_prompt_injection
except ImportError:
    check_prompt_injection = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_BASE_DIR = Path(".")
_OLLAMA_BASE = "http://127.0.0.1:11434"
_MODEL = "qwen3.5:9b"
_SCHEDULE_HOUR = 4   # 4:45 AM default
_MESH_NODES: dict = {}
_NODE_ID = "unknown"

# Last run results
_last_results: dict = {}
_last_run_ts: float = 0

ADVERSARIAL_PROMPT = """\
You are a red-team stress tester. Your job is to BREAK procedures by finding edge cases.

Given this procedure:
Task Type: {task_type}
Approach: {approach}
Confidence: {confidence}
Uses: {uses}

Generate exactly 3 edge cases where this procedure would FAIL.
For each:
1. The specific input/scenario that breaks it
2. WHY the procedure fails
3. Severity (low/medium/high)

Format:
EDGE_CASE: <scenario>
FAILURE: <why it breaks>
SEVERITY: <low|medium|high>

If truly unbreakable, say: UNBREAKABLE
Be ruthless.
"""


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


def _call_model(prompt: str, timeout: int = 60) -> Optional[str]:
    """Call inference for adversarial analysis."""
    try:
        payload = json.dumps({
            "model": _MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.8, "num_predict": 500},
        }).encode()
        req = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/generate", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        log.debug("[crucible] Model call failed: %s", e)
        return None


def _fetch_procedures(limit: int = 50) -> list[dict]:
    """Fetch procedures from local Bifrost."""
    try:
        url = f"http://127.0.0.1:8765/procedures?limit={limit}"
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read()).get("procedures", [])
    except Exception:
        return []


def run_crucible(dry_run: bool = False, limit: int = 20) -> dict:
    """Run adversarial stress-test on procedures."""
    global _last_results, _last_run_ts

    log.info("=== THE CRUCIBLE — Adversarial Procedure Test ===")
    stats = {"tested": 0, "broken": 0, "unbreakable": 0, "skipped": 0, "details": []}

    procs = _fetch_procedures(limit=limit)
    if not procs:
        log.info("[crucible] No procedures to test")
        stats["message"] = "No procedures available"
        _last_results = stats
        _last_run_ts = time.time()
        return stats

    # Sort by confidence descending
    procs.sort(key=lambda p: p.get("confidence", 0.5), reverse=True)

    for proc in procs[:limit]:
        task_type = proc.get("task_type", "unknown")
        approach = proc.get("approach", "")
        confidence = proc.get("confidence", 0.5)
        uses = proc.get("uses", 0)

        if not approach or len(approach) < 20:
            stats["skipped"] += 1
            continue

        # Heimdall: check for prompt injection in procedure text
        if check_prompt_injection:
            is_suspicious, patterns = check_prompt_injection(approach)
            if is_suspicious:
                log.warning("[crucible] Prompt injection in procedure '%s': %s",
                           task_type, patterns)
                stats["details"].append({
                    "task_type": task_type, "verdict": "injection_blocked",
                    "patterns": patterns,
                })
                stats["broken"] += 1
                stats["tested"] += 1
                continue

        prompt = ADVERSARIAL_PROMPT.format(
            task_type=task_type, approach=approach[:500],
            confidence=confidence, uses=uses,
        )
        result = _call_model(prompt)
        if not result:
            stats["skipped"] += 1
            continue

        stats["tested"] += 1

        if "UNBREAKABLE" in result.upper():
            stats["unbreakable"] += 1
            _publish("crucible.unbreakable", {"task_type": task_type})
            stats["details"].append({
                "task_type": task_type, "verdict": "unbreakable",
                "confidence": confidence,
            })
            continue

        high_count = result.upper().count("SEVERITY: HIGH")
        edge_count = result.upper().count("EDGE_CASE:")

        if edge_count == 0:
            stats["unbreakable"] += 1
            continue

        if high_count > 0:
            stats["broken"] += 1
            _publish("crucible.broken", {
                "task_type": task_type, "high_severity": high_count,
                "edge_cases": result[:500],
            })
            stats["details"].append({
                "task_type": task_type, "verdict": "broken",
                "high_severity": high_count, "edge_cases": result[:300],
            })
        else:
            _publish("crucible.tested", {"task_type": task_type})
            stats["details"].append({
                "task_type": task_type, "verdict": "stressed",
                "edge_count": edge_count,
            })

    stats["run_at"] = int(time.time())
    stats["dry_run"] = dry_run
    _last_results = stats
    _last_run_ts = time.time()

    log.info("[crucible] Done: tested=%d broken=%d unbreakable=%d",
             stats["tested"], stats["broken"], stats["unbreakable"])
    return stats


def _scheduler():
    """Background scheduler for nightly crucible runs."""
    time.sleep(120)  # Wait 2min after startup
    while True:
        now = datetime.now()
        if now.hour == _SCHEDULE_HOUR and now.minute >= 45 and now.minute < 55:
            if time.time() - _last_run_ts > 3600 * 6:
                log.info("[crucible] Scheduled run triggered")
                run_crucible()
        time.sleep(300)  # Check every 5 min


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    dry_run: bool = False
    limit: int = 20


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _OLLAMA_BASE, _MODEL, _SCHEDULE_HOUR, _MESH_NODES, _NODE_ID

    _NODE_ID = config.get("node", {}).get("name", "unknown")
    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MESH_NODES = config.get("mesh", {}).get("nodes", {})

    crucible_cfg = config.get("crucible", {})
    _SCHEDULE_HOUR = crucible_cfg.get("schedule_hour", 4)
    _MODEL = crucible_cfg.get("model", "qwen3.5:9b")

    providers = config.get("models", {}).get("providers", {})
    if "llama" in providers:
        url = providers["llama"].get("url", _OLLAMA_BASE)
        if "/v1" in url:
            url = url.rsplit("/v1", 1)[0]
        _OLLAMA_BASE = url

    router = APIRouter(tags=["crucible"])

    @router.post("/api/v1/crucible/run")
    async def api_run_crucible(req: RunRequest):
        return run_crucible(dry_run=req.dry_run, limit=req.limit)

    @router.get("/api/v1/crucible/results")
    async def api_get_results():
        return {
            "last_run": _last_results,
            "last_run_at": _last_run_ts,
            "schedule_hour": _SCHEDULE_HOUR,
        }

    app.include_router(router)

    # Start scheduler
    t = threading.Thread(target=_scheduler, daemon=True, name="crucible-scheduler")
    t.start()

    log.info("[crucible] Plugin loaded. Scheduled at %02d:45", _SCHEDULE_HOUR)

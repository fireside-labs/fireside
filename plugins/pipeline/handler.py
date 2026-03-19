"""
pipeline plugin — Multi-stage pipeline orchestrator for the Valhalla Mesh.

Ported from V1 bot/pipeline.py (637 lines).

Pipeline flow:
    Huginn spec → Build (parallel, local) → Test (Heimdall) → FAIL?
      → Huginn regression check (PROGRESS vs REGRESS)
      → PROGRESS → fix brief → rebuild → retest
      → REGRESS → escalate to human
    PASS → Muninn distills lessons → memory → SHIP

Key V2 changes:
    - Uses valhalla.yaml config for model URLs (not hardcoded constants)
    - Uses event-bus for inter-plugin communication
    - Stores pipeline state in war_room_data/pipelines/ JSON files
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("valhalla.pipeline")

# ---------------------------------------------------------------------------
# Config (set at register_routes)
# ---------------------------------------------------------------------------
_NODE_ID = "unknown"
_BASE_DIR = Path(".")
_MESH_NODES: dict = {}
_MODEL_PROVIDERS: dict = {}
_MODEL_ALIASES: dict = {}
_ROUTING: dict = {}

# Active pipelines: {pipeline_id: meta_dict}
_pipelines: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Heimdall's pipeline guard (Sprint 4 security)
# ---------------------------------------------------------------------------
try:
    from middleware.pipeline_guard import guard, check_prompt_injection
except ImportError:
    guard = None
    check_prompt_injection = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _publish(topic: str, payload: dict) -> None:
    """Publish to event bus."""
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


def _call_model(prompt: str, system: str = "", task_type: str = "build",
                timeout: int = 60, max_tokens: int = 1500) -> Optional[str]:
    """Call inference via the model appropriate for the task type.

    Uses model_router routing config to pick the right model.
    Falls back to default local model.
    """
    # Determine model from routing config
    model_ref = _ROUTING.get(task_type, _ROUTING.get("fallback", ""))

    # Parse model ref: "cloud/glm-5" or "local/default"
    if "/" in model_ref:
        provider_key, model_name = model_ref.split("/", 1)
    else:
        provider_key = "llama"
        model_name = model_ref or "default"

    # Resolve "default" to the actual model from aliases
    if model_name == "default":
        # Use the first provider's default
        for alias, ref in _MODEL_ALIASES.items():
            if ref:
                model_name = ref.split("/", 1)[-1] if "/" in ref else ref
                break

    provider = _MODEL_PROVIDERS.get(provider_key, {})
    url = provider.get("url", "http://127.0.0.1:8080/v1")

    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }).encode()

        req = urllib.request.Request(
            f"{url.rstrip('/')}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        # Add API key if present
        key = provider.get("key", "")
        if key and key != "local" and not key.startswith("$"):
            req.add_header("Authorization", f"Bearer {key}")

        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning("[pipeline] Model call failed (%s/%s): %s", provider_key, model_name, e)
        return None


def _parse_verdict(text: str) -> str:
    """Parse agent result into: pass, fail, ship, regress, or progress."""
    if not text:
        return "fail"
    upper = text.upper()

    # 1. Explicit VERDICT: line
    match = re.search(r'VERDICT:\s*(\w+)', upper)
    if match:
        v = match.group(1).lower()
        if v in ("pass", "ship", "fail", "regress", "progress"):
            return v

    # 2. Keyword fallback
    if "SHIP" in upper or "APPROVED" in upper:
        return "ship"
    if "PASS" in upper or "ALL TESTS PASS" in upper:
        return "pass"
    if "REGRESS" in upper:
        return "regress"
    if "PROGRESS" in upper:
        return "progress"
    return "fail"


def _pipeline_dir() -> Path:
    """Get pipeline storage directory."""
    d = _BASE_DIR / "war_room_data" / "pipelines"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_pipeline(pipeline_id: str, meta: dict) -> None:
    """Save pipeline state to JSON."""
    path = _pipeline_dir() / f"{pipeline_id}.json"
    path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")


def _load_pipeline(pipeline_id: str) -> Optional[dict]:
    """Load pipeline state from JSON."""
    path = _pipeline_dir() / f"{pipeline_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _load_all_pipelines() -> dict[str, dict]:
    """Load all pipeline states."""
    result = {}
    for f in _pipeline_dir().glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result[f.stem] = data
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Pipeline lifecycle
# ---------------------------------------------------------------------------

def create_pipeline(title: str, description: str, stages: list,
                    max_iterations: int = 3, posted_by: str = "odin") -> dict:
    """Create a new pipeline and start the first stage."""
    pipeline_id = f"pipe_{uuid.uuid4().hex[:8]}"
    ts = int(time.time())

    # Register with Heimdall's guard (enforces concurrency + iteration limits)
    if guard:
        guard.create_pipeline(
            pipeline_id, max_iterations=max_iterations,
            project_dir=_BASE_DIR,
        )

    meta = {
        "id": pipeline_id,
        "title": title,
        "description": description,
        "stages": stages,
        "current_stage": 0,
        "current_iteration": 0,
        "max_iterations": max_iterations,
        "status": "active",
        "created_at": ts,
        "created_by": posted_by,
        "history": [],
        "results": {},
    }

    _pipelines[pipeline_id] = meta
    _save_pipeline(pipeline_id, meta)

    _publish("pipeline.created", {
        "pipeline_id": pipeline_id,
        "title": title,
        "stages": len(stages),
        "max_iterations": max_iterations,
    })

    log.info("[pipeline] Created: %s (%d stages, max %d iterations)",
             pipeline_id, len(stages), max_iterations)

    # Start the first stage
    _start_stage(pipeline_id, meta)
    return meta


def _start_stage(pipeline_id: str, meta: dict) -> None:
    """Execute the current stage of the pipeline."""
    # Heimdall guard — check iteration limit + pipeline timeout
    if guard:
        try:
            guard.check_iteration(pipeline_id)
        except Exception as e:
            log.warning("[pipeline] Guard killed %s: %s", pipeline_id, e)
            meta["status"] = "killed"
            meta["kill_reason"] = str(e)
            _save_pipeline(pipeline_id, meta)
            _publish("pipeline.escalated", {
                "pipeline_id": pipeline_id, "reason": str(e),
            })
            return

    stage_idx = meta["current_stage"]
    if stage_idx >= len(meta["stages"]):
        _complete_pipeline(pipeline_id, meta)
        return

    stage = meta["stages"][stage_idx]
    stage_name = stage.get("name", f"stage_{stage_idx}")
    agent = stage.get("agent", "local")
    task_type = stage.get("task_type", "build")

    # Heimdall guard — mark stage start for timeout tracking
    if guard:
        guard.start_stage(pipeline_id, stage_name)

    log.info("[pipeline] Starting stage %d: %s (agent=%s)", stage_idx, stage_name, agent)

    # Build the prompt
    system = stage.get("system_prompt", f"You are executing stage '{stage_name}' of a pipeline.")
    prompt = stage.get("prompt", meta["description"])

    # Add previous stage results as context — structured and compressed
    prev_results = meta.get("results", {})
    if prev_results:
        prompt += "\n\n--- CONTEXT FROM PREVIOUS STAGES ---"
        for stage_key, stage_output in prev_results.items():
            # Compress each stage's output: keep first 1500 chars and last 500 chars
            if isinstance(stage_output, list):
                text = "\n".join(str(r) for r in stage_output[-3:])
            elif isinstance(stage_output, str):
                text = stage_output
            else:
                text = str(stage_output)

            # Smart truncation: keep beginning (spec/plan) and end (results/verdict)
            if len(text) > 2000:
                text = text[:1500] + "\n...[truncated]...\n" + text[-500:]

            prompt += f"\n\n[Stage '{stage_key}' output:]\n{text}"

        prompt += "\n--- END PREVIOUS CONTEXT ---\n"

    # Add iteration feedback if retrying
    if meta["current_iteration"] > 0:
        history = meta.get("history", [])
        if history:
            last = history[-1]
            prompt += f"\n\nThis is iteration {meta['current_iteration'] + 1}. " \
                      f"Previous verdict: {last.get('verdict', 'fail')}. " \
                      f"Feedback: {last.get('feedback', 'Fix the issues and try again.')}"

    # Call the model — handle parallel sub-stages (e.g. backend + frontend)
    if "parallel" in stage:
        # Parallel sub-stages: run each sequentially on single-GPU,
        # merge their outputs. On mesh, these dispatch to different nodes.
        sub_results = []
        for sub in stage["parallel"]:
            sub_system = sub.get("system_prompt",
                         f"You are a {sub.get('role', 'executor')} working on stage '{stage_name}'.")
            sub_prompt = sub.get("prompt", meta["description"])

            # Include the same previous context
            if prev_results:
                sub_prompt += "\n\n--- CONTEXT FROM PREVIOUS STAGES ---"
                for sk, sv in prev_results.items():
                    text = sv if isinstance(sv, str) else str(sv)
                    if len(text) > 1500:
                        text = text[:1000] + "\n...[truncated]...\n" + text[-500:]
                    sub_prompt += f"\n\n[Stage '{sk}' output:]\n{text}"
                sub_prompt += "\n--- END PREVIOUS CONTEXT ---\n"

            sub_task_type = sub.get("task_type", task_type)
            sub_result = _call_model(sub_prompt, system=sub_system,
                                     task_type=sub_task_type, timeout=120)
            if sub_result:
                sub_results.append({
                    "role": sub.get("role", "unknown"),
                    "output": sub_result,
                })
                log.info("[pipeline] Sub-stage '%s/%s' complete (%d chars)",
                         stage_name, sub.get("role", "?"), len(sub_result))

        # Merge parallel results
        if sub_results:
            merged = "\n\n".join(
                f"=== {r['role'].upper()} ===\n{r['output']}" for r in sub_results
            )
            result = merged
        else:
            result = None
    else:
        result = _call_model(prompt, system=system, task_type=task_type, timeout=120)

    if result:
        verdict = _parse_verdict(result)
        meta["results"][stage_name] = result
        meta["history"].append({
            "stage": stage_name,
            "iteration": meta["current_iteration"],
            "verdict": verdict,
            "result_preview": result[:500],
            "ts": int(time.time()),
        })

        _publish("pipeline.stage_complete", {
            "pipeline_id": pipeline_id,
            "stage": stage_name,
            "verdict": verdict,
            "iteration": meta["current_iteration"],
        })

        _advance(pipeline_id, meta, stage_name, verdict, result)
    else:
        # Model call failed — record and retry once
        meta["history"].append({
            "stage": stage_name,
            "iteration": meta["current_iteration"],
            "verdict": "error",
            "feedback": "Model call failed — no response",
            "ts": int(time.time()),
        })
        meta["status"] = "error"
        _save_pipeline(pipeline_id, meta)


def _advance(pipeline_id: str, meta: dict, stage_name: str,
             verdict: str, result: str) -> None:
    """Decide what to do based on stage verdict."""
    if verdict in ("pass", "ship"):
        # Move to next stage
        meta["current_stage"] += 1
        meta["current_iteration"] = 0
        log.info("[pipeline] Stage '%s' passed — advancing", stage_name)

        if meta["current_stage"] >= len(meta["stages"]):
            _complete_pipeline(pipeline_id, meta)
        else:
            _save_pipeline(pipeline_id, meta)
            _start_stage(pipeline_id, meta)

    elif verdict == "regress":
        _publish("pipeline.regression", {
            "pipeline_id": pipeline_id,
            "stage": stage_name,
            "iteration": meta["current_iteration"],
        })

        if meta["current_iteration"] >= meta["max_iterations"]:
            _escalate(pipeline_id, meta, result)
        else:
            log.warning("[pipeline] REGRESSION in '%s' — escalating", stage_name)
            _escalate(pipeline_id, meta, result)

    else:  # fail or progress
        meta["current_iteration"] += 1

        _publish("pipeline.iteration", {
            "pipeline_id": pipeline_id,
            "stage": stage_name,
            "iteration": meta["current_iteration"],
            "verdict": verdict,
        })

        if meta["current_iteration"] > meta["max_iterations"]:
            _escalate(pipeline_id, meta, result)
        else:
            log.info("[pipeline] Stage '%s' verdict=%s — iteration %d/%d",
                     stage_name, verdict, meta["current_iteration"], meta["max_iterations"])
            _save_pipeline(pipeline_id, meta)
            _start_stage(pipeline_id, meta)


def _complete_pipeline(pipeline_id: str, meta: dict) -> None:
    """Mark pipeline as shipped."""
    meta["status"] = "shipped"
    meta["completed_at"] = int(time.time())
    meta["total_iterations"] = sum(
        1 for h in meta.get("history", []) if h.get("verdict") in ("fail", "progress")
    )

    _save_pipeline(pipeline_id, meta)

    # Release Heimdall guard tracking
    if guard:
        guard.remove_pipeline(pipeline_id)

    _publish("pipeline.shipped", {
        "pipeline_id": pipeline_id,
        "title": meta.get("title", ""),
        "total_iterations": meta["total_iterations"],
        "duration_s": meta["completed_at"] - meta.get("created_at", meta["completed_at"]),
    })

    log.info("[pipeline] SHIPPED: %s (%d iterations)", pipeline_id, meta["total_iterations"])


def _escalate(pipeline_id: str, meta: dict, last_feedback: str) -> None:
    """Max iterations reached — escalate to human."""
    meta["status"] = "escalated"
    meta["escalated_at"] = int(time.time())
    meta["escalation_reason"] = last_feedback[:500]

    _save_pipeline(pipeline_id, meta)

    _publish("pipeline.escalated", {
        "pipeline_id": pipeline_id,
        "title": meta.get("title", ""),
        "reason": last_feedback[:200],
        "iterations": meta["current_iteration"],
    })

    log.warning("[pipeline] ESCALATED: %s after %d iterations",
                pipeline_id, meta["current_iteration"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CreatePipelineRequest(BaseModel):
    title: str
    description: str
    stages: list
    max_iterations: int = 3


class AdvanceRequest(BaseModel):
    action: str = "advance"  # "advance" or "retry"


# ---------------------------------------------------------------------------
# Git branching (Sprint 5)
# ---------------------------------------------------------------------------
_GIT_BRANCHING = False
_GIT_AUTO_MERGE = True
_GIT_BRANCH_PREFIX = "pipeline"


def _git_create_branch(pipeline_id: str, agent: str) -> bool:
    """Create a git branch for a pipeline stage dispatch."""
    if not _GIT_BRANCHING:
        return False
    import subprocess
    branch = f"{_GIT_BRANCH_PREFIX}/{pipeline_id}/{agent}"
    try:
        subprocess.run(
            ["git", "checkout", "-b", branch],
            cwd=str(_BASE_DIR), capture_output=True, timeout=10,
        )
        log.info("[pipeline] Created branch: %s", branch)
        return True
    except Exception as e:
        log.debug("[pipeline] Git branch failed: %s", e)
        return False


def _git_merge_branch(pipeline_id: str, agent: str) -> bool:
    """Merge a pipeline branch back to main after tests pass."""
    if not _GIT_BRANCHING or not _GIT_AUTO_MERGE:
        return False
    import subprocess
    branch = f"{_GIT_BRANCH_PREFIX}/{pipeline_id}/{agent}"
    try:
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=str(_BASE_DIR), capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "merge", "--no-ff", branch, "-m", f"Merge {branch} (pipeline auto-merge)"],
            cwd=str(_BASE_DIR), capture_output=True, timeout=10,
        )
        log.info("[pipeline] Merged branch: %s", branch)
        return True
    except Exception as e:
        log.debug("[pipeline] Git merge failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    """Called by plugin_loader."""
    global _NODE_ID, _BASE_DIR, _MESH_NODES, _MODEL_PROVIDERS, _MODEL_ALIASES, _ROUTING, _pipelines
    global _GIT_BRANCHING, _GIT_AUTO_MERGE, _GIT_BRANCH_PREFIX

    _NODE_ID = config.get("node", {}).get("name", "unknown")
    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MESH_NODES = config.get("mesh", {}).get("nodes", {})
    _MODEL_PROVIDERS = config.get("models", {}).get("providers", {})
    _MODEL_ALIASES = config.get("models", {}).get("aliases", {})
    _ROUTING = config.get("model_router", {}).get("routing", {
        "spec": "cloud/glm-5",
        "review": "cloud/glm-5",
        "build": "local/default",
        "test": "local/default",
        "memory": "cloud/kimi-k2.5",
        "fallback": "local/default",
    })

    # Git branching config
    pipe_cfg = config.get("pipeline", {})
    _GIT_BRANCHING = pipe_cfg.get("git_branching", False)
    _GIT_AUTO_MERGE = pipe_cfg.get("auto_merge", True)
    _GIT_BRANCH_PREFIX = pipe_cfg.get("branch_prefix", "pipeline")

    # Load any persisted pipelines
    _pipelines = _load_all_pipelines()

    router = APIRouter(tags=["pipeline"])

    @router.post("/api/v1/pipeline")
    async def api_create_pipeline(req: CreatePipelineRequest):
        """Create a new pipeline."""
        meta = create_pipeline(
            title=req.title,
            description=req.description,
            stages=req.stages,
            max_iterations=req.max_iterations,
        )
        return {"pipeline_id": meta["id"], "status": meta["status"]}

    @router.get("/api/v1/pipeline")
    async def api_list_pipelines():
        """List all pipelines."""
        all_pipes = _load_all_pipelines()
        return {
            "pipelines": [
                {
                    "id": pid,
                    "title": m.get("title", ""),
                    "status": m.get("status", "unknown"),
                    "current_stage": m.get("current_stage", 0),
                    "total_stages": len(m.get("stages", [])),
                    "current_iteration": m.get("current_iteration", 0),
                    "created_at": m.get("created_at"),
                }
                for pid, m in all_pipes.items()
            ],
            "count": len(all_pipes),
        }

    @router.get("/api/v1/pipeline/{pipeline_id}")
    async def api_get_pipeline(pipeline_id: str):
        """Get pipeline details."""
        meta = _load_pipeline(pipeline_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return meta

    @router.post("/api/v1/pipeline/{pipeline_id}/advance")
    async def api_advance_pipeline(pipeline_id: str, req: AdvanceRequest):
        """Manually advance or retry a pipeline."""
        meta = _load_pipeline(pipeline_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if meta["status"] not in ("active", "escalated", "error"):
            raise HTTPException(status_code=400, detail=f"Cannot advance: status is {meta['status']}")

        if req.action == "advance":
            meta["current_stage"] += 1
            meta["current_iteration"] = 0
            meta["status"] = "active"
        elif req.action == "retry":
            meta["status"] = "active"

        _pipelines[pipeline_id] = meta
        _save_pipeline(pipeline_id, meta)
        _start_stage(pipeline_id, meta)
        return {"ok": True, "status": meta["status"]}

    @router.delete("/api/v1/pipeline/{pipeline_id}")
    async def api_cancel_pipeline(pipeline_id: str):
        """Cancel a pipeline."""
        meta = _load_pipeline(pipeline_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        meta["status"] = "cancelled"
        meta["cancelled_at"] = int(time.time())
        _save_pipeline(pipeline_id, meta)
        _pipelines.pop(pipeline_id, None)
        # Release Heimdall guard
        if guard:
            guard.remove_pipeline(pipeline_id)
        return {"ok": True, "cancelled": pipeline_id}

    # Configure guard with pipeline settings
    if guard:
        guard.configure(config)

    app.include_router(router)
    log.info("[pipeline] Plugin loaded. %d persisted pipelines. Guard: %s, Git: %s",
             len(_pipelines), "active" if guard else "off",
             "on" if _GIT_BRANCHING else "off")

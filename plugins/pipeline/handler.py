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


def _resolve_model(task_type: str = "build") -> tuple[str, str]:
    """Resolve model provider URL and name from routing config."""
    model_ref = _ROUTING.get(task_type, _ROUTING.get("fallback", ""))
    if "/" in model_ref:
        provider_key, model_name = model_ref.split("/", 1)
    else:
        provider_key = "llama"
        model_name = model_ref or "default"

    if model_name == "default":
        for alias, ref in _MODEL_ALIASES.items():
            if ref:
                model_name = ref.split("/", 1)[-1] if "/" in ref else ref
                break

    provider = _MODEL_PROVIDERS.get(provider_key, {})
    url = provider.get("url", "http://127.0.0.1:8080/v1")
    key = provider.get("key", "")
    return url, model_name, key, provider_key


def _call_model(prompt: str, system: str = "", task_type: str = "build",
                timeout: int = 60, max_tokens: int = 1500,
                role: str = "") -> dict | None:
    """Call inference with full tool access (same tools as the main chat agent).

    Returns dict: {"text": str, "tokens_prompt": int, "tokens_completion": int,
                   "files_created": [str], "tools_used": [str]}
    or None on failure.
    """
    url, model_name, key, provider_key = _resolve_model(task_type)

    # Import shared tool system
    try:
        from tool_defs import get_tools_for_role, execute_tool
        tools = get_tools_for_role(role) if role else []
    except ImportError:
        tools = []
        execute_tool = None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    max_tool_rounds = 5  # Allow up to 5 rounds of tool use
    all_text = []
    total_prompt_tokens = 0
    total_completion_tokens = 0
    files_created: list[str] = []
    tools_used: list[str] = []

    for tool_round in range(max_tool_rounds + 1):
        try:
            payload_dict = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }
            # Include tools on all but the last round
            if tools and tool_round < max_tool_rounds:
                payload_dict["tools"] = tools

            payload = json.dumps(payload_dict).encode()
            req = urllib.request.Request(
                f"{url.rstrip('/')}/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            if key and key != "local" and not key.startswith("$"):
                req.add_header("Authorization", f"Bearer {key}")

            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())

            # Accumulate token usage
            usage = data.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)

            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content", "") or ""
            tool_calls = msg.get("tool_calls", [])

            if content:
                all_text.append(content)

            # If the model made tool calls, execute them and continue
            if tool_calls and execute_tool and tool_round < max_tool_rounds:
                log.info("[pipeline] Tool round %d: %d call(s) [role=%s]",
                         tool_round + 1, len(tool_calls), role)

                # Append assistant message with tool_calls
                messages.append(msg)

                for tc in tool_calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    try:
                        fn_args = json.loads(fn.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        fn_args = {}

                    result = execute_tool(fn_name, fn_args)
                    log.info("[pipeline]   %s → %s", fn_name, result[:80])
                    tools_used.append(fn_name)

                    # Track file creation
                    if fn_name in ("files_write", "create_pptx", "create_docx", "create_xlsx"):
                        created_path = fn_args.get("path", "")
                        if created_path and "Error" not in result and "BLOCKED" not in result:
                            files_created.append(created_path)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", f"call_{tool_round}"),
                        "content": result,
                    })

                continue  # Next round — model will see tool results

            # No tool calls (or final round) — we're done
            break

        except Exception as e:
            log.warning("[pipeline] Model call failed (%s/%s): %s", provider_key, model_name, e)
            return None

    result_text = "\n\n".join(all_text).strip()
    if not result_text:
        return None

    return {
        "text": result_text,
        "tokens_prompt": total_prompt_tokens,
        "tokens_completion": total_completion_tokens,
        "files_created": files_created,
        "tools_used": tools_used,
    }


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
        "token_usage": {"prompt": 0, "completion": 0},
        "stage_times": [],
        "files_created": [],
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

    # Start the first stage in a background thread so the API returns immediately
    import threading
    threading.Thread(
        target=_start_stage, args=(pipeline_id, meta),
        name=f"pipeline-{pipeline_id[:8]}", daemon=True,
    ).start()
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

    stage_start_ts = int(time.time())
    log.info("[pipeline] Starting stage %d: %s (agent=%s)", stage_idx, stage_name, agent)

    # Publish stage started event for real-time dashboard updates
    _publish("pipeline.stage_started", {
        "pipeline_id": pipeline_id,
        "stage": stage_name,
        "stage_index": stage_idx,
        "total_stages": len(meta["stages"]),
        "iteration": meta["current_iteration"],
    })

    # ── Gate stage: pause for human approval ──
    if stage.get("type") == "gate":
        meta["status"] = "waiting_approval"
        meta["gate_prompt"] = stage.get("prompt", "Approval required to continue.")
        meta["gate_stage"] = stage_name
        _save_pipeline(pipeline_id, meta)
        _publish("pipeline.gate_waiting", {
            "pipeline_id": pipeline_id,
            "stage": stage_name,
            "stage_index": stage_idx,
            "total_stages": len(meta["stages"]),
            "prompt": meta["gate_prompt"],
            "title": meta.get("title", ""),
        })
        log.info("[pipeline] Gate pause at stage '%s' — waiting for approval", stage_name)
        return  # Stop here — resume when user approves

    # Build the prompt
    try:
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
                sub_role = sub.get("role", "executor")
                sub_result = _call_model(sub_prompt, system=sub_system,
                                         task_type=sub_task_type, timeout=120,
                                         role=sub_role)
                if sub_result:
                    sub_results.append({
                        "role": sub.get("role", "unknown"),
                        "output": sub_result["text"],
                    })
                    # Accumulate tokens and files from sub-stages
                    meta["token_usage"]["prompt"] += sub_result.get("tokens_prompt", 0)
                    meta["token_usage"]["completion"] += sub_result.get("tokens_completion", 0)
                    meta["files_created"].extend(sub_result.get("files_created", []))
                    log.info("[pipeline] Sub-stage '%s/%s' complete (%d chars)",
                             stage_name, sub.get("role", "?"), len(sub_result["text"]))

            # Merge parallel results
            if sub_results:
                merged = "\n\n".join(
                    f"=== {r['role'].upper()} ===\n{r['output']}" for r in sub_results
                )
                result_text = merged
            else:
                result_text = None
        else:
            stage_role = stage.get("role", stage.get("agent", "executor"))
            model_result = _call_model(prompt, system=system, task_type=task_type,
                                       timeout=120, role=stage_role)
            if model_result:
                result_text = model_result["text"]
                meta["token_usage"]["prompt"] += model_result.get("tokens_prompt", 0)
                meta["token_usage"]["completion"] += model_result.get("tokens_completion", 0)
                meta["files_created"].extend(model_result.get("files_created", []))
            else:
                result_text = None

        # Calculate stage duration and ETA
        stage_duration = int(time.time()) - stage_start_ts
        meta["stage_times"].append(stage_duration)
        avg_stage_time = sum(meta["stage_times"]) / len(meta["stage_times"])
        remaining_stages = len(meta["stages"]) - stage_idx - 1
        eta_seconds = int(avg_stage_time * remaining_stages)
        meta["eta_seconds"] = eta_seconds
        meta["eta_minutes"] = round(eta_seconds / 60, 1)

        if result_text:
            verdict = _parse_verdict(result_text)
            meta["results"][stage_name] = result_text
            meta["history"].append({
                "stage": stage_name,
                "iteration": meta["current_iteration"],
                "verdict": verdict,
                "result_preview": result_text[:500],
                "duration_s": stage_duration,
                "ts": int(time.time()),
            })

            _publish("pipeline.stage_complete", {
                "pipeline_id": pipeline_id,
                "stage": stage_name,
                "stage_index": stage_idx,
                "total_stages": len(meta["stages"]),
                "verdict": verdict,
                "iteration": meta["current_iteration"],
                "duration_s": stage_duration,
                "eta_seconds": eta_seconds,
                "tokens": meta["token_usage"],
            })

            # Publish file-created events for dashboard toast notifications
            for fpath in meta.get("files_created", []):
                _publish("pipeline.file_created", {
                    "pipeline_id": pipeline_id,
                    "stage": stage_name,
                    "path": fpath,
                    "title": meta.get("title", ""),
                })
            # Clear files list after publishing (avoid re-publishing on retry)
            meta["files_created"] = []

            _advance(pipeline_id, meta, stage_name, verdict, result_text)
        else:
            # Model call failed — record and retry once
            meta["history"].append({
                "stage": stage_name,
                "iteration": meta["current_iteration"],
                "verdict": "error",
                "feedback": "Model call failed — no response",
                "duration_s": stage_duration,
                "ts": int(time.time()),
            })
            meta["status"] = "error"
            _save_pipeline(pipeline_id, meta)

    except Exception as exc:
        log.error("[pipeline] Stage '%s' crashed: %s", stage_name, exc)
        meta["history"].append({
            "stage": stage_name,
            "iteration": meta["current_iteration"],
            "verdict": "error",
            "feedback": f"Stage execution crashed: {exc}",
            "ts": int(time.time()),
        })
        meta["status"] = "error"
        _pipelines[pipeline_id] = meta
        _save_pipeline(pipeline_id, meta)


def _advance(pipeline_id: str, meta: dict, stage_name: str,
             verdict: str, result: str) -> None:
    """Decide what to do based on stage verdict.

    Supports on_fail routing:
      - "retry" (default): retry current stage
      - "goto:stage_name": jump to a different stage
      - "escalate": immediately escalate to human
    """
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
            return

        # Check on_fail routing from the stage definition
        stage_def = meta["stages"][meta["current_stage"]] if meta["current_stage"] < len(meta["stages"]) else {}
        on_fail = stage_def.get("on_fail", "retry")

        if on_fail.startswith("goto:"):
            target_name = on_fail[5:]
            # Find the target stage index
            stage_names = [s.get("name", "") for s in meta["stages"]]
            if target_name in stage_names:
                target_idx = stage_names.index(target_name)
                log.info("[pipeline] on_fail goto '%s' (stage %d) from '%s'",
                         target_name, target_idx, stage_name)
                meta["current_stage"] = target_idx
                meta["current_iteration"] = 0  # Reset iteration for the target stage
                _save_pipeline(pipeline_id, meta)
                _start_stage(pipeline_id, meta)
            else:
                log.warning("[pipeline] on_fail target '%s' not found — retrying current", target_name)
                _save_pipeline(pipeline_id, meta)
                _start_stage(pipeline_id, meta)
        elif on_fail == "escalate":
            _escalate(pipeline_id, meta, result)
        else:  # "retry" or default
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
    meta["eta_seconds"] = 0
    meta["eta_minutes"] = 0

    _save_pipeline(pipeline_id, meta)

    # Release Heimdall guard tracking
    if guard:
        guard.remove_pipeline(pipeline_id)

    duration_s = meta["completed_at"] - meta.get("created_at", meta["completed_at"])
    tokens = meta.get("token_usage", {})

    _publish("pipeline.shipped", {
        "pipeline_id": pipeline_id,
        "title": meta.get("title", ""),
        "total_iterations": meta["total_iterations"],
        "duration_s": duration_s,
        "tokens": tokens,
        "files_created": meta.get("files_created", []),
    })

    log.info("[pipeline] SHIPPED: %s (%d iterations, %ds, %d tokens)",
             pipeline_id, meta["total_iterations"], duration_s,
             tokens.get("prompt", 0) + tokens.get("completion", 0))


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
    description: str = ""
    stages: list
    max_iterations: int = 3


class AdvanceRequest(BaseModel):
    action: str = "advance"  # "advance" or "retry"


class InterventionRequest(BaseModel):
    guidance: str  # Human guidance to inject into the current stage


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
                    "eta_minutes": m.get("eta_minutes", 0),
                    "token_usage": m.get("token_usage", {}),
                    "files_created": m.get("files_created", []),
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
        import threading
        threading.Thread(target=_start_stage, args=(pipeline_id, meta), daemon=True).start()
        return {"ok": True, "status": meta["status"]}

    @router.post("/api/v1/pipeline/{pipeline_id}/intervene")
    async def api_intervene_pipeline(pipeline_id: str, req: InterventionRequest):
        """Inject human guidance into the current stage of a running pipeline."""
        meta = _load_pipeline(pipeline_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if meta["status"] not in ("active", "escalated", "waiting_approval"):
            raise HTTPException(status_code=400, detail=f"Cannot intervene: status is {meta['status']}")

        # Add guidance to history so the next stage iteration sees it
        meta["history"].append({
            "stage": meta["stages"][meta["current_stage"]].get("name", "unknown") if meta["current_stage"] < len(meta["stages"]) else "unknown",
            "iteration": meta["current_iteration"],
            "verdict": "human_guidance",
            "feedback": req.guidance,
            "ts": int(time.time()),
        })

        # If escalated, restart the current stage with human context
        if meta["status"] == "escalated":
            meta["status"] = "active"

        _pipelines[pipeline_id] = meta
        _save_pipeline(pipeline_id, meta)

        _publish("pipeline.human_intervention", {
            "pipeline_id": pipeline_id,
            "guidance": req.guidance[:200],
            "stage": meta["stages"][meta["current_stage"]].get("name", "unknown") if meta["current_stage"] < len(meta["stages"]) else "unknown",
        })

        # Restart current stage with the new guidance injected
        import threading
        threading.Thread(target=_start_stage, args=(pipeline_id, meta), daemon=True).start()
        return {"ok": True, "status": "intervention_applied"}

    @router.post("/api/v1/pipeline/{pipeline_id}/approve")
    async def api_approve_pipeline(pipeline_id: str):
        """Approve a gate stage — pipeline continues to next stage."""
        meta = _load_pipeline(pipeline_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if meta["status"] != "waiting_approval":
            raise HTTPException(status_code=400, detail=f"Pipeline not at a gate: status is {meta['status']}")

        stage_idx = meta["current_stage"]
        stage_name = meta.get("gate_stage", "unknown")

        # Record gate approval in history
        meta["history"].append({
            "stage": stage_name,
            "iteration": meta["current_iteration"],
            "verdict": "gate_approved",
            "feedback": "",
            "ts": int(time.time()),
        })

        # Record stage completion time
        stage_start = meta.get("stage_start_ts", int(time.time()))
        duration = int(time.time()) - stage_start
        meta["stage_times"].append(duration)

        # Advance past gate
        meta["status"] = "active"
        meta["current_stage"] += 1
        meta["current_iteration"] = 0
        meta.pop("gate_prompt", None)
        meta.pop("gate_stage", None)

        _pipelines[pipeline_id] = meta
        _save_pipeline(pipeline_id, meta)

        _publish("pipeline.gate_approved", {
            "pipeline_id": pipeline_id,
            "stage": stage_name,
            "stage_index": stage_idx,
        })

        log.info("[pipeline] Gate approved: %s stage '%s'", pipeline_id, stage_name)
        import threading
        threading.Thread(target=_start_stage, args=(pipeline_id, meta), daemon=True).start()
        return {"ok": True, "status": "approved"}

    @router.post("/api/v1/pipeline/{pipeline_id}/reject")
    async def api_reject_pipeline(pipeline_id: str):
        """Reject a gate stage — triggers on_fail routing."""
        meta = _load_pipeline(pipeline_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if meta["status"] != "waiting_approval":
            raise HTTPException(status_code=400, detail=f"Pipeline not at a gate: status is {meta['status']}")

        stage_idx = meta["current_stage"]
        stage = meta["stages"][stage_idx] if stage_idx < len(meta["stages"]) else {}
        stage_name = meta.get("gate_stage", "unknown")

        # Record gate rejection in history
        meta["history"].append({
            "stage": stage_name,
            "iteration": meta["current_iteration"],
            "verdict": "gate_rejected",
            "feedback": "Gate rejected by user",
            "ts": int(time.time()),
        })
        meta.pop("gate_prompt", None)
        meta.pop("gate_stage", None)

        _publish("pipeline.gate_rejected", {
            "pipeline_id": pipeline_id,
            "stage": stage_name,
            "stage_index": stage_idx,
        })

        # Follow on_fail routing
        on_fail = stage.get("on_fail", "escalate")
        if on_fail.startswith("goto:"):
            target_name = on_fail[5:]
            stage_names = [s.get("name", "") for s in meta["stages"]]
            if target_name in stage_names:
                meta["current_stage"] = stage_names.index(target_name)
                meta["current_iteration"] = 0
                meta["status"] = "active"
                _pipelines[pipeline_id] = meta
                _save_pipeline(pipeline_id, meta)
                import threading
                threading.Thread(target=_start_stage, args=(pipeline_id, meta), daemon=True).start()
                return {"ok": True, "status": "rejected_goto", "target": target_name}
        elif on_fail == "retry":
            meta["status"] = "active"
            _pipelines[pipeline_id] = meta
            _save_pipeline(pipeline_id, meta)
            import threading
            threading.Thread(target=_start_stage, args=(pipeline_id, meta), daemon=True).start()
            return {"ok": True, "status": "rejected_retry"}

        # Default: escalate
        _escalate(pipeline_id, meta, "Gate rejected by user")
        return {"ok": True, "status": "rejected_escalated"}

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

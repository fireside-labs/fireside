"""
pipeline.py -- Multi-stage pipeline orchestrator for the Valhalla Mesh.

Pipelines chain tasks through stages with conditional routing:

    Odin/Ravens (plan) → Thor+Freya (build parallel) → Heimdall (QA) → iterate → ship

Each pipeline is a parent task with child subtasks. The pipeline executor
runs each poll cycle, checking for completed subtasks and advancing to
the next stage or looping back on failure.

Usage:
    POST /war-room/pipeline {title, description, stages, max_iterations}
"""

import json
import logging
import os
import re
import time
import urllib.request
import urllib.error

log = logging.getLogger("pipeline")

LOCAL_BIFROST = os.environ.get("DISPATCH_LOCAL_BIFROST", "http://127.0.0.1:8765")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post(url: str, data: dict, timeout: int = 10) -> dict:
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


def _parse_result(text: str) -> str:
    """Parse agent result text into a verdict: pass, fail, or ship.

    Uses keyword detection on the result. Agents are instructed in their
    dispatch to use these keywords explicitly.
    """
    t = text.lower().strip()

    # Check for explicit verdicts first
    if re.search(r'\b(ship|lgtm|approved|all\s+(?:tests?\s+)?pass)', t):
        return "pass"
    if re.search(r'\b(fail|bug|error|broken|syntax\s+error|crash)', t):
        return "fail"
    if re.search(r'\bpass\b', t):
        return "pass"

    # Default: treat as feedback (needs iteration)
    return "fail"


# ---------------------------------------------------------------------------
# Pipeline creation
# ---------------------------------------------------------------------------

def create_pipeline(title: str, description: str, stages: list,
                    max_iterations: int = 3, posted_by: str = "odin") -> dict:
    """Create a pipeline parent task and kick off the first stage.

    Args:
        title: Human-readable pipeline name
        description: What should be built
        stages: List of stage defs, e.g.:
            [
              {"name": "build", "parallel": [
                  {"agent": "thor",  "description": "..."},
                  {"agent": "freya", "description": "..."},
              ]},
              {"name": "test", "agent": "heimdall", "description": "..."},
            ]
        max_iterations: Max feedback loops before escalation
        posted_by: Who created the pipeline

    Returns:
        The parent pipeline task dict.
    """
    # Create the parent pipeline task
    parent = _post(f"{LOCAL_BIFROST}/war-room/task", {
        "title": f"[pipeline] {title}",
        "description": description,
        "posted_by": posted_by,
        "assigned_to": "odin",
    })
    parent_id = parent.get("id") or parent.get("task_id")

    # Store pipeline metadata on the parent task
    meta = {
        "pipeline": True,
        "stages": stages,
        "max_iterations": max_iterations,
        "current_stage": 0,
        "iteration": 0,
        "stage_history": [],
    }

    # Save pipeline metadata as a sidecar file
    _save_pipeline_meta(parent_id, meta)

    log.info("Created pipeline %s: %s (%d stages, max %d iterations)",
             parent_id[:14], title, len(stages), max_iterations)

    # Kick off first stage
    _start_stage(parent_id, meta, description)

    return parent


def _save_pipeline_meta(pipeline_id: str, meta: dict):
    """Save pipeline metadata to a JSON sidecar file."""
    from pathlib import Path
    meta_dir = Path(os.environ.get("PIPELINE_DIR",
                    os.path.expanduser("~/.openclaw/workspace/bot/bot/pipelines")))
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta_path = meta_dir / f"{pipeline_id}.json"
    meta_path.write_text(json.dumps(meta, indent=2))


def _load_pipeline_meta(pipeline_id: str) -> dict | None:
    """Load pipeline metadata from sidecar file."""
    from pathlib import Path
    meta_dir = Path(os.environ.get("PIPELINE_DIR",
                    os.path.expanduser("~/.openclaw/workspace/bot/bot/pipelines")))
    meta_path = meta_dir / f"{pipeline_id}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return None


def _get_active_pipelines() -> list[str]:
    """Get IDs of all active pipelines (have sidecar files)."""
    from pathlib import Path
    meta_dir = Path(os.environ.get("PIPELINE_DIR",
                    os.path.expanduser("~/.openclaw/workspace/bot/bot/pipelines")))
    if not meta_dir.exists():
        return []
    return [f.stem for f in meta_dir.glob("*.json")]


# ---------------------------------------------------------------------------
# Stage execution
# ---------------------------------------------------------------------------

def _start_stage(pipeline_id: str, meta: dict, project_description: str,
                 prev_results: list[str] | None = None):
    """Create subtask(s) for the current stage and dispatch them."""
    stage_idx = meta["current_stage"]
    if stage_idx >= len(meta["stages"]):
        log.info("Pipeline %s: all stages complete!", pipeline_id[:14])
        _complete_pipeline(pipeline_id, meta)
        return

    stage = meta["stages"][stage_idx]
    stage_name = stage.get("name", f"stage-{stage_idx}")
    iteration = meta["iteration"]

    # Build context from previous results
    context = f"Project: {project_description}\n"
    if prev_results:
        context += "\n--- Previous stage feedback ---\n"
        context += "\n".join(prev_results)
        context += "\n--- End feedback ---\n"
    context += f"\nFirst do: git pull origin main\n"

    if "parallel" in stage:
        # Fan-out: create one subtask per parallel agent
        for p in stage["parallel"]:
            agent = p["agent"]
            desc = p.get("description", f"Complete {stage_name} phase")
            task_desc = f"{context}\nYour task: {desc}"

            # Add result format instruction
            task_desc += _result_format_instruction(stage_name)

            _post(f"{LOCAL_BIFROST}/war-room/task", {
                "title": f"[{pipeline_id[:8]}] {stage_name}/{agent} (iter {iteration})",
                "description": task_desc,
                "assigned_to": agent,
                "posted_by": "odin",
                "parent_id": pipeline_id,
            })
            log.info("  Pipeline %s → stage '%s' dispatched to %s",
                     pipeline_id[:14], stage_name, agent)
    else:
        # Sequential: single agent
        agent = stage["agent"]
        desc = stage.get("description", f"Complete {stage_name} phase")
        task_desc = f"{context}\nYour task: {desc}"
        task_desc += _result_format_instruction(stage_name)

        _post(f"{LOCAL_BIFROST}/war-room/task", {
            "title": f"[{pipeline_id[:8]}] {stage_name}/{agent} (iter {iteration})",
            "description": task_desc,
            "assigned_to": agent,
            "posted_by": "odin",
            "parent_id": pipeline_id,
        })
        log.info("  Pipeline %s → stage '%s' dispatched to %s",
                 pipeline_id[:14], stage_name, agent)


def _result_format_instruction(stage_name: str) -> str:
    """Append explicit result format instructions based on stage type."""
    if stage_name == "test":
        return (
            "\n\n---\nRESULT FORMAT: End your response with exactly one of:\n"
            "  VERDICT: PASS  (if all tests pass and code works)\n"
            "  VERDICT: FAIL  (if there are bugs — list each bug)\n"
            "Be specific about which files and lines have issues."
        )
    elif stage_name == "review":
        return (
            "\n\n---\nRESULT FORMAT: End your response with exactly one of:\n"
            "  VERDICT: SHIP  (if code quality is acceptable)\n"
            "  VERDICT: IMPROVE  (list specific improvements needed)\n"
        )
    else:
        return (
            "\n\n---\nRESULT FORMAT: After completing your work, report:\n"
            "  FILES: <list of files you created or modified>\n"
            "  STATUS: DONE\n"
        )


# ---------------------------------------------------------------------------
# Pipeline advancement (called each poll cycle)
# ---------------------------------------------------------------------------

def check_pipelines():
    """Check all active pipelines for completed stages and advance them.

    Called by the dispatcher on each poll cycle.
    """
    pipeline_ids = _get_active_pipelines()
    if not pipeline_ids:
        return

    # Fetch all tasks
    try:
        all_tasks = _get(f"{LOCAL_BIFROST}/war-room/tasks")
        if isinstance(all_tasks, dict):
            all_tasks = all_tasks.get("tasks", [])
    except Exception as e:
        log.warning("Pipeline check failed to fetch tasks: %s", e)
        return

    for pid in pipeline_ids:
        meta = _load_pipeline_meta(pid)
        if not meta:
            continue

        # Find subtasks for this pipeline's current stage
        stage_idx = meta["current_stage"]
        if stage_idx >= len(meta["stages"]):
            continue

        stage = meta["stages"][stage_idx]
        stage_name = stage.get("name", f"stage-{stage_idx}")

        # Get child tasks that belong to this pipeline
        children = [t for t in all_tasks
                     if t.get("parent_id") == pid
                     and f"[{pid[:8]}] {stage_name}/" in t.get("title", "")]

        if not children:
            continue

        # Check if all children for this stage are done
        all_done = all(t.get("status") == "done" for t in children)
        if not all_done:
            continue

        # Collect results from completed stage
        results = [t.get("result", "") for t in children]
        agents = [t.get("assigned_to", "unknown") for t in children]

        log.info("Pipeline %s: stage '%s' complete (%d subtasks)",
                 pid[:14], stage_name, len(children))

        # Record in history
        meta["stage_history"].append({
            "stage": stage_name,
            "iteration": meta["iteration"],
            "agents": agents,
            "results": [r[:200] for r in results],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

        # Get the parent task for project description
        parent = next((t for t in all_tasks if t.get("id") == pid), {})
        project_desc = parent.get("description", "")

        # Advance the pipeline
        _advance(pid, meta, stage_name, results, project_desc)


def _advance(pipeline_id: str, meta: dict, stage_name: str,
             results: list[str], project_desc: str):
    """Decide what to do next based on stage results."""

    combined_result = "\n".join(results)
    verdict = _parse_result(combined_result)

    if stage_name in ("test", "review"):
        if verdict == "pass":
            # Advance to next stage
            meta["current_stage"] += 1
            meta["iteration"] = 0  # reset iteration for new stage
            _save_pipeline_meta(pipeline_id, meta)
            _start_stage(pipeline_id, meta, project_desc)
        else:
            # Feedback loop — go back to build stage
            meta["iteration"] += 1
            if meta["iteration"] > meta["max_iterations"]:
                log.warning("Pipeline %s: max iterations reached! Escalating.",
                            pipeline_id[:14])
                _escalate(pipeline_id, meta, combined_result)
                return

            # Loop back to the build stage (stage 0)
            meta["current_stage"] = 0
            _save_pipeline_meta(pipeline_id, meta)

            log.info("Pipeline %s: %s stage FAILED (iter %d/%d), looping back",
                     pipeline_id[:14], stage_name,
                     meta["iteration"], meta["max_iterations"])

            _start_stage(pipeline_id, meta, project_desc,
                         prev_results=results)
    else:
        # Build/plan stage completed — move to next stage
        meta["current_stage"] += 1
        _save_pipeline_meta(pipeline_id, meta)
        _start_stage(pipeline_id, meta, project_desc, prev_results=results)


def _complete_pipeline(pipeline_id: str, meta: dict):
    """Mark pipeline as done and clean up."""
    log.info("Pipeline %s SHIPPED! (%d iterations total)",
             pipeline_id[:14], meta["iteration"])

    # Complete the parent task
    try:
        history_summary = "\n".join(
            f"  [{h['stage']}] iter {h['iteration']}: {', '.join(h['agents'])}"
            for h in meta["stage_history"]
        )
        _post(f"{LOCAL_BIFROST}/war-room/complete", {
            "task_id": pipeline_id,
            "agent_id": "odin",
            "result": f"Pipeline complete!\n\nStage history:\n{history_summary}",
        })
    except Exception as e:
        log.error("Failed to complete pipeline %s: %s", pipeline_id[:14], e)

    # Post a War Room message
    try:
        _post(f"{LOCAL_BIFROST}/war-room/message", {
            "from": "odin",
            "to": "all",
            "type": "announcement",
            "subject": f"Pipeline shipped: {pipeline_id[:14]}",
            "body": f"Pipeline {pipeline_id} completed after "
                    f"{meta['iteration']} iteration(s). Check git log for deliverables.",
        })
    except Exception:
        pass

    # Remove sidecar file
    from pathlib import Path
    meta_dir = Path(os.environ.get("PIPELINE_DIR",
                    os.path.expanduser("~/.openclaw/workspace/bot/bot/pipelines")))
    meta_path = meta_dir / f"{pipeline_id}.json"
    if meta_path.exists():
        meta_path.unlink()


def _escalate(pipeline_id: str, meta: dict, last_feedback: str):
    """Max iterations reached — escalate to human."""
    log.warning("Pipeline %s: ESCALATING to Odin (max iterations)",
                pipeline_id[:14])

    try:
        _post(f"{LOCAL_BIFROST}/war-room/message", {
            "from": "odin",
            "to": "odin",
            "type": "alert",
            "subject": f"Pipeline {pipeline_id[:14]} needs human review",
            "body": f"Max iterations ({meta['max_iterations']}) reached.\n\n"
                    f"Last feedback:\n{last_feedback[:500]}",
        })
    except Exception:
        pass

    # Remove sidecar file — pipeline is dead
    from pathlib import Path
    meta_dir = Path(os.environ.get("PIPELINE_DIR",
                    os.path.expanduser("~/.openclaw/workspace/bot/bot/pipelines")))
    meta_path = meta_dir / f"{pipeline_id}.json"
    if meta_path.exists():
        meta_path.unlink()
""",
<parameter name="Complexity">8

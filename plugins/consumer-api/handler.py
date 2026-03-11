"""
consumer-api plugin — Consumer-friendly API responses for Valhalla Mesh.

Sprint 6: Backend changes to support the consumer UX.

Endpoints:
  GET /api/v1/system/hardware     — Device name, GPU, VRAM, RAM, CPU + model recs
  GET /api/v1/friendly/nodes      — Nodes with consumer-friendly labels
  GET /api/v1/friendly/pipeline   — Pipelines with plain-English step descriptions
  GET /api/v1/friendly/personality — Personality as form-friendly fields
  GET /api/v1/activity/today      — "Answered 12 questions, read 3 files"
  GET /api/v1/learning/summary    — "Things it knows: 247, Reliable: 94%"
"""
from __future__ import annotations

import json
import logging
import os
import platform
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.consumer-api")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_NODE_ID = "unknown"
_BASE_DIR = Path(".")
_MESH_NODES: dict = {}
_MODEL_PROVIDERS: dict = {}
_MODEL_ALIASES: dict = {}
_SOUL_CONFIG: dict = {}

# Activity tracking — in-memory counters reset daily
_activity_lock = threading.Lock()
_activity: dict = {
    "questions_answered": 0,
    "files_read": 0,
    "things_learned": 0,
    "tasks_completed": 0,
    "debates_held": 0,
    "last_reset": 0,
}


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Hardware detection
# ---------------------------------------------------------------------------

# Model VRAM requirements (GB)
MODEL_VRAM_REQUIREMENTS = {
    "llama-3.1-8b": {"min_vram_gb": 6, "recommended_vram_gb": 8, "label": "Llama 3.1 8B"},
    "llama-3.1-70b": {"min_vram_gb": 40, "recommended_vram_gb": 48, "label": "Llama 3.1 70B"},
    "mistral-7b": {"min_vram_gb": 5, "recommended_vram_gb": 8, "label": "Mistral 7B"},
    "qwen-2.5-14b": {"min_vram_gb": 10, "recommended_vram_gb": 16, "label": "Qwen 2.5 14B"},
    "deepseek-r1": {"min_vram_gb": 4, "recommended_vram_gb": 8, "label": "DeepSeek R1"},
    "phi-3-mini": {"min_vram_gb": 3, "recommended_vram_gb": 4, "label": "Phi-3 Mini"},
    "gemma-2-9b": {"min_vram_gb": 6, "recommended_vram_gb": 8, "label": "Gemma 2 9B"},
}


def detect_hardware() -> dict:
    """Detect local hardware: device name, GPU, VRAM, RAM, CPU."""
    info = {
        "device_name": platform.node() or "Unknown Device",
        "os": platform.system(),
        "os_version": platform.mac_ver()[0] if platform.system() == "Darwin" else platform.version(),
        "cpu": _detect_cpu(),
        "cpu_cores": os.cpu_count() or 0,
        "ram_gb": _detect_ram_gb(),
        "gpu": _detect_gpu(),
        "vram_gb": _detect_vram_gb(),
    }

    # Friendly device name
    user = os.environ.get("USER", os.environ.get("USERNAME", ""))
    if user:
        info["friendly_name"] = f"{user.capitalize()}'s {_friendly_device_type()}"
    else:
        info["friendly_name"] = info["device_name"]

    # Model compatibility
    vram = info["vram_gb"]
    info["recommended_model"] = _recommend_model(vram)
    info["compatible_models"] = _compatible_models(vram)

    return info


def _detect_cpu() -> str:
    """Detect CPU model."""
    try:
        if platform.system() == "Darwin":
            r = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() or platform.processor()
        return platform.processor() or "Unknown"
    except Exception:
        return platform.processor() or "Unknown"


def _detect_ram_gb() -> float:
    """Detect total RAM in GB."""
    try:
        if platform.system() == "Darwin":
            r = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5,
            )
            return round(int(r.stdout.strip()) / (1024**3), 1)
        # Linux fallback
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    return round(kb / (1024**2), 1)
    except Exception:
        pass
    return 0.0


def _detect_gpu() -> str:
    """Detect GPU model."""
    try:
        if platform.system() == "Darwin":
            r = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=10,
            )
            for line in r.stdout.splitlines():
                if "Chipset Model" in line or "Chip" in line:
                    return line.split(":", 1)[-1].strip()
            # Apple Silicon — check for unified memory
            r2 = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            cpu = r2.stdout.strip()
            if "Apple" in cpu:
                return cpu  # e.g., "Apple M2 Pro"
        # nvidia-smi fallback
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return "Unknown GPU"


def _detect_vram_gb() -> float:
    """Detect VRAM (or unified memory on Apple Silicon)."""
    try:
        if platform.system() == "Darwin":
            # Apple Silicon uses unified memory — report RAM as VRAM
            r = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5,
            )
            if "Apple" in r.stdout:
                return _detect_ram_gb()  # Unified memory
        # nvidia-smi
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            mb = int(r.stdout.strip().split("\n")[0])
            return round(mb / 1024, 1)
    except Exception:
        pass
    return 0.0


def _friendly_device_type() -> str:
    """Friendly device type name."""
    system = platform.system()
    if system == "Darwin":
        # Check if laptop or desktop
        try:
            r = subprocess.run(
                ["sysctl", "-n", "hw.model"],
                capture_output=True, text=True, timeout=5,
            )
            model = r.stdout.strip().lower()
            if "book" in model:
                return "MacBook"
            if "mini" in model:
                return "Mac Mini"
            if "pro" in model or "studio" in model:
                return "Mac Studio"
            return "Mac"
        except Exception:
            return "Mac"
    elif system == "Linux":
        return "Linux PC"
    return "Computer"


def _recommend_model(vram_gb: float) -> dict:
    """Recommend the best model for available VRAM."""
    best = None
    for model_id, reqs in MODEL_VRAM_REQUIREMENTS.items():
        if vram_gb >= reqs["recommended_vram_gb"]:
            if best is None or reqs["recommended_vram_gb"] > MODEL_VRAM_REQUIREMENTS[best]["recommended_vram_gb"]:
                best = model_id
    if best:
        return {"model": best, "label": MODEL_VRAM_REQUIREMENTS[best]["label"]}
    # Fallback to smallest
    return {"model": "phi-3-mini", "label": "Phi-3 Mini (lightweight)"}


def _compatible_models(vram_gb: float) -> list:
    """Return all compatible models with compatibility flags."""
    results = []
    for model_id, reqs in MODEL_VRAM_REQUIREMENTS.items():
        if vram_gb >= reqs["min_vram_gb"]:
            status = "✅ Recommended" if vram_gb >= reqs["recommended_vram_gb"] else "⚠️ May be slow"
        else:
            status = "❌ Not enough AI memory"
        results.append({
            "model": model_id,
            "label": reqs["label"],
            "min_vram_gb": reqs["min_vram_gb"],
            "recommended_vram_gb": reqs["recommended_vram_gb"],
            "status": status,
            "compatible": vram_gb >= reqs["min_vram_gb"],
        })
    return sorted(results, key=lambda x: x["min_vram_gb"])


# ---------------------------------------------------------------------------
# Friendly names
# ---------------------------------------------------------------------------

ROLE_FRIENDLY = {
    "orchestrator": "Main AI",
    "backend": "Helper",
    "memory": "Memory Assistant",
    "security": "Security Guard",
    "agent": "Worker",
    "observer": "Watcher",
}

STAGE_FRIENDLY = {
    "build": "Creating...",
    "test": "Checking quality...",
    "review": "Getting a second opinion...",
    "spec": "Planning what to do...",
    "memory": "Remembering for later...",
    "deploy": "Making it live...",
}

STATUS_FRIENDLY = {
    "active": "Working on it",
    "shipped": "Done ✅",
    "escalated": "Needs Your Help",
    "error": "Something went wrong",
    "cancelled": "Stopped",
    "killed": "Stopped (safety limit)",
}

PERSONALITY_TONES = {
    (0.0, 0.3): "Casual",
    (0.3, 0.5): "Friendly",
    (0.5, 0.7): "Professional",
    (0.7, 0.9): "Direct",
    (0.9, 1.0): "Playful",
}


def friendly_node(node_name: str, node_config: dict) -> dict:
    """Add consumer-friendly labels to a node."""
    role = node_config.get("role", "agent")
    user = node_name.split(".")[0].capitalize() if "." in node_name else node_name.capitalize()

    return {
        "name": node_name,
        "friendly_name": f"{user}'s Device",
        "friendly_role": ROLE_FRIENDLY.get(role, role.capitalize()),
        "role": role,
        **{k: v for k, v in node_config.items() if k != "role"},
    }


def friendly_pipeline(pipeline: dict) -> dict:
    """Add consumer-friendly labels to a pipeline."""
    stage_idx = pipeline.get("current_stage", 0)
    stages = pipeline.get("stages", [])
    total = len(stages)

    current_stage_name = ""
    if stage_idx < total:
        current_stage_name = stages[stage_idx].get("name", f"stage_{stage_idx}")

    status = pipeline.get("status", "active")
    iteration = pipeline.get("current_iteration", 0)
    max_iter = pipeline.get("max_iterations", 3)

    return {
        **pipeline,
        "step_description": f"Step {stage_idx + 1} of {total}: {STAGE_FRIENDLY.get(current_stage_name, current_stage_name)}",
        "friendly_status": STATUS_FRIENDLY.get(status, status),
        "progress_text": f"Attempt {iteration + 1} of {max_iter}",
        "progress_pct": round((stage_idx / max(total, 1)) * 100),
    }


def friendly_personality(traits: dict, soul_config: dict) -> dict:
    """Convert personality traits to form-friendly fields."""
    # Determine tone from formality-like traits
    accuracy = traits.get("accuracy", 0.5)
    tone = "Friendly"
    for (lo, hi), label in PERSONALITY_TONES.items():
        if lo <= accuracy < hi:
            tone = label
            break

    # Extract skills from soul config or traits
    skills = []
    approach = traits.get("default_approach", "")
    if "code" in approach.lower() or "build" in approach.lower():
        skills.append("Coding")
    if "research" in approach.lower() or "learn" in approach.lower():
        skills.append("Research")
    if "write" in approach.lower() or "draft" in approach.lower():
        skills.append("Writing")
    if not skills:
        skills = ["General assistance"]

    return {
        "tone": tone,
        "tone_options": ["Casual", "Friendly", "Professional", "Direct", "Playful"],
        "skills": skills,
        "boundaries": [],
        "traits_raw": traits,
        "name": soul_config.get("name", _NODE_ID),
        "role": soul_config.get("role", "Assistant"),
    }


# ---------------------------------------------------------------------------
# Activity tracking
# ---------------------------------------------------------------------------

def record_activity(event_type: str, count: int = 1) -> None:
    """Record an activity for today's summary."""
    with _activity_lock:
        today = int(time.time()) // 86400
        if _activity["last_reset"] != today:
            _activity.update({
                "questions_answered": 0, "files_read": 0,
                "things_learned": 0, "tasks_completed": 0,
                "debates_held": 0, "last_reset": today,
            })

        key_map = {
            "chat.response": "questions_answered",
            "file.read": "files_read",
            "pipeline.shipped": "tasks_completed",
            "hypothesis.accepted": "things_learned",
            "crucible.run": "things_learned",
            "socratic.consensus": "debates_held",
        }
        key = key_map.get(event_type)
        if key:
            _activity[key] = _activity.get(key, 0) + count


def get_activity_summary() -> dict:
    """Return today's activity in plain English."""
    with _activity_lock:
        parts = []
        if _activity["questions_answered"]:
            parts.append(f"Answered {_activity['questions_answered']} question{'s' if _activity['questions_answered'] != 1 else ''}")
        if _activity["files_read"]:
            parts.append(f"read {_activity['files_read']} file{'s' if _activity['files_read'] != 1 else ''}")
        if _activity["things_learned"]:
            parts.append(f"learned {_activity['things_learned']} new thing{'s' if _activity['things_learned'] != 1 else ''}")
        if _activity["tasks_completed"]:
            parts.append(f"completed {_activity['tasks_completed']} task{'s' if _activity['tasks_completed'] != 1 else ''}")
        if _activity["debates_held"]:
            parts.append(f"held {_activity['debates_held']} debate{'s' if _activity['debates_held'] != 1 else ''}")

        summary = ", ".join(parts) if parts else "Just woke up — no activity yet today"

        return {
            "summary": summary,
            "details": {k: v for k, v in _activity.items() if k != "last_reset"},
        }


# ---------------------------------------------------------------------------
# Learning summary
# ---------------------------------------------------------------------------

def get_learning_summary(base_dir: Path) -> dict:
    """Aggregate knowledge stats for the 'How It's Learning' page."""
    import datetime

    # Count procedures
    proc_file = base_dir / "war_room_data" / "procedures.json"
    total_procedures = 0
    high_confidence = 0
    if proc_file.exists():
        try:
            procs = json.loads(proc_file.read_text(encoding="utf-8"))
            if isinstance(procs, list):
                total_procedures = len(procs)
                high_confidence = sum(1 for p in procs if p.get("confidence", 0) >= 0.7)
            elif isinstance(procs, dict):
                total_procedures = len(procs)
                high_confidence = sum(
                    1 for p in procs.values()
                    if isinstance(p, dict) and p.get("confidence", 0) >= 0.7
                )
        except Exception:
            pass

    reliability = round((high_confidence / max(total_procedures, 1)) * 100)

    # Check crucible results — compute knowledge check score
    crucible_file = base_dir / "war_room_data" / "crucible_results.json"
    crucible_runs = 0
    crucible_survived = 0
    if crucible_file.exists():
        try:
            data = json.loads(crucible_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                crucible_runs = len(data)
                crucible_survived = sum(
                    1 for r in data
                    if isinstance(r, dict) and r.get("survived", r.get("passed", False))
                )
        except Exception:
            pass

    knowledge_check_score = round(
        (crucible_survived / max(crucible_runs, 1)) * 100
    )

    # Check predictions accuracy + week-over-week improvement
    pred_file = base_dir / "war_room_data" / "predictions.json"
    prediction_count = 0
    correct_predictions = 0
    wow_improvement = 0.0
    if pred_file.exists():
        try:
            data = json.loads(pred_file.read_text(encoding="utf-8"))
            preds = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
            prediction_count = len(preds)

            # Calculate accuracy
            for p in preds:
                if isinstance(p, dict) and p.get("correct", False):
                    correct_predictions += 1

            # Week-over-week improvement
            now = datetime.datetime.utcnow()
            week_ago = now - datetime.timedelta(days=7)
            two_weeks_ago = now - datetime.timedelta(days=14)

            this_week = []
            last_week = []
            for p in preds:
                if not isinstance(p, dict):
                    continue
                ts = p.get("timestamp", p.get("created_at", 0))
                if isinstance(ts, str):
                    try:
                        ts = datetime.datetime.fromisoformat(ts).timestamp()
                    except Exception:
                        ts = 0
                if ts >= week_ago.timestamp():
                    this_week.append(p)
                elif ts >= two_weeks_ago.timestamp():
                    last_week.append(p)

            if this_week and last_week:
                this_acc = sum(1 for p in this_week if p.get("correct", False)) / len(this_week)
                last_acc = sum(1 for p in last_week if p.get("correct", False)) / len(last_week)
                wow_improvement = round((this_acc - last_acc) * 100, 1)
        except Exception:
            pass

    accuracy_pct = round((correct_predictions / max(prediction_count, 1)) * 100)

    return {
        "things_it_knows": total_procedures,
        "reliable_pct": reliability,
        "crucible_tests_run": crucible_runs,
        "knowledge_check_score": knowledge_check_score,
        "predictions_made": prediction_count,
        "accuracy_pct": accuracy_pct,
        "week_over_week_improvement": wow_improvement,
        "summary": f"Things it knows: {total_procedures}. "
                   f"Reliable: {reliability}%. "
                   f"Knowledge check: {knowledge_check_score}%. "
                   f"Tested {crucible_runs} time{'s' if crucible_runs != 1 else ''}. "
                   f"WoW: {'+' if wow_improvement >= 0 else ''}{wow_improvement}%.",
    }


# ---------------------------------------------------------------------------
# Event bus hook
# ---------------------------------------------------------------------------

def on_event(event_name: str, payload: dict) -> None:
    """Hook called by plugin_loader for event bus events."""
    record_activity(event_name)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _NODE_ID, _BASE_DIR, _MESH_NODES, _MODEL_PROVIDERS, _MODEL_ALIASES, _SOUL_CONFIG

    _NODE_ID = config.get("node", {}).get("name", "unknown")
    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MESH_NODES = config.get("mesh", {}).get("nodes", {})
    _MODEL_PROVIDERS = config.get("models", {}).get("providers", {})
    _MODEL_ALIASES = config.get("models", {}).get("aliases", {})
    _SOUL_CONFIG = config.get("soul", {})

    router = APIRouter(tags=["consumer-api"])

    @router.get("/api/v1/system/hardware")
    async def api_hardware():
        """Detect local hardware and recommend models."""
        return detect_hardware()

    @router.get("/api/v1/friendly/nodes")
    async def api_friendly_nodes():
        """Nodes with consumer-friendly labels."""
        nodes = []
        for name, cfg in _MESH_NODES.items():
            if isinstance(cfg, dict):
                nodes.append(friendly_node(name, cfg))
            else:
                nodes.append(friendly_node(name, {"url": str(cfg)}))
        return {"devices": nodes, "count": len(nodes)}

    @router.get("/api/v1/friendly/pipeline")
    async def api_friendly_pipeline():
        """Pipelines with plain-English step descriptions."""
        pipe_dir = _BASE_DIR / "war_room_data" / "pipelines"
        if not pipe_dir.exists():
            return {"tasks": [], "count": 0}

        tasks = []
        for f in sorted(pipe_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                tasks.append(friendly_pipeline(data))
            except Exception:
                pass

        return {"tasks": tasks, "count": len(tasks)}

    @router.get("/api/v1/friendly/personality")
    async def api_friendly_personality():
        """Personality as form-friendly fields."""
        # Try loading personality traits
        traits_file = _BASE_DIR / "war_room_data" / "personality_traits.json"
        traits = {}
        if traits_file.exists():
            try:
                traits = json.loads(traits_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return friendly_personality(traits, _SOUL_CONFIG)

    @router.get("/api/v1/activity/today")
    async def api_activity():
        """What your AI did today — plain English."""
        return get_activity_summary()

    @router.get("/api/v1/learning/summary")
    async def api_learning():
        """How It's Learning — knowledge count, reliability, trend."""
        return get_learning_summary(_BASE_DIR)

    app.include_router(router)
    log.info("[consumer-api] Plugin loaded. Device: %s", platform.node())

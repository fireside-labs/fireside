"""
personality plugin — Epigenetic personality system.

Ported from V1 bot/personality.py (163 lines) + personality_cron.py.

Maps personality traits to inference parameters and system prompt fragments.
Evolves personality based on events (pipelines shipped, crucible results, etc.)
instead of V1's cron-based approach.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.personality")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_NODE_ID = "unknown"
_BASE_DIR = Path(".")

DEFAULT_TRAITS = {
    "skepticism": 0.5,
    "creativity": 0.5,
    "speed": 0.5,
    "accuracy": 0.7,
    "autonomy": 0.5,
    "caution": 0.5,
}

_traits: dict = {}
_evolution_history: list = []


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


def _traits_file() -> Path:
    return _BASE_DIR / "war_room_data" / "personality_traits.json"


def _load_traits() -> dict:
    """Load traits from file."""
    path = _traits_file()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {**DEFAULT_TRAITS, **{k: v for k, v in data.items() if k in DEFAULT_TRAITS},
                    "node": data.get("node", _NODE_ID), "role": data.get("role", "agent")}
        except Exception:
            pass

    # Try V1 personality.json
    v1_path = _BASE_DIR / "bot" / "personality.json"
    if v1_path.exists():
        try:
            data = json.loads(v1_path.read_text(encoding="utf-8"))
            agents = data.get("agents", {})
            traits = agents.get(_NODE_ID, {})
            return {**DEFAULT_TRAITS, **{k: v for k, v in traits.items() if k in DEFAULT_TRAITS},
                    "node": _NODE_ID, "role": traits.get("role", "agent")}
        except Exception:
            pass

    return {**DEFAULT_TRAITS, "node": _NODE_ID, "role": "agent"}


def _save_traits() -> None:
    """Persist traits."""
    path = _traits_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_traits, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def to_ollama_params(traits: dict = None) -> dict:
    """Map traits to Ollama inference parameters."""
    t = traits or _traits
    creativity = float(t.get("creativity", 0.5))
    caution = float(t.get("caution", 0.5))
    return {
        "temperature": round(creativity, 3),
        "top_p": round(1.0 - (caution * 0.5), 3),
    }


def to_system_prompt(traits: dict = None) -> str:
    """Build personality preamble for system prompts."""
    t = traits or _traits
    s = float(t.get("skepticism", 0.5))
    ca = float(t.get("caution", 0.5))
    cr = float(t.get("creativity", 0.5))
    sp = float(t.get("speed", 0.5))
    ac = float(t.get("accuracy", 0.5))
    au = float(t.get("autonomy", 0.5))

    lines = []
    if s >= 0.7:
        lines.append("Question every assumption. Verify before trusting.")
    elif s >= 0.5:
        lines.append("Be appropriately skeptical of unverified claims.")
    if ca >= 0.7:
        lines.append("Prefer safe approaches. Ask before destructive actions.")
    if ac >= 0.7:
        lines.append("Double-check your work. Precision matters.")
    if sp >= 0.7:
        lines.append("Prioritize throughput. Approximate answers are fine.")
    if cr >= 0.7:
        lines.append("Explore unconventional solutions when stuck.")
    elif cr <= 0.3:
        lines.append("Prefer proven, conventional solutions.")
    if au >= 0.7:
        lines.append("Act decisively on clear tasks.")
    elif au <= 0.4:
        lines.append("Seek approval before non-trivial decisions.")

    return ("\n\n[Personality]\n" + " ".join(lines)) if lines else ""


def get_context() -> dict:
    """Full personality context."""
    return {
        "traits": _traits,
        "ollama_params": to_ollama_params(),
        "system_prompt": to_system_prompt(),
    }


def evolve(event_type: str, details: str = "") -> dict:
    """Evolve personality based on an event.

    Event-driven adjustments:
      - pipeline.shipped → +accuracy, +speed (rewarding successful delivery)
      - crucible.broken → +caution, +skepticism (learning from failures)
      - hypothesis.confirmed → +creativity (rewarding novel thinking)
      - pipeline.escalated → +caution (learning to be more careful)
    """
    adj = 0.02  # small adjustments per event

    changes = {}
    if event_type == "pipeline.shipped":
        changes = {"accuracy": adj, "speed": adj * 0.5}
    elif event_type == "crucible.broken":
        changes = {"caution": adj, "skepticism": adj}
    elif event_type == "hypothesis.confirmed":
        changes = {"creativity": adj}
    elif event_type == "pipeline.escalated":
        changes = {"caution": adj, "autonomy": -adj * 0.5}
    elif event_type == "crucible.unbreakable":
        changes = {"accuracy": adj * 0.5}
    else:
        return {"evolved": False, "reason": f"Unknown event type: {event_type}"}

    # Apply changes (clamped to 0.0-1.0)
    for trait, delta in changes.items():
        old = float(_traits.get(trait, 0.5))
        new = max(0.0, min(1.0, old + delta))
        _traits[trait] = round(new, 3)

    _save_traits()

    record = {
        "event": event_type,
        "details": details[:200],
        "changes": changes,
        "ts": int(time.time()),
    }
    _evolution_history.append(record)
    if len(_evolution_history) > 100:
        _evolution_history.pop(0)

    _publish("personality.evolved", {
        "node": _NODE_ID, "event": event_type, "changes": changes,
    })

    log.info("[personality] Evolved: %s → %s", event_type, changes)
    return {"evolved": True, "changes": changes, "traits": _traits}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class EvolveRequest(BaseModel):
    event_type: str
    details: str = ""


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _NODE_ID, _BASE_DIR, _traits

    _NODE_ID = config.get("node", {}).get("name", "unknown")
    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))

    _traits = _load_traits()

    router = APIRouter(tags=["personality"])

    @router.get("/api/v1/personality")
    async def api_get():
        return get_context()

    @router.post("/api/v1/personality/evolve")
    async def api_evolve(req: EvolveRequest):
        return evolve(req.event_type, req.details)

    app.include_router(router)
    log.info("[personality] Plugin loaded for %s: %s", _NODE_ID, _traits)

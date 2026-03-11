"""
companion/handler.py — Pocket Companion API.

Routes:
  GET  /api/v1/companion/status    — Pet status (stats, mood prefix)
  POST /api/v1/companion/feed      — Feed the pet
  POST /api/v1/companion/walk      — Take a walk
  POST /api/v1/companion/queue     — Add task from phone
  GET  /api/v1/companion/queue     — Poll for task results
  POST /api/v1/companion/sync      — Sync personality to phone
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("valhalla.companion")


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AdoptRequest(BaseModel):
    name: str
    species: str = "cat"


class FeedRequest(BaseModel):
    food: str


class QueueTaskRequest(BaseModel):
    task_type: str
    payload: Optional[dict] = None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    router = APIRouter(tags=["companion"])

    @router.get("/api/v1/companion/status")
    async def api_status():
        """Get companion status."""
        from plugins.companion.sim import load_state, get_status
        state = load_state()
        if not state:
            return {"adopted": False, "message": "No companion adopted yet."}
        return {"adopted": True, **get_status(state)}

    @router.post("/api/v1/companion/adopt")
    async def api_adopt(req: AdoptRequest):
        """Adopt a new companion."""
        from plugins.companion.sim import default_companion, save_state, load_state
        existing = load_state()
        if existing:
            raise HTTPException(400, f"You already have {existing['name']}! Release first.")
        state = default_companion(req.name, req.species)
        save_state(state)
        return {"ok": True, "companion": state}

    @router.post("/api/v1/companion/feed")
    async def api_feed(req: FeedRequest):
        """Feed the companion."""
        from plugins.companion.sim import load_state, feed
        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted.")
        result = feed(state, req.food)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error"))
        _publish("companion.fed", result)
        if result.get("level_up"):
            _publish("companion.levelup", {"name": state["name"], "level": state["level"]})
        return result

    @router.post("/api/v1/companion/walk")
    async def api_walk():
        """Take the companion for a walk."""
        from plugins.companion.sim import load_state, walk
        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted.")
        result = walk(state)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error"))
        _publish("companion.walked", result)
        if result.get("level_up"):
            _publish("companion.levelup", {"name": state["name"], "level": state["level"]})
        return result

    @router.post("/api/v1/companion/queue")
    async def api_queue_task(req: QueueTaskRequest):
        """Add a task from the phone."""
        from plugins.companion.queue import add_task
        result = add_task(req.task_type, req.payload)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error"))
        _publish("companion.task.queued", result["task"])
        return result

    @router.get("/api/v1/companion/queue")
    async def api_get_queue(status: str = ""):
        """Get task queue."""
        from plugins.companion.queue import get_queue, get_stats
        tasks = get_queue(status)
        stats = get_stats()
        return {"tasks": tasks, **stats}

    @router.post("/api/v1/companion/sync")
    async def api_sync():
        """Sync personality profile for the phone."""
        from plugins.companion.sim import load_state, get_status, get_mood_prefix

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted.")

        # Build personality profile for phone
        status = get_status(state)

        # Load agent personality if available
        personality = {}
        try:
            from plugins.agent_profiles.leveling import load_profile
            profile = load_profile(state.get("name", "companion"))
            personality = profile.get("personality", {})
        except Exception:
            pass

        return {
            "ok": True,
            "companion": status,
            "personality": personality,
            "mood_prefix": get_mood_prefix(state),
            "synced_at": __import__("time").time(),
        }

    @router.delete("/api/v1/companion")
    async def api_release():
        """Release companion into the wild."""
        from plugins.companion.sim import _state_file
        f = _state_file()
        if f.exists():
            f.unlink()
        return {"ok": True, "message": "Released into the wild. 🌲"}

    app.include_router(router)
    log.info("[companion] Plugin loaded.")

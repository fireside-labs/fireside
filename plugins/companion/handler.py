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


class TranslateRequest(BaseModel):
    text: str
    target_lang: str
    source_lang: str = ""


class GuardianRequest(BaseModel):
    text: str
    hour: int = -1
    recipient: str = ""


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

        status = get_status(state)
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

    # --- Sprint 14: Translation + Guardian ---

    @router.post("/api/v1/companion/translate")
    async def api_translate(req: TranslateRequest):
        """Translate text using NLLB-200."""
        from plugins.companion.nllb import translate
        result = translate(req.text, req.target_lang, req.source_lang)
        return result

    @router.get("/api/v1/companion/translate/languages")
    async def api_languages():
        """List supported languages."""
        from plugins.companion.nllb import get_languages, get_info
        return {"languages": get_languages(), **get_info()}

    @router.post("/api/v1/companion/guardian")
    async def api_guardian(req: GuardianRequest):
        """Analyze a message before sending (regret detection)."""
        from plugins.companion.sim import load_state
        from plugins.companion.guardian import analyze_message
        state = load_state()
        species = state.get("species", "cat") if state else "cat"
        result = analyze_message(req.text, req.hour, req.recipient, species)
        return result

    # --- Sprint 1: Mobile endpoints ---

    @router.post("/api/v1/companion/mobile/sync")
    async def api_mobile_sync():
        """Single-call sync for mobile app launch.

        Returns: companion status, pending task results, personality, mood prefix.
        The phone calls this once on launch to get everything it needs in one request.
        """
        import time as _time
        from plugins.companion.sim import load_state, get_status, get_mood_prefix
        from plugins.companion.queue import get_queue

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        companion_status = get_status(state)

        personality = {}
        try:
            from plugins.agent_profiles.leveling import load_profile
            profile = load_profile(state.get("name", "companion"))
            personality = profile.get("personality", {})
        except Exception:
            pass

        # Completed tasks not yet acknowledged by the phone
        try:
            pending_tasks = get_queue(status="completed")
        except Exception:
            pending_tasks = []

        return {
            "ok": True,
            "companion": companion_status,
            "personality": personality,
            "mood_prefix": get_mood_prefix(state),
            "pending_tasks": pending_tasks,
            "synced_at": _time.time(),
        }

    @router.post("/api/v1/companion/mobile/pair")
    async def api_mobile_pair():
        """Generate a pairing token for the mobile app.

        Creates a 6-character alphanumeric code and stores it in
        ~/.valhalla/mobile_token.json with a 365-day expiry.
        Heimdall will harden the auth model in Sprint 2.
        """
        import secrets
        import string
        import json
        import time as _time
        from pathlib import Path
        from datetime import datetime, timezone, timedelta

        # Generate 6-char uppercase alphanumeric token (easy to type on phone)
        alphabet = string.ascii_uppercase + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(6))

        expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        expires_ts = expires_at.timestamp()

        # Persist to ~/.valhalla/mobile_token.json
        token_dir = Path.home() / ".valhalla"
        token_dir.mkdir(parents=True, exist_ok=True)
        token_file = token_dir / "mobile_token.json"
        token_file.write_text(
            json.dumps({
                "token": token,
                "created_at": _time.time(),
                "expires_at": expires_ts,
            }),
            encoding="utf-8",
        )

        log.info("[companion/pair] Mobile pairing token generated (expires %s)",
                 expires_at.strftime("%Y-%m-%d"))

        return {
            "ok": True,
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    app.include_router(router)
    log.info("[companion] Plugin loaded (with translation + guardian + mobile).")

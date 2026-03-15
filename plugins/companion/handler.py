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

import hmac
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
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
    name: str  # Sprint 3: max_length enforced below in endpoint
    species: str = "cat"

    @classmethod
    def validate_name(cls, v):
        if len(v) > 20:
            raise ValueError("Companion name must be 20 characters or fewer")
        return v


class FeedRequest(BaseModel):
    food: str


class QueueTaskRequest(BaseModel):
    task_type: str  # Sprint 3: max_length enforced below in endpoint
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
        # Sprint 3 Task 5: Input validation
        if len(req.name) > 20:
            raise HTTPException(422, "Companion name must be 20 characters or fewer.")
        if not req.name.strip():
            raise HTTPException(422, "Companion name cannot be empty.")
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
        # Sprint 3 Task 5: Input validation
        if len(req.task_type) > 200:
            raise HTTPException(422, "task_type must be 200 characters or fewer.")
        if req.payload and len(json.dumps(req.payload)) > 10000:
            raise HTTPException(422, "payload too large (max 10KB).")
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

    # --- Sprint 1+2: Mobile endpoints ---

    # Rate limit tracking for /mobile/pair (Sprint 2, Task 3)
    _pair_attempts: dict = {}  # ip → [timestamps]
    _PAIR_RATE_LIMIT = 3  # max requests per minute
    _stored_config = config  # Store config ref for auth checks

    @router.post("/api/v1/companion/mobile/sync")
    async def api_mobile_sync():
        """Single-call sync for mobile app launch.

        Returns: companion status, pending task results, personality, mood prefix.
        Sprint 2: Also returns adoption info when no companion is adopted.
        """
        import time as _time
        from plugins.companion.sim import load_state, get_status, get_mood_prefix

        state = load_state()
        if not state:
            # Sprint 2 Task 5: return adoption info instead of 404
            return {
                "ok": True,
                "adopted": False,
                "available_species": ["cat", "dog", "penguin", "fox", "owl", "dragon"],
                "message": "No companion adopted yet. Choose a species to adopt!",
                "synced_at": _time.time(),
            }

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
            from plugins.companion.queue import get_queue
            pending_tasks = get_queue(status="completed")
        except Exception:
            pending_tasks = []

        # Sprint 4 Task 2: Check daily gift availability
        last_gift_ts = state.get("last_daily_gift", 0)
        daily_gift_available = (_time.time() - last_gift_ts) > 86400  # 24h

        # Sprint 4 Task 1: Adventure availability (simple cooldown check)
        last_adventure_ts = state.get("last_adventure", 0)
        adventure_available = (_time.time() - last_adventure_ts) > 3600  # 1h cooldown

        return {
            "ok": True,
            "adopted": True,
            "companion": companion_status,
            "personality": personality,
            "mood_prefix": get_mood_prefix(state),
            "pending_tasks": pending_tasks,
            "synced_at": _time.time(),
            # Sprint 4 Task 4: Feature flags for mobile
            "features": {
                "adventures": True,
                "daily_gift": True,
                "guardian": True,
                "teach_me": True,
                "translation": True,
                "morning_briefing": True,
            },
            "daily_gift_available": daily_gift_available,
            "adventure_available": adventure_available,
        }

    @router.post("/api/v1/companion/mobile/pair")
    async def api_mobile_pair(request: "Request"):
        """Generate a pairing token for the mobile app.

        Sprint 2 hardened:
        - Requires X-Valhalla-Auth header (dashboard.auth_key)
        - Rate limited: 3 requests per minute per IP
        - Token TTL: 15 minutes (was 365 days)
        - Invalidates previous token on new generation
        - File permissions set to owner-only (0600)
        """
        import secrets
        import string
        import json
        import os
        import time as _time
        from pathlib import Path
        from datetime import datetime, timezone, timedelta

        # Sprint 2 Task 2: Require auth header
        auth_key = _stored_config.get("dashboard", {}).get("auth_key", "")
        provided = request.headers.get("X-Valhalla-Auth", "")
        if not auth_key or auth_key == "change-me-dashboard-key":
            log.warning("[companion/pair] dashboard.auth_key is not configured!")
        # Sprint 3 Task 3: timing-safe comparison
        if not provided or not hmac.compare_digest(provided, auth_key):
            raise HTTPException(401, "Missing or invalid X-Valhalla-Auth header.")

        # Sprint 2 Task 3: Rate limiting (3/min per IP)
        # Sprint 3 Task 4: Cleanup stale entries (>2 min old)
        client_ip = request.client.host if request.client else "unknown"
        now = _time.time()
        stale_ips = [ip for ip, times in _pair_attempts.items()
                     if all(now - t > 120 for t in times)]
        for ip in stale_ips:
            del _pair_attempts[ip]
        window = [t for t in _pair_attempts.get(client_ip, []) if now - t < 60]
        if len(window) >= _PAIR_RATE_LIMIT:
            raise HTTPException(429, "Too many pairing attempts. Try again in 1 minute.")
        window.append(now)
        _pair_attempts[client_ip] = window

        # Generate 6-char uppercase alphanumeric token (easy to type on phone)
        alphabet = string.ascii_uppercase + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(6))

        # Sprint 2 Task 3: Reduced TTL → 15 minutes
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        expires_ts = expires_at.timestamp()

        # Persist to ~/.valhalla/mobile_token.json
        # Sprint 2 Task 3: Invalidates previous token by overwriting
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

        # Sprint 2 Task 3: Set file permissions to owner-only (0600)
        try:
            os.chmod(str(token_file), 0o600)
        except OSError:
            pass  # Windows doesn't support POSIX permissions

        log.info("[companion/pair] Mobile pairing token generated (expires %s)",
                 expires_at.strftime("%H:%M:%S"))

        return {
            "ok": True,
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    # --- Sprint 2: Chat history endpoints (Task 4) ---

    @router.post("/api/v1/companion/chat/history")
    async def api_save_chat(request: "Request"):
        """Save a chat message to persistent history.

        Body: { "role": "user"|"companion", "content": "...", "timestamp": 1234567890.0 }
        Stores in ~/.valhalla/chat_history.json, capped at 500 messages (FIFO).
        """
        import json
        import time as _time
        from pathlib import Path

        body = await request.json()
        role = body.get("role", "")
        content = body.get("content", "")
        timestamp = body.get("timestamp", _time.time())

        if role not in ("user", "companion"):
            raise HTTPException(400, "role must be 'user' or 'companion'")
        if not content or not isinstance(content, str):
            raise HTTPException(400, "content must be a non-empty string")
        if len(content) > 5000:
            raise HTTPException(400, "content too long (max 5000 chars)")

        history_dir = Path.home() / ".valhalla"
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / "chat_history.json"

        messages = []
        if history_file.exists():
            try:
                messages = json.loads(history_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                messages = []

        messages.append({
            "role": role,
            "content": content,
            "timestamp": timestamp,
        })

        # FIFO cap at 500
        if len(messages) > 500:
            messages = messages[-500:]

        history_file.write_text(
            json.dumps(messages, ensure_ascii=False),
            encoding="utf-8",
        )

        return {"ok": True, "total_messages": len(messages)}

    @router.get("/api/v1/companion/chat/history")
    async def api_get_chat():
        """Get chat history (last 100 messages, sorted by timestamp)."""
        import json
        from pathlib import Path

        history_file = Path.home() / ".valhalla" / "chat_history.json"
        if not history_file.exists():
            return {"ok": True, "messages": [], "total": 0}

        try:
            messages = json.loads(history_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            return {"ok": True, "messages": [], "total": 0}

        # Sort by timestamp, return last 100
        messages.sort(key=lambda m: m.get("timestamp", 0))
        recent = messages[-100:]

        return {"ok": True, "messages": recent, "total": len(messages)}

    # --- Sprint 2: IP validation endpoint (Task 6) ---

    @router.get("/api/v1/companion/mobile/validate-host")
    async def api_validate_host(host: str = ""):
        """Validate an IP:port or hostname:port string for mobile setup.

        Returns whether the format is acceptable.
        """
        import re

        if not host:
            raise HTTPException(400, "host parameter is required")

        host = host.strip()

        # Accept: IP:port, IP without port, hostname:port, hostname
        ip_port_re = re.compile(
            r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?$"
        )
        hostname_re = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$"
        )
        hostname_port_re = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*:\d{1,5}$"
        )

        # Reject protocols
        if host.startswith(("http://", "https://", "ftp://", "javascript:", "file://")):
            return {
                "ok": False,
                "valid": False,
                "error": "Don't include the protocol (http://). Just enter the IP or hostname.",
            }

        if ip_port_re.match(host):
            # Validate IP octets
            ip_part = host.split(":")[0]
            octets = ip_part.split(".")
            for octet in octets:
                if int(octet) > 255:
                    return {"ok": False, "valid": False, "error": f"Invalid IP octet: {octet}"}
            # Validate port if present
            if ":" in host:
                port = int(host.split(":")[1])
                if port < 1 or port > 65535:
                    return {"ok": False, "valid": False, "error": f"Port must be 1-65535, got {port}"}
            return {"ok": True, "valid": True, "host": host}

        if hostname_port_re.match(host) or hostname_re.match(host):
            return {"ok": True, "valid": True, "host": host}

        return {
            "ok": False,
            "valid": False,
            "error": "Invalid format. Expected: IP address (e.g., 100.117.255.38) or hostname (e.g., my-pc:8765)",
        }
    # --- Sprint 3: Push notification endpoints ---

    @router.post("/api/v1/companion/mobile/register-push")
    async def api_register_push(request: Request):
        """Register an Expo push token from the mobile app.

        Body: { "token": "ExponentPushToken[...]" }
        Stores in ~/.valhalla/push_token.json.
        """
        body = await request.json()
        expo_token = body.get("token", "")
        if not expo_token or not isinstance(expo_token, str):
            raise HTTPException(400, "token must be a non-empty string")
        if not expo_token.startswith("ExponentPushToken["):
            raise HTTPException(400, "Invalid Expo push token format")

        from plugins.companion.notifications import save_push_token
        result = save_push_token(expo_token)
        return result

    @router.post("/api/v1/companion/mobile/check-notifications")
    async def api_check_notifications():
        """Manually trigger notification checks (also runs on decay cycle)."""
        from plugins.companion.sim import load_state
        state = load_state()
        if not state:
            return {"ok": True, "fired": []}

        from plugins.companion.notifications import check_and_notify
        fired = await check_and_notify(state)
        return {"ok": True, "fired": fired}

    # --- Sprint 4: Adventure endpoints (Task 1) ---

    @router.post("/api/v1/companion/adventure/generate")
    async def api_adventure_generate():
        """Generate a random adventure encounter.

        Returns an encounter with intro, choices, and loot table.
        Server-authoritative — rewards are signed.
        """
        import random
        import time as _time
        from plugins.companion.sim import load_state, save_state
        from plugins.companion.adventure_guard import (
            VALID_ENCOUNTER_TYPES, sign_adventure_result,
        )

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        # 1-hour cooldown
        last_adv = state.get("last_adventure", 0)
        if _time.time() - last_adv < 3600:
            remaining = int(3600 - (_time.time() - last_adv))
            raise HTTPException(429, f"Adventure cooldown: {remaining}s remaining.")

        species = state.get("species", "cat")
        enc_type = random.choice(list(VALID_ENCOUNTER_TYPES))

        # Generate encounter based on type
        encounter = _generate_encounter(enc_type, species, state.get("name", "Companion"))

        # Mark adventure started
        state["last_adventure"] = _time.time()
        save_state(state)

        return {"ok": True, "encounter": encounter}

    def _generate_encounter(enc_type: str, species: str, name: str) -> dict:
        """Build a random encounter based on type."""
        import random
        import time as _time

        encounters = {
            "riddle": {
                "type": "riddle",
                "intro": f"{name} found a mysterious stone tablet! A riddle is carved into it...",
                "riddle": random.choice([
                    "I have cities, but no houses. Forests, but no trees. Water, but no fish. What am I?",
                    "The more you take, the more you leave behind. What am I?",
                    "I speak without a mouth and hear without ears. I have no body, but I am alive with the wind.",
                ]),
                "accept_answers": random.choice([["map", "a map"], ["footsteps", "steps"], ["echo", "an echo"]]),
                "reward": {"xp": 15, "happiness": 10},
                "choices": [
                    {"text": "Try to solve it", "reward": {"xp": 15, "happiness": 10}},
                    {"text": "Walk away", "reward": {"xp": 2, "happiness": 0}},
                ],
            },
            "treasure": {
                "type": "treasure",
                "intro": f"{name} spotted something shiny buried under a rock!",
                "loot_table": [
                    {"item": "golden_coin", "chance": 0.4, "emoji": "🪙"},
                    {"item": "crystal_shard", "chance": 0.3, "emoji": "💎"},
                    {"item": "ancient_scroll", "chance": 0.2, "emoji": "📜"},
                    {"item": "dragon_scale", "chance": 0.1, "emoji": "🐉"},
                ],
                "reward": {"xp": 10, "happiness": 15},
                "choices": [
                    {"text": "Dig it up!", "reward": {"xp": 10, "happiness": 15}},
                    {"text": "Leave it for another day", "reward": {"xp": 2, "happiness": 0}},
                ],
            },
            "merchant": {
                "type": "merchant",
                "intro": f"A wandering merchant appears! '{name}, I have wares if you have coin...'",
                "choices": [
                    {"text": "Browse wares", "reward": {"xp": 5, "happiness": 8}},
                    {"text": "Haggle for a deal", "reward": {"xp": 12, "happiness": 5}},
                    {"text": "Keep walking", "reward": {"xp": 2, "happiness": 0}},
                ],
                "reward": {"xp": 8, "happiness": 5},
            },
            "forage": {
                "type": "forage",
                "intro": f"{name} found a patch of interesting plants!",
                "finds": [
                    {"item": "healing_herb", "chance": 0.5, "emoji": "🌿"},
                    {"item": "glowing_mushroom", "chance": 0.3, "emoji": "🍄"},
                    {"item": "rare_flower", "chance": 0.2, "emoji": "🌸"},
                ],
                "reward": {"xp": 8, "happiness": 10},
                "choices": [
                    {"text": "Gather everything", "reward": {"xp": 8, "happiness": 10}},
                    {"text": "Pick carefully", "reward": {"xp": 5, "happiness": 12}},
                ],
            },
            "lost_pet": {
                "type": "lost_pet",
                "intro": f"{name} heard a small cry from behind a bush. A lost baby animal!",
                "choices": [
                    {"text": "Help it find home", "reward": {"xp": 20, "happiness": 20}},
                    {"text": "Leave food nearby", "reward": {"xp": 10, "happiness": 10}},
                    {"text": "Let nature take its course", "reward": {"xp": 2, "happiness": -5}},
                ],
                "reward": {"xp": 15, "happiness": 15},
            },
            "weather": {
                "type": "weather",
                "intro": random.choice([
                    f"A sudden rainbow appeared! {name} is mesmerized.",
                    f"It started snowing softly. {name} tries to catch flakes.",
                    f"A warm breeze carries cherry blossoms past {name}.",
                ]),
                "choices": [
                    {"text": "Enjoy the moment", "reward": {"xp": 5, "happiness": 15}},
                    {"text": "Take a photo (mentally)", "reward": {"xp": 8, "happiness": 10}},
                ],
                "reward": {"xp": 5, "happiness": 12},
            },
            "storyteller": {
                "type": "storyteller",
                "intro": f"An old traveler sits by the path. 'Sit, {name}. Let me tell you a tale...'",
                "choices": [
                    {"text": "Listen to the story", "reward": {"xp": 15, "happiness": 10}},
                    {"text": "Tell your own story", "reward": {"xp": 10, "happiness": 12}},
                    {"text": "Politely decline", "reward": {"xp": 3, "happiness": 0}},
                ],
                "reward": {"xp": 12, "happiness": 10},
            },
            "challenge": {
                "type": "challenge",
                "intro": f"A rival {species} appears! They want to see who's tougher.",
                "choices": [
                    {"text": "Accept the challenge!", "reward": {"xp": 20, "happiness": 5}},
                    {"text": "Offer friendship instead", "reward": {"xp": 10, "happiness": 20}},
                    {"text": "Run away", "reward": {"xp": 5, "happiness": -3}},
                ],
                "reward": {"xp": 15, "happiness": 8},
            },
        }

        encounter = encounters.get(enc_type, encounters["weather"])
        encounter["generated_at"] = _time.time()
        return encounter

    @router.post("/api/v1/companion/adventure/choose")
    async def api_adventure_choose(request: Request):
        """Submit a choice for an adventure and receive rewards.

        Body: { "encounter_type": "riddle", "choice_index": 0 }
        Returns: rewards applied, signed result.
        """
        import time as _time
        from plugins.companion.sim import load_state, save_state
        from plugins.companion.adventure_guard import sign_adventure_result

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        body = await request.json()
        enc_type = body.get("encounter_type", "")
        choice_idx = body.get("choice_index", 0)
        choice_rewards = body.get("rewards", {})

        # Default rewards if not provided
        xp = choice_rewards.get("xp", 5)
        happiness = choice_rewards.get("happiness", 5)

        # Apply rewards
        state["happiness"] = min(100, state.get("happiness", 50) + happiness)
        xp_before = state.get("xp", 0)
        state["xp"] = xp_before + xp

        # Check level up
        level = state.get("level", 1)
        xp_needed = level * 100
        leveled_up = False
        if state["xp"] >= xp_needed:
            state["level"] = level + 1
            state["xp"] -= xp_needed
            leveled_up = True

        save_state(state)

        # Sign the result
        timestamp = _time.time()
        rewards = {"xp": xp, "happiness": happiness}
        signature = sign_adventure_result(enc_type, choice_idx, rewards, timestamp)

        return {
            "ok": True,
            "rewards": rewards,
            "leveled_up": leveled_up,
            "new_level": state.get("level", 1),
            "signature": signature,
            "timestamp": timestamp,
        }

    # --- Sprint 4: Daily Gift endpoints (Task 2) ---

    @router.get("/api/v1/companion/daily-gift")
    async def api_daily_gift_check():
        """Check if daily gift is available.

        Returns today's gift (species-specific) or null if already claimed.
        """
        import random
        import time as _time
        from plugins.companion.sim import load_state

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        last_gift = state.get("last_daily_gift", 0)
        if (_time.time() - last_gift) < 86400:
            return {
                "ok": True,
                "available": False,
                "next_gift_in": int(86400 - (_time.time() - last_gift)),
                "message": "You already claimed your daily gift! Come back tomorrow.",
            }

        species = state.get("species", "cat")
        gift = _generate_daily_gift(species, state.get("name", "Companion"))

        return {
            "ok": True,
            "available": True,
            "gift": gift,
        }

    def _generate_daily_gift(species: str, name: str) -> dict:
        """Create a species-specific daily gift."""
        import random

        gifts = {
            "cat": [
                {"type": "poem", "content": f"{name} wrote you a haiku:\nSunbeam on the floor\nI chase it with no regrets\nNap time comes again", "emoji": "📝"},
                {"type": "item", "item": "lucky_whisker", "content": f"{name} found a lucky whisker for you!", "emoji": "🐱"},
                {"type": "fact", "content": f"{name} learned that cats can rotate their ears 180 degrees!", "emoji": "🧠"},
                {"type": "compliment", "content": f"{name} thinks you're the best human ever!", "emoji": "💕"},
            ],
            "dog": [
                {"type": "item", "item": "golden_bone", "content": f"{name} dug up something special!", "emoji": "🦴"},
                {"type": "poem", "content": f"{name} barks a song:\nTail wagging so fast\nEvery walk is an adventure\nYou are my best friend", "emoji": "📝"},
                {"type": "compliment", "content": f"{name} would fetch you the moon if they could!", "emoji": "💕"},
            ],
            "penguin": [
                {"type": "item", "item": "smooth_pebble", "content": f"{name} found the smoothest pebble for you!", "emoji": "🪨"},
                {"type": "fact", "content": f"{name} learned that penguins propose with pebbles!", "emoji": "🧠"},
                {"type": "advice", "content": f"{name} says: 'Waddle with purpose, even when you don't know where you're going.'", "emoji": "🐧"},
            ],
            "fox": [
                {"type": "item", "item": "forest_gem", "content": f"{name} found a gem hidden under autumn leaves!", "emoji": "💎"},
                {"type": "fact", "content": f"{name} learned that foxes use the Earth's magnetic field to hunt!", "emoji": "🧠"},
                {"type": "compliment", "content": f"{name} thinks you're as clever as a fox!", "emoji": "🦊"},
            ],
            "owl": [
                {"type": "item", "item": "wisdom_feather", "content": f"{name} dropped a feather of wisdom!", "emoji": "🪶"},
                {"type": "fact", "content": f"{name} counted exactly 147 stars last night.", "emoji": "🧠"},
                {"type": "advice", "content": f"{name} says: 'Knowledge is the one treasure that grows when shared.'", "emoji": "🦉"},
            ],
            "dragon": [
                {"type": "item", "item": "ember_crystal", "content": f"{name} breathed fire and crystallized something for you!", "emoji": "🔥"},
                {"type": "poem", "content": f"{name} roars a verse:\nScales of ancient gold\nFire burns but never consumes\nI warm your cold days", "emoji": "📝"},
                {"type": "compliment", "content": f"{name} says: 'Even dragons need a hero. You're mine.'", "emoji": "🐉"},
            ],
        }

        species_gifts = gifts.get(species, gifts["cat"])
        return random.choice(species_gifts)

    @router.post("/api/v1/companion/daily-gift/claim")
    async def api_daily_gift_claim():
        """Claim the daily gift. Applies rewards."""
        import time as _time
        from plugins.companion.sim import load_state, save_state

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        last_gift = state.get("last_daily_gift", 0)
        if (_time.time() - last_gift) < 86400:
            raise HTTPException(400, "Daily gift already claimed. Come back tomorrow!")

        species = state.get("species", "cat")
        gift = _generate_daily_gift(species, state.get("name", "Companion"))

        # Apply gift rewards
        state["last_daily_gift"] = _time.time()
        state["happiness"] = min(100, state.get("happiness", 50) + 10)
        state["xp"] = state.get("xp", 0) + 5

        # Add item to inventory if it's an item gift
        if gift.get("type") == "item" and gift.get("item"):
            inventory = state.get("inventory", [])
            # Check if already has this item
            found = False
            for slot in inventory:
                if slot.get("item") == gift["item"]:
                    slot["count"] = slot.get("count", 1) + 1
                    found = True
                    break
            if not found and len(inventory) < 20:
                inventory.append({"item": gift["item"], "count": 1, "emoji": gift.get("emoji", "🎁")})
            state["inventory"] = inventory

        save_state(state)

        return {
            "ok": True,
            "gift": gift,
            "rewards": {"happiness": 10, "xp": 5},
        }

    app.include_router(router)
    log.info("[companion] Plugin loaded (with translation + guardian + mobile + chat + push + adventures + gifts).")

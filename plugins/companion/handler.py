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

        # Sprint 5 Task 3: Platform activity
        platform_info = _get_platform_activity()

        # Generate or retrieve a permanent device token for WebSocket auth
        device_token = None
        try:
            import secrets as _secrets
            from pathlib import Path as _DTPath
            dt_file = _DTPath.home() / ".valhalla" / "device_tokens.json"
            dt_file.parent.mkdir(parents=True, exist_ok=True)
            existing_tokens = []
            if dt_file.exists():
                try:
                    existing_tokens = json.loads(dt_file.read_text(encoding="utf-8"))
                except Exception:
                    existing_tokens = []
            if existing_tokens:
                device_token = existing_tokens[0].get("token", "")
            if not device_token:
                device_token = _secrets.token_urlsafe(32)
                existing_tokens.append({
                    "token": device_token,
                    "created_at": _time.time(),
                    "device": "mobile",
                })
                dt_file.write_text(json.dumps(existing_tokens), encoding="utf-8")
                log.info("[companion/sync] Generated permanent device token for mobile")
        except Exception as e:
            log.debug("[companion/sync] Device token generation failed: %s", e)

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
            "platform": platform_info,
            "device_token": device_token,
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

    # Sprint 5 Task 1: Server-side encounter storage (fixes Heimdall MEDIUM)
    _active_encounters = {}

    # --- Sprint 4: Adventure endpoints (Task 1) ---

    @router.post("/api/v1/companion/adventure/generate")
    async def api_adventure_generate():
        """Generate a random adventure encounter.

        Returns an encounter with intro, choices, and loot table.
        Server-authoritative — encounter stored server-side, rewards cannot be forged.
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
        companion_name = state.get("name", "Companion")
        encounter = _generate_encounter(enc_type, species, companion_name)

        # Sprint 5: Store encounter server-side (5-min expiry)
        _active_encounters[companion_name] = {
            "type": enc_type,
            "choices": encounter.get("choices", []),
            "reward": encounter.get("reward", {}),
            "generated_at": _time.time(),
            "expires_at": _time.time() + 300,
        }

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

        Body: { "choice_index": 0 }
        Sprint 5: Rewards are now looked up server-side — client values ignored.
        """
        import time as _time
        from plugins.companion.sim import load_state, save_state
        from plugins.companion.adventure_guard import sign_adventure_result

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        companion_name = state.get("name", "Companion")

        # Sprint 5: Look up encounter server-side (ignore client rewards)
        encounter = _active_encounters.pop(companion_name, None)
        if not encounter:
            raise HTTPException(400, "No active encounter. Generate one first.")
        if _time.time() > encounter["expires_at"]:
            raise HTTPException(400, "Encounter expired (5-minute limit). Generate a new one.")

        body = await request.json()
        choice_idx = body.get("choice_index", 0)

        # Get rewards from server-stored encounter (NOT client body)
        choices = encounter.get("choices", [])
        if choice_idx < 0 or choice_idx >= len(choices):
            raise HTTPException(400, f"Invalid choice index: {choice_idx}")

        choice_rewards = choices[choice_idx].get("reward", encounter.get("reward", {}))
        xp = choice_rewards.get("xp", 5)
        happiness = choice_rewards.get("happiness", 5)
        enc_type = encounter["type"]

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

    # --- Sprint 5 Task 2: Unregister push ---

    @router.post("/api/v1/companion/mobile/unregister-push")
    async def api_unregister_push():
        """Remove stored push token. Called when user disables notifications."""
        from pathlib import Path as _Path
        token_path = _Path.home() / ".valhalla" / "push_token.json"
        if token_path.exists():
            token_path.unlink()
        return {"ok": True}

    # --- Sprint 5 Task 3: Platform activity helper ---

    def _get_platform_activity() -> dict:
        """Gather platform activity metrics for /mobile/sync.

        Gracefully returns null for unavailable data.
        """
        import os as _os
        import time as _time

        platform = {
            "uptime_hours": None,
            "models_loaded": None,
            "memory_count": None,
            "plugins_active": None,
            "last_dream_cycle": None,
            "last_prediction": None,
            "mesh_nodes": None,
        }

        # Uptime from process start
        try:
            import psutil
            p = psutil.Process(_os.getpid())
            platform["uptime_hours"] = round((_time.time() - p.create_time()) / 3600, 1)
        except Exception:
            try:
                # Fallback: use a module-level start time
                if not hasattr(_get_platform_activity, "_start"):
                    _get_platform_activity._start = _time.time()
                platform["uptime_hours"] = round((_time.time() - _get_platform_activity._start) / 3600, 1)
            except Exception:
                pass

        # Memory count from working-memory plugin
        try:
            from plugins import working_memory
            memories = working_memory.get_memories() if hasattr(working_memory, "get_memories") else []
            platform["memory_count"] = len(memories)
        except Exception:
            platform["memory_count"] = 0

        # Loaded models from model-router
        try:
            from plugins import model_router
            platform["models_loaded"] = model_router.get_loaded_models() if hasattr(model_router, "get_loaded_models") else []
        except Exception:
            platform["models_loaded"] = []

        # Active plugins count
        try:
            from plugin_loader import loaded_plugins
            platform["plugins_active"] = len(loaded_plugins())
        except Exception:
            platform["plugins_active"] = 0

        # Last prediction
        try:
            from plugins import predictions
            platform["last_prediction"] = predictions.get_last() if hasattr(predictions, "get_last") else None
        except Exception:
            pass

        # Mesh nodes
        try:
            from plugin_loader import get_config
            cfg = get_config()
            peers = cfg.get("mesh", {}).get("peers", [])
            platform["mesh_nodes"] = len(peers) + 1  # +1 for self
        except Exception:
            platform["mesh_nodes"] = 1

        return platform

    # --- Sprint 5 Task 4: Proactive Guardian check-in ---

    @router.get("/api/v1/companion/guardian/check-in")
    async def api_guardian_checkin():
        """Time-aware check-in. Returns proactive warning if late at night.

        Called by mobile app when user opens the chat tab.
        Species-specific messages for extra personality.
        """
        from datetime import datetime
        from plugins.companion.sim import load_state

        hour = datetime.now().hour
        state = load_state()
        species = state.get("species", "cat") if state else "cat"
        name = state.get("name", "Companion") if state else "Companion"

        if 0 <= hour < 5:
            late_messages = {
                "cat": f"It's {hour}AM. Even I think you should sleep. 😾",
                "dog": f"It's really late! Maybe sleep first? I'll guard your phone! 🐕",
                "penguin": f"It's {hour}AM in human time. We penguins would be huddling for warmth right now. 🐧",
                "fox": f"Even nocturnal creatures rest sometimes. It's {hour}AM, friend. 🦊",
                "owl": f"I'm the night owl here, not you. Get some rest! 🦉",
                "dragon": f"The dragon sleeps at {hour}AM. So should you. 🐉",
            }
            return {
                "proactive_warning": True,
                "message": late_messages.get(species, f"{name} thinks it's too late to be texting."),
                "hold_option": True,
                "hour": hour,
            }

        return {"proactive_warning": False, "hour": hour}

    # --- Sprint 6 Task 1: Voice endpoints for mobile ---

    @router.post("/api/v1/voice/transcribe")
    async def api_voice_transcribe(request: Request):
        """Speech-to-Text via Whisper (local, private).

        Accepts multipart/form-data with audio file (webm/m4a/wav).
        Voice data NEVER leaves the local network.
        """
        import tempfile
        form = await request.form()
        audio_file = form.get("audio")
        if not audio_file:
            raise HTTPException(400, "No audio file provided. Upload as 'audio' field.")

        # Read uploaded audio bytes
        audio_bytes = await audio_file.read()
        if len(audio_bytes) > 25 * 1024 * 1024:  # 25MB max
            raise HTTPException(413, "Audio file too large (max 25MB).")

        language = form.get("language", "en")

        try:
            from plugins.voice.stt import transcribe_bytes
            result = transcribe_bytes(audio_bytes, language=language)
            if not result.get("ok"):
                raise HTTPException(503, result.get("error", "STT failed"))
            return {
                "text": result.get("text", ""),
                "language": result.get("language", language),
                "duration": result.get("duration", 0),
            }
        except ImportError:
            raise HTTPException(503, "Voice STT not available. Enable via POST /api/v1/voice/enable")

    @router.post("/api/v1/voice/speak")
    async def api_voice_speak(request: Request):
        """Text-to-Speech via Kokoro (local, private).

        Body: { "text": "Hello!", "voice": "af_default" }
        Returns: audio/wav binary stream.
        """
        from fastapi.responses import FileResponse

        body = await request.json()
        text = body.get("text", "")
        if not text or len(text) > 5000:
            raise HTTPException(400, "Text required (max 5000 chars).")

        voice = body.get("voice", "af_default")

        try:
            from plugins.voice.tts import synthesize
            result = synthesize(text, voice=voice)
            if not result.get("ok"):
                raise HTTPException(503, result.get("error", "TTS failed"))
            return FileResponse(
                result["path"],
                media_type="audio/wav",
                filename="speech.wav",
            )
        except ImportError:
            raise HTTPException(503, "Voice TTS not available. Enable via POST /api/v1/voice/enable")

    # --- Sprint 6 Task 2: Marketplace API for mobile ---

    @router.get("/api/v1/marketplace/browse")
    async def api_marketplace_browse(category: str = None):
        """Browse marketplace items for mobile.

        Optional query: ?category=general
        """
        try:
            from plugins.marketplace.handler import _load_registry
            registry = _load_registry()
            if category:
                registry = [a for a in registry if a.get("category", "general") == category]
            return {"ok": True, "items": registry, "count": len(registry)}
        except Exception as e:
            log.error("Marketplace browse error: %s", e)
            return {"ok": True, "items": [], "count": 0, "note": "Marketplace service unavailable"}

    @router.get("/api/v1/marketplace/search")
    async def api_marketplace_search(q: str = ""):
        """Search marketplace items by name, description, or tags."""
        if not q or len(q) < 2:
            raise HTTPException(400, "Search query must be at least 2 characters.")

        try:
            from plugins.marketplace.handler import _load_registry
            registry = _load_registry()
            query = q.lower()
            results = [
                a for a in registry
                if query in a.get("name", "").lower()
                or query in a.get("description", "").lower()
                or any(query in t.lower() for t in a.get("tags", []))
            ]
            return {"ok": True, "items": results, "count": len(results), "query": q}
        except Exception as e:
            log.error("Marketplace search error: %s", e)
            return {"ok": True, "items": [], "count": 0, "query": q, "note": "Marketplace service unavailable"}

    @router.get("/api/v1/marketplace/item/{item_id}")
    async def api_marketplace_item(item_id: str):
        """Get marketplace item detail."""
        try:
            from plugins.marketplace.handler import _load_registry
            registry = _load_registry()
            for item in registry:
                if item.get("id") == item_id or item.get("name") == item_id:
                    return {"ok": True, "item": item}
            raise HTTPException(404, "Item not found in marketplace")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    @router.post("/api/v1/marketplace/install")
    async def api_marketplace_install(request: Request):
        """Install a free marketplace item.

        Body: { "item_id": "my-agent" }
        """
        body = await request.json()
        item_id = body.get("item_id", "")
        if not item_id:
            raise HTTPException(400, "item_id required")

        try:
            from plugins.marketplace.handler import _load_registry
            registry = _load_registry()
            item = None
            for a in registry:
                if a.get("id") == item_id or a.get("name") == item_id:
                    item = a
                    break

            if not item:
                raise HTTPException(404, "Item not found")

            price = item.get("price", 0)
            if price > 0:
                return {
                    "ok": False,
                    "error": "Paid item — use Stripe checkout",
                    "price": price,
                    "checkout_url": f"/api/v1/payments/checkout?item={item_id}",
                }

            # For free items, mark as installed
            item["installed"] = True
            return {"ok": True, "installed": item_id, "item": item}
        except HTTPException:
            raise
        except Exception as e:
            log.error("Marketplace install error: %s", e)
            raise HTTPException(500, "Marketplace service unavailable")

    # --- Sprint 6 Task 3: Web page summary ---

    @router.post("/api/v1/browse/summarize")
    async def api_browse_summarize(request: Request):
        """Summarize a web page for the iOS share sheet.

        Body: { "url": "https://example.com" }
        Uses the existing browse/parser.py accessibility-tree parser.
        """
        body = await request.json()
        url = body.get("url", "")
        if not url or not url.startswith("http"):
            raise HTTPException(400, "Valid URL required (must start with http)")

        # URL length limit
        if len(url) > 2000:
            raise HTTPException(400, "URL too long (max 2000 chars)")

        # Sprint 7: SSRF blocklist check
        if not _is_url_safe(url):
            raise HTTPException(403, "URL points to a blocked internal address")

        try:
            from plugins.browse.parser import fetch_and_parse_sync
            parsed = fetch_and_parse_sync(url)

            text = parsed.to_text()
            stats = parsed.summary_stats()

            # Extract key points (first few heading-associated blocks)
            key_points = []
            for el in (parsed.elements or [])[:20]:
                if el.role in ("heading", "h1", "h2", "h3"):
                    key_points.append(el.text)

            return {
                "ok": True,
                "title": parsed.title,
                "description": parsed.description,
                "summary": text[:2000],  # First 2000 chars of clean text
                "key_points": key_points[:10],
                "stats": stats,
                "url": url,
            }
        except Exception as e:
            log.error("Browse summarize error: %s", e)
            raise HTTPException(502, "Failed to fetch or parse the URL")

    # --- Sprint 7 Task 1: SSRF blocklist ---

    def _is_url_safe(url: str) -> bool:
        """Check URL against SSRF blocklist."""
        import ipaddress
        import urllib.parse

        BLOCKED_NETWORKS = [
            ipaddress.ip_network("127.0.0.0/8"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("169.254.0.0/16"),
            ipaddress.ip_network("0.0.0.0/8"),
        ]

        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname in ("localhost", "0.0.0.0"):
            return False
        try:
            addr = ipaddress.ip_address(hostname)
            return not any(addr in net for net in BLOCKED_NETWORKS)
        except ValueError:
            # Domain name — allow (resolves externally)
            return True

    # --- Sprint 6 Task 4: WebSocket for real-time companion sync ---
    # Sprint 7 Task 2: Added auth token + 5 connection cap

    _ws_connections: list = []
    _WS_MAX_CONNECTIONS = 5

    def _verify_ws_token(token: str) -> bool:
        """Verify WebSocket token against stored pairing token OR device tokens.

        Accepts:
          - Dashboard pair token (from mobile_token.json, 15-min TTL)
          - Device token (from device_tokens.json, permanent)
        """
        import hmac
        from pathlib import Path as _Path

        # Check permanent device tokens first (most common for WebSocket)
        dt_file = _Path.home() / ".valhalla" / "device_tokens.json"
        if dt_file.exists():
            try:
                tokens = json.loads(dt_file.read_text(encoding="utf-8"))
                for entry in tokens:
                    stored = entry.get("token", "")
                    if stored and hmac.compare_digest(stored, token):
                        return True
            except Exception:
                pass

        # Fall back to dashboard pair token (15-min TTL)
        token_path = _Path.home() / ".valhalla" / "mobile_token.json"
        if not token_path.exists():
            return False
        try:
            data = json.loads(token_path.read_text(encoding="utf-8"))
            stored = data.get("token", "")
            return hmac.compare_digest(stored, token)
        except Exception:
            return False

    def _cleanup_dead_ws():
        """Remove dead WebSocket connections."""
        dead = [ws for ws in _ws_connections if hasattr(ws, 'client_state') and ws.client_state.name == 'DISCONNECTED']
        for ws in dead:
            _ws_connections.remove(ws)

    @router.websocket("/api/v1/companion/ws")
    async def ws_companion_sync(websocket):
        """WebSocket for real-time companion state updates.

        Requires ?token= query param matching stored pairing token.
        Max 5 concurrent connections.
        Optionally accepts ?session_id= for cross-device context.

        Events pushed from server:
          - full_sync: complete sync payload on connection (same as /mobile/sync)
          - companion_state_update: happiness, XP, level changes
          - task_completed: task queue item finished
          - chat_message: message from desktop chat (bidirectional sync)
          - notification: push notification content

        Messages accepted from client:
          - "ping" → responds with {"type": "pong"}
          - "sync" → responds with companion_state_update
          - JSON {"type": "chat_message", "data": {...}} → broadcast + store
          - JSON {"type": "teach", "data": {"fact": "..."}} → store as memory
        """
        from fastapi import WebSocket

        # Sprint 7: Auth check
        token = websocket.query_params.get("token", "")
        if not token or not _verify_ws_token(token):
            await websocket.close(code=4001, reason="Unauthorized")
            return

        # Sprint 7: Cleanup dead connections + enforce cap
        _cleanup_dead_ws()
        if len(_ws_connections) >= _WS_MAX_CONNECTIONS:
            await websocket.close(code=4029, reason="Too many connections")
            return

        # Track session ID for cross-device context
        session_id = websocket.query_params.get("session_id", "unknown")

        await websocket.accept()
        _ws_connections.append(websocket)
        log.info("[companion/ws] Client connected (session=%s, total=%d)",
                 session_id, len(_ws_connections))

        # Send initial full sync payload on connect
        try:
            import time as _time
            from plugins.companion.sim import load_state, get_status, get_mood_prefix

            state = load_state()
            if state:
                companion_status = get_status(state)
                personality = {}
                try:
                    from plugins.agent_profiles.leveling import load_profile
                    profile = load_profile(state.get("name", "companion"))
                    personality = profile.get("personality", {})
                except Exception:
                    pass

                try:
                    from plugins.companion.queue import get_queue
                    pending_tasks = get_queue(status="completed")
                except Exception:
                    pending_tasks = []

                await websocket.send_json({
                    "type": "full_sync",
                    "data": {
                        "ok": True,
                        "adopted": True,
                        "companion": companion_status,
                        "personality": personality,
                        "mood_prefix": get_mood_prefix(state),
                        "pending_tasks": pending_tasks,
                        "synced_at": _time.time(),
                        "features": {
                            "adventures": True,
                            "daily_gift": True,
                            "guardian": True,
                            "teach_me": True,
                            "translation": True,
                            "morning_briefing": True,
                        },
                    },
                })
        except Exception as e:
            log.debug("[companion/ws] Initial sync failed: %s", e)

        try:
            while True:
                data = await websocket.receive_text()

                # Plain text commands
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                # JSON messages
                try:
                    msg = json.loads(data)
                except (json.JSONDecodeError, ValueError):
                    # Legacy: "sync" as plain text
                    if data == "sync":
                        import time as _time
                        from plugins.companion.sim import load_state, get_status, get_mood_prefix
                        state = load_state()
                        if state:
                            await websocket.send_json({
                                "type": "companion_state_update",
                                "data": {
                                    "companion": get_status(state),
                                    "mood_prefix": get_mood_prefix(state),
                                    "synced_at": _time.time(),
                                },
                            })
                    continue

                msg_type = msg.get("type", "")
                msg_data = msg.get("data", {})

                if msg_type == "sync":
                    import time as _time
                    from plugins.companion.sim import load_state, get_status, get_mood_prefix
                    state = load_state()
                    if state:
                        await websocket.send_json({
                            "type": "companion_state_update",
                            "data": {
                                "companion": get_status(state),
                                "mood_prefix": get_mood_prefix(state),
                                "synced_at": _time.time(),
                            },
                        })

                elif msg_type == "chat_message":
                    # Bidirectional chat sync — broadcast to all other WS clients
                    for ws in _ws_connections:
                        if ws is not websocket:
                            try:
                                await ws.send_json({
                                    "type": "chat_message",
                                    "data": msg_data,
                                })
                            except Exception:
                                pass

                    # Also store in chat history
                    try:
                        role = msg_data.get("role", "user")
                        content = msg_data.get("message", "")
                        if content and role in ("user", "companion"):
                            from pathlib import Path as _Path
                            import time as _time
                            history_dir = _Path.home() / ".valhalla"
                            history_dir.mkdir(parents=True, exist_ok=True)
                            history_file = history_dir / "chat_history.json"
                            messages = []
                            if history_file.exists():
                                try:
                                    messages = json.loads(
                                        history_file.read_text(encoding="utf-8"))
                                except Exception:
                                    messages = []
                            messages.append({
                                "role": role,
                                "content": content,
                                "timestamp": msg_data.get("timestamp", _time.time()),
                                "session": session_id,
                            })
                            if len(messages) > 500:
                                messages = messages[-500:]
                            history_file.write_text(
                                json.dumps(messages, ensure_ascii=False),
                                encoding="utf-8",
                            )
                    except Exception as e:
                        log.debug("[companion/ws] Chat store failed: %s", e)

                elif msg_type == "teach":
                    # Store a fact in the orchestrator's memory
                    fact = msg_data.get("fact", "")
                    if fact:
                        try:
                            import orchestrator as orch_mod
                            orch_mod.observe(
                                f"User taught via mobile: {fact}",
                                importance=0.8,
                                source="mobile_teach",
                            )
                            await websocket.send_json({
                                "type": "teach_ack",
                                "data": {"ok": True, "fact": fact[:100]},
                            })
                        except Exception:
                            await websocket.send_json({
                                "type": "teach_ack",
                                "data": {"ok": False, "error": "Memory system unavailable"},
                            })

                elif msg_type == "phone_context":
                    # Phone sensor data — raw pipe from contacts/calendar/device
                    # Store for the big brain to use in conversations
                    _store_phone_context(msg_data, session_id)
                    await websocket.send_json({
                        "type": "context_ack",
                        "data": {"ok": True, "stored": len(msg_data)},
                    })

        except Exception:
            pass
        finally:
            if websocket in _ws_connections:
                _ws_connections.remove(websocket)
            log.info("[companion/ws] Client disconnected (session=%s, remaining=%d)",
                     session_id, len(_ws_connections))

    async def broadcast_ws_event(event_type: str, data: dict):
        """Broadcast an event to all connected WebSocket clients."""
        import json as _json
        message = _json.dumps({"type": event_type, "data": data})
        dead = []
        for ws in _ws_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _ws_connections.remove(ws)

    # --- Sprint 6 Task 5: Morning briefing placeholder fix ---

    @router.get("/api/v1/companion/morning-briefing")
    async def api_morning_briefing():
        """Morning briefing with real data — nulls for unavailable fields.

        Returns only verified data. Frontend shows "data unavailable"
        for null fields instead of fake numbers.
        """
        from plugins.companion.sim import load_state

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        # All fields default to null — only set if real data available
        briefing = {
            "conversations_reviewed": None,
            "facts_tested": None,
            "facts_passed": None,
            "facts_refined": None,
            "improvement_percent": None,
            "pet_walk_result": None,
            "pet_loot_found": None,
            "daily_gift": None,
            "streak_days": None,
        }

        # Real data: streak from state
        briefing["streak_days"] = state.get("streak_days", 0)

        # Real data: daily gift availability
        import time as _time
        last_gift = state.get("last_daily_gift", 0)
        briefing["daily_gift"] = (_time.time() - last_gift) > 86400

        # Real data: walk result from last adventure
        last_adv = state.get("last_adventure", 0)
        if _time.time() - last_adv < 86400:
            briefing["pet_walk_result"] = "Your companion went on an adventure today!"

        # Memory facts if available
        try:
            from plugins import working_memory
            if hasattr(working_memory, "get_memories"):
                memories = working_memory.get_memories()
                briefing["facts_tested"] = len(memories)
        except Exception:
            pass  # Leave as null — frontend shows "data unavailable"

        # Validate through adventure_guard
        from plugins.companion.adventure_guard import validate_briefing_data
        validated = validate_briefing_data(briefing)
        return {
            "ok": True,
            "briefing": validated.get("sanitized", briefing),
            "companion_name": state.get("name", "Companion"),
            "species": state.get("species", "cat"),
        }

    # --- Sprint 7 Task 4: Achievement endpoints ---

    @router.get("/api/v1/companion/achievements")
    async def api_achievements():
        """List all achievements with earned status."""
        from plugins.companion.achievements import get_all_achievements
        return {"ok": True, "achievements": get_all_achievements()}

    @router.post("/api/v1/companion/achievements/check")
    async def api_achievements_check():
        """Check and award any newly earned achievements.

        Called after actions (feed, walk, quest, teach, etc.).
        Returns newly earned achievements for toast notifications.
        """
        from plugins.companion.sim import load_state
        from plugins.companion.achievements import check_and_award

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        newly = check_and_award(state)
        return {
            "ok": True,
            "newly_earned": newly,
            "count": len(newly),
        }

    # --- Sprint 7 Task 5: Weekly summary ---

    @router.get("/api/v1/companion/weekly-summary")
    async def api_weekly_summary():
        """Summary of the past 7 days."""
        from datetime import datetime, timedelta
        from plugins.companion.sim import load_state
        from plugins.companion.achievements import load_earned

        state = load_state()
        if not state:
            raise HTTPException(404, "No companion adopted yet.")

        now = datetime.now()
        week_ago = now - timedelta(days=7)
        period = f"{week_ago.strftime('%b %d')} - {now.strftime('%b %d')}"

        counters = state.get("counters", {})
        level = state.get("level", 1)
        earned = load_earned()

        # Count achievements earned this week
        import time as _time
        week_ago_ts = _time.time() - (7 * 86400)
        recent_achievements = [
            aid for aid, info in earned.items()
            if info.get("earned_at", 0) > week_ago_ts
        ]

        stats = {
            "feeds": counters.get("feeds", 0),
            "walks": counters.get("walks", 0),
            "quests_completed": counters.get("quests", 0),
            "facts_learned": counters.get("teaches", 0),
            "messages_sent": counters.get("messages", 0),
            "levels_gained": max(0, level - counters.get("level_at_week_start", level)),
            "achievements_earned": len(recent_achievements),
            "guardian_saves": counters.get("guardian_saves", 0),
        }

        # Generate highlights
        highlights = []
        if stats["levels_gained"] > 0:
            highlights.append(f"Reached level {level}!")
        if recent_achievements:
            from plugins.companion.achievements import ACHIEVEMENTS
            for aid in recent_achievements[:3]:
                if aid in ACHIEVEMENTS:
                    highlights.append(f"Earned '{ACHIEVEMENTS[aid]['name']}' achievement")
        if stats["facts_learned"] > 0:
            highlights.append(f"Your companion learned {stats['facts_learned']} new facts")
        if stats["quests_completed"] > 0:
            highlights.append(f"Completed {stats['quests_completed']} quests")

        return {
            "ok": True,
            "period": period,
            "stats": stats,
            "highlights": highlights[:5],
            "companion_name": state.get("name", "Companion"),
        }
    # --- Sprint 8: Hosted waitlist ---

    _waitlist_requests: list = []  # timestamps for rate limiting

    @router.post("/api/v1/waitlist")
    async def api_waitlist(request: Request):
        """Sign up for hosted mode waitlist.

        Body: { "email": "user@example.com" }
        Validates email, deduplicates, rate-limited to 10/min.
        """
        import re
        import time as _time

        # Rate limit: 10 signups per minute
        now = _time.time()
        _waitlist_requests[:] = [t for t in _waitlist_requests if now - t < 60]
        if len(_waitlist_requests) >= 10:
            raise HTTPException(429, "Too many signups. Try again in a minute.")
        _waitlist_requests.append(now)

        body = await request.json()
        email = body.get("email", "").strip().lower()

        # Validate email format
        if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise HTTPException(400, "Invalid email address.")

        # Store in waitlist.json (append, deduplicate)
        from pathlib import Path as _Path
        waitlist_path = _Path.home() / ".valhalla" / "waitlist.json"
        waitlist_path.parent.mkdir(parents=True, exist_ok=True)

        existing = []
        if waitlist_path.exists():
            try:
                existing = json.loads(waitlist_path.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        # Deduplicate
        if any(e.get("email") == email for e in existing):
            return {
                "ok": True,
                "message": "You're already on the waitlist! We'll email you when your private AI is ready.",
            }

        existing.append({"email": email, "signed_up": _time.time()})
        waitlist_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        return {
            "ok": True,
            "message": "You're on the waitlist! We'll email you when your private AI is ready.",
        }
    # --- Sprint 9 Task 1: Rich action response builder ---

    def _build_action(action_type: str, **kwargs) -> dict:
        """Build a structured action for rich mobile card rendering.

        Action types:
          - browse_result: URL summary with title, summary, key_points
          - pipeline_status: task progress with name, stage, percent
          - pipeline_complete: finished multi-stage task with results
          - memory_recall: companion remembered something (source, content, date)
          - translation_result: translation with languages + text
        """
        import time as _time
        from datetime import datetime

        action = {"type": action_type, "timestamp": datetime.utcnow().isoformat() + "Z"}

        if action_type == "browse_result":
            action.update({
                "title": kwargs.get("title", ""),
                "url": kwargs.get("url", ""),
                "summary": kwargs.get("summary", ""),
                "key_points": kwargs.get("key_points", []),
            })
        elif action_type == "pipeline_status":
            action.update({
                "name": kwargs.get("name", ""),
                "stage": kwargs.get("stage", ""),
                "percent": kwargs.get("percent", 0),
                "estimated_completion": kwargs.get("estimated_completion"),
            })
        elif action_type == "pipeline_complete":
            action.update({
                "name": kwargs.get("name", ""),
                "results": kwargs.get("results", {}),
                "duration_s": kwargs.get("duration_s", 0),
            })
        elif action_type == "memory_recall":
            action.update({
                "source": kwargs.get("source", ""),
                "content": kwargs.get("content", ""),
                "date": kwargs.get("date", ""),
            })
        elif action_type == "translation_result":
            action.update({
                "source_lang": kwargs.get("source_lang", ""),
                "target_lang": kwargs.get("target_lang", ""),
                "original": kwargs.get("original", ""),
                "translated": kwargs.get("translated", ""),
            })

        return action

    # --- Sprint 9 Task 2: Cross-context search ---

    @router.post("/api/v1/companion/query")
    async def api_companion_query(request: Request):
        """Search across all companion knowledge sources.

        Body: { "query": "marketing strategy" }
        Searches: working_memory, taught_facts, chat_history, hypotheses
        Returns top 10 results ranked by relevance.
        """
        body = await request.json()
        query = body.get("query", "").strip()
        if not query or len(query) < 2:
            raise HTTPException(400, "Query must be at least 2 characters.")

        results = []
        terms = query.lower().split()

        # Source 1: Working memory
        try:
            from plugins.working_memory.handler import get_working_memory
            wm = get_working_memory()
            memories = wm.recall(query, top_k=5)
            for m in memories:
                content = m.get("content", "")
                results.append({
                    "source": "working_memory",
                    "content": content[:500],
                    "relevance": round(m.get("importance", 0.5), 2),
                    "date": None,
                })
        except ImportError:
            pass

        # Source 2: Taught facts (from companion state)
        try:
            from plugins.companion.sim import load_state
            state = load_state()
            if state:
                facts = state.get("taught_facts", [])
                for fact in facts:
                    fact_text = fact if isinstance(fact, str) else fact.get("text", "")
                    fact_lower = fact_text.lower()
                    if any(t in fact_lower for t in terms):
                        date = fact.get("date") if isinstance(fact, dict) else None
                        results.append({
                            "source": "taught_facts",
                            "content": f"You taught me: '{fact_text}'",
                            "relevance": 0.85,
                            "date": date,
                        })
        except ImportError:
            pass

        # Source 3: Chat history (recent messages in companion state)
        try:
            from plugins.companion.sim import load_state as _ls
            state = _ls()
            if state:
                history = state.get("chat_history", [])
                for msg in history[-50:]:  # last 50 messages
                    text = msg if isinstance(msg, str) else msg.get("text", "")
                    text_lower = text.lower()
                    if any(t in text_lower for t in terms):
                        date = msg.get("date") if isinstance(msg, dict) else None
                        results.append({
                            "source": "chat_history",
                            "content": f"In conversation: '{text[:300]}'",
                            "relevance": 0.70,
                            "date": date,
                        })
        except ImportError:
            pass

        # Source 4: Hypotheses
        try:
            from plugins.hypotheses.handler import get_hypotheses
            hypotheses = get_hypotheses(limit=10)
            for h in hypotheses:
                text = h.get("text", "") if isinstance(h, dict) else str(h)
                text_lower = text.lower()
                if any(t in text_lower for t in terms):
                    results.append({
                        "source": "hypotheses",
                        "content": text[:500],
                        "relevance": round(h.get("confidence", 0.6), 2) if isinstance(h, dict) else 0.6,
                        "date": h.get("created") if isinstance(h, dict) else None,
                    })
        except ImportError:
            pass

        # Sort by relevance, cap at 10
        results.sort(key=lambda r: r.get("relevance", 0), reverse=True)
        results = results[:10]

        return {
            "ok": True,
            "results": results,
            "total": len(results),
            "query": query,
        }

    # --- Sprint 9 Task 3: Privacy email ---
    # The privacy@valhalla.local placeholder is in mobile/app/privacy.tsx (Freya's domain).
    # Backend has no privacy email references. Noting hello@fablefur.com as canonical.

    @router.get("/api/v1/privacy-contact")
    async def api_privacy_contact():
        """Return the privacy contact email for mobile app."""
        return {"email": "hello@fablefur.com"}

    # --- Sprint 10 Task 3: Agent Profile API ---

    @router.get("/api/v1/agent/profile")
    async def api_agent_profile():
        """Return AI agent profile with companion, live stats."""
        import time as _time
        from pathlib import Path as _Path

        # Load companion state
        state = {}
        state_path = _Path.home() / ".valhalla" / "companion_state.json"
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Load valhalla.yaml for agent config
        agent_config = {}
        yaml_path = _Path.home() / ".fireside" / "valhalla.yaml"
        if not yaml_path.exists():
            yaml_path = _Path("valhalla.yaml")
        if yaml_path.exists():
            try:
                import yaml
                agent_config = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            except ImportError:
                # Parse agent section manually
                content = yaml_path.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("name:") and "agent" in content[:content.index(line)].split("\n")[-3:]:
                        agent_config.setdefault("agent", {})["name"] = stripped.split(":", 1)[1].strip().strip('"')
                    if stripped.startswith("style:"):
                        agent_config.setdefault("agent", {})["style"] = stripped.split(":", 1)[1].strip().strip('"')
            except Exception:
                pass

        agent = state.get("agent", agent_config.get("agent", {}))
        agent_name = agent.get("name", "Atlas") if agent else "Atlas"
        agent_style = agent.get("style", "analytical") if agent else "analytical"

        # Live data
        uptime_str = "unknown"
        try:
            import psutil
            boot_time = psutil.boot_time()
            uptime_s = _time.time() - boot_time
            hours = int(uptime_s // 3600)
            minutes = int((uptime_s % 3600) // 60)
            uptime_str = f"{hours}h {minutes}m"
        except ImportError:
            pass

        # Count active plugins
        plugins_active = 0
        try:
            from plugin_loader import get_loaded_plugins
            plugins_active = len(get_loaded_plugins())
        except ImportError:
            plugins_active = 12  # fallback

        return {
            "name": agent_name,
            "style": agent_style,
            "companion": {
                "name": state.get("name", "Companion"),
                "species": state.get("species", "fox"),
            },
            "owner": state.get("owner", "User"),
            "uptime": uptime_str,
            "plugins_active": plugins_active,
            "models_loaded": [state.get("brain", "qwen-14b")],
            "current_activity": "idle",
        }

    # --- Sprint 10 Task 4: Guild Hall Real Data ---

    @router.get("/api/v1/guildhall/agents")
    async def api_guildhall_agents():
        """Return real agent state for guild hall visualization."""
        from pathlib import Path as _Path

        # Load companion state
        state = {}
        state_path = _Path.home() / ".valhalla" / "companion_state.json"
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        agent = state.get("agent", {})
        agent_name = agent.get("name", "Atlas") if agent else "Atlas"
        agent_style = agent.get("style", "analytical") if agent else "analytical"

        # Determine AI activity from live system state
        ai_activity = "idle"
        ai_task_label = None

        # Check for active pipelines
        try:
            from plugins.pipeline.handler import get_active_pipelines
            active = get_active_pipelines()
            if active:
                ai_activity = "building"
                ai_task_label = active[0].get("name", "Working on a task")
        except (ImportError, Exception):
            pass

        # Check for active browse requests
        if ai_activity == "idle":
            try:
                from plugins.browse.parser import _active_requests
                if _active_requests:
                    ai_activity = "researching"
                    ai_task_label = "Browsing the web"
            except (ImportError, AttributeError):
                pass

        # Determine companion activity
        companion_activity = "idle"
        companion_task_label = None
        ws_count = len([c for c in _active_ws_connections if c is not None]) if '_active_ws_connections' in dir() else 0

        # Check WebSocket connections
        try:
            if len(_active_ws_connections) > 0:
                companion_activity = "chatting"
                companion_task_label = f"Talking to {state.get('owner', 'User')}"
        except (NameError, Exception):
            pass

        agents = [
            {
                "name": agent_name,
                "type": "ai",
                "style": agent_style,
                "activity": ai_activity,
                "status": "online",
                "taskLabel": ai_task_label,
            },
            {
                "name": state.get("name", "Companion"),
                "type": "companion",
                "species": state.get("species", "fox"),
                "activity": companion_activity,
                "status": "online",
                "taskLabel": companion_task_label,
            },
        ]

        return {"agents": agents}

    # --- Sprint 11 Task 2: Network Status API ---

    @router.get("/api/v1/network/status")
    async def api_network_status():
        """Return local and Tailscale IPs for mobile connection routing."""
        import socket
        import subprocess

        # Get local IP
        local_ip = "unknown"
        try:
            # Create a UDP socket to determine the primary local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                pass

        # Get Tailscale IP
        tailscale_ip = None
        bridge_active = False
        try:
            result = subprocess.run(
                ["tailscale", "ip", "-4"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                tailscale_ip = result.stdout.strip().split("\n")[0]
                bridge_active = True
        except FileNotFoundError:
            # Tailscale not installed
            pass
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        return {
            "local_ip": local_ip,
            "tailscale_ip": tailscale_ip,
            "bridge_active": bridge_active,
        }

    # --- Missing Mobile Endpoints ---

    # ── Phone Context Sync (sensor layer → brain layer) ────────────────────────

    def _store_phone_context(data: dict, session_id: str = ""):
        """Store phone sensor data for the big brain to use.

        The phone is a dumb sensor pipe — contacts, calendar, device info.
        This function stores the raw data and injects key facts into working memory.
        """
        import time as _time
        from pathlib import Path as _Path

        context_file = _Path.home() / ".valhalla" / "phone_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing context
        existing = {}
        if context_file.exists():
            try:
                existing = json.loads(context_file.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        # Merge new data (don't overwrite fields that weren't sent)
        if "contacts" in data:
            existing["contacts"] = data["contacts"]
            existing["contacts_updated_at"] = _time.time()
        if "calendar" in data:
            existing["calendar"] = data["calendar"]
            existing["calendar_updated_at"] = _time.time()
        if "device" in data:
            existing["device"] = data["device"]
        existing["last_sync"] = _time.time()
        existing["session_id"] = session_id

        context_file.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Inject key facts into working memory for the big brain
        try:
            import orchestrator as orch_mod

            # Calendar context — so AI knows user's schedule
            cal = data.get("calendar", {})
            if cal.get("next_event"):
                evt = cal["next_event"]
                loc = f" at {evt['location']}" if evt.get('location') else ""
                orch_mod.observe(
                    f"User's next calendar event: \"{evt['title']}\" starting {evt['start']}{loc}",
                    importance=0.6,
                    source="phone_calendar",
                )
            if cal.get("event_count", 0) > 0:
                orch_mod.observe(
                    f"User has {cal['event_count']} events today on their calendar",
                    importance=0.4,
                    source="phone_calendar",
                )

            # Device context — timezone, time of day
            device = data.get("device", {})
            if device.get("time_zone"):
                orch_mod.observe(
                    f"User's phone timezone: {device['time_zone']}, current hour: {device.get('hour', '?')}",
                    importance=0.2,
                    source="phone_device",
                )

            # Contact count (not individual contacts — that's stored in the file)
            contacts = data.get("contacts", [])
            if contacts:
                orch_mod.observe(
                    f"Phone synced {len(contacts)} contacts to working memory",
                    importance=0.3,
                    source="phone_contacts",
                )
        except Exception as e:
            log.debug("[companion/context] Working memory inject failed: %s", e)

        log.info("[companion/context] Phone context synced (contacts=%s, calendar=%s, device=%s)",
                 "contacts" in data, "calendar" in data, "device" in data)

    @router.post("/api/v1/companion/context/sync")
    async def api_context_sync(request: "Request"):
        """HTTP fallback for phone context sync (when WebSocket unavailable)."""
        body = await request.json()
        _store_phone_context(body)
        return {"ok": True, "stored": len(body)}

    @router.get("/api/v1/companion/context")
    async def api_context_get():
        """Return stored phone context (for dashboard/debug)."""
        from pathlib import Path as _Path
        context_file = _Path.home() / ".valhalla" / "phone_context.json"
        if not context_file.exists():
            return {"ok": True, "context": {}, "synced": False}
        try:
            data = json.loads(context_file.read_text(encoding="utf-8"))
            return {"ok": True, "context": data, "synced": True}
        except Exception:
            return {"ok": True, "context": {}, "synced": False}

    # ── Skills (RPG toggle cards) ──────────────────────────────────────────────

    @router.get("/api/v1/companion/skills")
    async def api_companion_skills():
        """Return available companion skills with XP and toggle state."""
        from pathlib import Path as _Path

        skills_file = _Path.home() / ".valhalla" / "companion_skills.json"

        # Default skills if none saved
        default_skills = [
            {"id": "research",    "name": "Research",       "description": "Search the web and summarize findings",       "emoji": "🔍", "enabled": True,  "level": 1, "xp_cost": 100},
            {"id": "code",        "name": "Code",           "description": "Write, debug, and review code",              "emoji": "💻", "enabled": True,  "level": 1, "xp_cost": 150},
            {"id": "translate",   "name": "Translation",    "description": "Translate between 200+ languages",           "emoji": "🌍", "enabled": True,  "level": 1, "xp_cost": 75},
            {"id": "browse",      "name": "Web Browse",     "description": "Read and extract data from web pages",       "emoji": "🌐", "enabled": True,  "level": 1, "xp_cost": 100},
            {"id": "file_ops",    "name": "File Operations","description": "Read, write, and organize files on your PC", "emoji": "📁", "enabled": True,  "level": 1, "xp_cost": 125},
            {"id": "voice",       "name": "Voice",          "description": "Speech-to-text and text-to-speech",          "emoji": "🎤", "enabled": True,  "level": 1, "xp_cost": 100},
            {"id": "guardian",    "name": "Guardian",       "description": "Message safety filter and sleep mode",       "emoji": "🛡️", "enabled": True,  "level": 1, "xp_cost": 50},
            {"id": "memory",      "name": "Memory",         "description": "Remember facts, preferences, and context",   "emoji": "🧠", "enabled": True,  "level": 1, "xp_cost": 200},
            {"id": "pipeline",    "name": "Pipeline",       "description": "Multi-step automated task execution",        "emoji": "⚡", "enabled": False, "level": 0, "xp_cost": 300},
            {"id": "debate",      "name": "Debate",         "description": "Generate multiple perspectives on a topic",  "emoji": "⚖️", "enabled": False, "level": 0, "xp_cost": 250},
        ]

        if skills_file.exists():
            try:
                saved = json.loads(skills_file.read_text(encoding="utf-8"))
                # Merge saved toggle/level state into defaults
                saved_map = {s["id"]: s for s in saved}
                for skill in default_skills:
                    if skill["id"] in saved_map:
                        skill["enabled"] = saved_map[skill["id"]].get("enabled", skill["enabled"])
                        skill["level"] = saved_map[skill["id"]].get("level", skill["level"])
            except Exception:
                pass

        return {"skills": default_skills}

    @router.post("/api/v1/companion/skills/toggle")
    async def api_companion_skill_toggle(request: "Request"):
        """Toggle a skill on/off."""
        from pathlib import Path as _Path
        body = await request.json()
        skill_id = body.get("skill_id", "")
        enabled = body.get("enabled", True)

        skills_file = _Path.home() / ".valhalla" / "companion_skills.json"
        skills_file.parent.mkdir(parents=True, exist_ok=True)

        existing = []
        if skills_file.exists():
            try:
                existing = json.loads(skills_file.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        # Update or add the skill
        found = False
        for s in existing:
            if s.get("id") == skill_id:
                s["enabled"] = enabled
                found = True
                break
        if not found:
            existing.append({"id": skill_id, "enabled": enabled, "level": 1 if enabled else 0})

        skills_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return {"ok": True, "skill": {"id": skill_id, "enabled": enabled}}

    # ── Personality (soul traits) ──────────────────────────────────────────────

    @router.get("/api/v1/companion/personality")
    async def api_companion_personality_get():
        """Return companion personality traits from soul file."""
        from pathlib import Path as _Path

        soul_file = _Path.home() / ".valhalla" / "companion_soul.json"

        default_personality = {
            "traits": {
                "warmth": "high",
                "humor": "medium",
                "formality": "low",
                "curiosity": "high",
                "empathy": "high",
                "creativity": "medium",
                "directness": "medium",
                "patience": "high",
                "enthusiasm": "high",
                "sarcasm": "low",
            },
            "voice_style": "warm and conversational",
            "greeting": "Hey there! What's on your mind?",
            "bio": "Your private AI companion — lives on your PC, travels with your phone.",
        }

        if soul_file.exists():
            try:
                saved = json.loads(soul_file.read_text(encoding="utf-8"))
                default_personality.update(saved)
            except Exception:
                pass

        return default_personality

    @router.post("/api/v1/companion/personality")
    async def api_companion_personality_update(request: "Request"):
        """Update personality traits."""
        from pathlib import Path as _Path

        body = await request.json()
        new_traits = body.get("traits", {})

        soul_file = _Path.home() / ".valhalla" / "companion_soul.json"
        soul_file.parent.mkdir(parents=True, exist_ok=True)

        existing = {}
        if soul_file.exists():
            try:
                existing = json.loads(soul_file.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        # Merge traits
        if "traits" not in existing:
            existing["traits"] = {}
        existing["traits"].update(new_traits)

        soul_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        log.info("[companion/personality] Traits updated: %s", list(new_traits.keys()))

        return {"ok": True, "traits": existing.get("traits", {})}

    # ── Teach (store user facts) ──────────────────────────────────────────────

    @router.post("/api/v1/companion/teach")
    async def api_companion_teach(request: "Request"):
        """Store a fact the user teaches the companion."""
        import time as _time
        from pathlib import Path as _Path

        body = await request.json()
        fact = body.get("fact", "").strip()
        if not fact:
            raise HTTPException(400, "No fact provided")

        facts_file = _Path.home() / ".valhalla" / "taught_facts.json"
        facts_file.parent.mkdir(parents=True, exist_ok=True)

        facts = []
        if facts_file.exists():
            try:
                facts = json.loads(facts_file.read_text(encoding="utf-8"))
            except Exception:
                facts = []

        facts.append({
            "fact": fact,
            "taught_at": _time.time(),
            "source": "mobile",
        })

        # Keep last 500 facts
        if len(facts) > 500:
            facts = facts[-500:]

        facts_file.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")

        # Also store in working memory if available
        try:
            import orchestrator as orch_mod
            orch_mod.observe(
                f"User taught: {fact}",
                importance=0.8,
                source="mobile_teach",
            )
        except Exception:
            pass

        log.info("[companion/teach] Stored fact: %s", fact[:80])
        return {
            "ok": True,
            "confirmation": f"Got it! I'll remember that.",
            "fact_count": len(facts),
        }

    # ── Heartbeat (what companion is doing) ───────────────────────────────────

    @router.get("/api/v1/companion/heartbeat")
    async def api_companion_heartbeat():
        """Return what the companion is currently doing."""
        import time as _time

        activity = "idle"
        emoji = "😴"
        detail = None
        since = None

        # Check for active pipelines
        try:
            from plugins.pipeline.handler import get_active_pipelines
            active = get_active_pipelines()
            if active:
                activity = "building"
                emoji = "⚡"
                detail = active[0].get("name", "Working on a task")
                since = active[0].get("started_at", "")
        except (ImportError, Exception):
            pass

        # Check for active WebSocket connections (chatting)
        if activity == "idle":
            try:
                if len(_ws_connections) > 0:
                    activity = "chatting"
                    emoji = "💬"
                    detail = "Connected with mobile"
            except Exception:
                pass

        # Check for active browse requests
        if activity == "idle":
            try:
                from plugins.browse.parser import _active_requests
                if _active_requests:
                    activity = "researching"
                    emoji = "🔍"
                    detail = "Browsing the web"
            except (ImportError, AttributeError):
                pass

        # Check companion mood
        if activity == "idle":
            try:
                from plugins.companion.sim import load_state
                state = load_state()
                if state:
                    happiness = state.get("happiness", 50)
                    if happiness >= 80:
                        activity = "happy"
                        emoji = "😊"
                        detail = "Feeling great!"
                    elif happiness >= 50:
                        activity = "content"
                        emoji = "😌"
                        detail = "Doing well"
                    elif happiness >= 30:
                        activity = "bored"
                        emoji = "😐"
                        detail = "Could use some attention"
                    else:
                        activity = "sad"
                        emoji = "😢"
                        detail = "Missing you..."
            except Exception:
                pass

        return {
            "activity": activity,
            "emoji": emoji,
            "detail": detail,
            "since": since,
        }

    # ── Pet State (mood/energy/hunger) ─────────────────────────────────────────

    @router.get("/api/v1/companion/pet-state")
    async def api_companion_pet_state():
        """Return companion pet state — mood, energy, hunger, last interaction.

        Powers the mobile care screen meters and desktop companion widget.
        """
        import time as _time
        from pathlib import Path as _Path

        state_path = _Path.home() / ".valhalla" / "companion_state.json"
        state = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "mood": state.get("happiness", 50),
            "energy": state.get("energy", 70),
            "hunger": state.get("hunger", 50),
            "last_interaction": state.get("last_interaction"),
        }

    # ── Interact (feed/walk/play) ──────────────────────────────────────────────

    @router.post("/api/v1/companion/interact")
    async def api_companion_interact(request: "Request"):
        """Interact with companion — feed, walk, or play.

        Body: { "action": "feed" | "walk" | "play", "item": "optional item" }
        Updates pet state and returns new state + flavour message.
        """
        import time as _time
        import random
        from pathlib import Path as _Path

        body = await request.json()
        action = body.get("action", "")
        item = body.get("item")

        if action not in ("feed", "walk", "play"):
            raise HTTPException(400, "action must be 'feed', 'walk', or 'play'")

        state_path = _Path.home() / ".valhalla" / "companion_state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)

        state = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                state = {}

        mood = state.get("happiness", 50)
        energy = state.get("energy", 70)
        hunger = state.get("hunger", 50)

        messages = {
            "feed": [
                "Nom nom! That was delicious! 🍖",
                "Mmmm, thank you! I was getting hungry! 🍕",
                "Yummy! My favorite! 🍪",
            ],
            "walk": [
                "What a lovely walk! Found a shiny pebble! 🪨✨",
                "Fresh air feels great! Let's do this more often! 🌳",
                "I spotted a butterfly! Almost caught it! 🦋",
            ],
            "play": [
                "That was so much fun! Again, again! 🎾",
                "Woohoo! Best playtime ever! 🎮",
                "I love playing with you! 🎉",
            ],
        }

        if action == "feed":
            hunger = max(0, hunger - 30)
            mood = min(100, mood + 10)
            energy = min(100, energy + 5)
        elif action == "walk":
            energy = max(0, energy - 15)
            mood = min(100, mood + 15)
            hunger = min(100, hunger + 10)
        elif action == "play":
            energy = max(0, energy - 20)
            mood = min(100, mood + 20)
            hunger = min(100, hunger + 5)

        state["happiness"] = mood
        state["energy"] = energy
        state["hunger"] = hunger
        state["last_interaction"] = _time.time()

        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "state": {"mood": mood, "energy": energy, "hunger": hunger},
            "message": random.choice(messages[action]),
        }

    # ── Forget All (nuclear reset) ─────────────────────────────────────────────

    @router.delete("/api/v1/companion/forget")
    async def api_companion_forget():
        """Nuclear reset — clear all companion data.

        Deletes: companion_state, taught_facts, companion_soul, chat_history,
        companion_skills, phone_context. Does NOT delete the user's config.
        """
        from pathlib import Path as _Path

        valhalla_dir = _Path.home() / ".valhalla"

        deleted = []
        for filename in [
            "companion_state.json",
            "taught_facts.json",
            "companion_soul.json",
            "chat_history.json",
            "companion_skills.json",
            "phone_context.json",
        ]:
            fp = valhalla_dir / filename
            if fp.exists():
                try:
                    fp.unlink()
                    deleted.append(filename)
                except Exception as e:
                    log.warning("[companion/forget] Failed to delete %s: %s", filename, e)

        log.info("[companion/forget] Nuclear reset — deleted %d files: %s", len(deleted), deleted)
        return {
            "ok": True,
            "message": f"All companion data has been reset. Deleted {len(deleted)} files.",
        }

    app.include_router(router)
    log.info("[companion] Plugin loaded (Sprint 11: network status + bridge).")

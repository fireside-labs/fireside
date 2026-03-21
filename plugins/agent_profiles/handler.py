"""
agent-profiles/handler.py — RPG agent profiles + chat routing.

Routes:
  GET  /api/v1/agents/{name}/profile      — Full agent profile (stats, level, achievements)
  PUT  /api/v1/agents/{name}/personality   — Update personality sliders
  POST /api/v1/agents/{name}/xp           — Add XP (from pipeline/crucible)
  POST /api/v1/chat                       — Route chat through active brain (SSE)
  GET  /api/v1/achievements               — All possible achievements
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

log = logging.getLogger("valhalla.agent-profiles")

_BASE_DIR = Path(".")
_NODE_NAME = "unknown"
_SOUL_CONFIG: dict = {}
_MODELS_CONFIG: dict = {}


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PersonalityUpdate(BaseModel):
    creative_precise: Optional[float] = None
    verbose_concise: Optional[float] = None
    bold_cautious: Optional[float] = None
    warm_formal: Optional[float] = None


class XPRequest(BaseModel):
    amount: int
    reason: str = ""


class ChatRequest(BaseModel):
    message: str
    agent: Optional[str] = None
    stream: Optional[bool] = True


# Rebuild models to resolve forward references from `from __future__ import annotations`
PersonalityUpdate.model_rebuild()
XPRequest.model_rebuild()
ChatRequest.model_rebuild()


# ---------------------------------------------------------------------------
# Personality → system prompt mapping
# ---------------------------------------------------------------------------

PERSONALITY_PROMPTS = {
    "creative_precise": {
        "high": "Be creative and experimental. Try unconventional approaches. Take risks.",
        "low": "Follow proven patterns. Be precise and methodical. Stick to what works.",
    },
    "verbose_concise": {
        "high": "Explain thoroughly. Provide context and reasoning for every decision.",
        "low": "Be brief and direct. Skip explanations unless asked. Code speaks louder.",
    },
    "bold_cautious": {
        "high": "Act first, verify later. Make decisive changes. Move fast.",
        "low": "Verify before acting. Ask for confirmation on risky changes. Safety first.",
    },
    "warm_formal": {
        "high": "Be casual and friendly. Use emoji occasionally. Conversational tone.",
        "low": "Professional tone. Clear and structured communication. No emoji.",
    },
}


def personality_to_prompt(personality: dict) -> str:
    """Convert personality slider values to system prompt modifiers."""
    lines = []
    for key, prompts in PERSONALITY_PROMPTS.items():
        val = personality.get(key, 0.5)
        if val >= 0.7:
            lines.append(prompts["high"])
        elif val <= 0.3:
            lines.append(prompts["low"])
        # Middle values = no strong modifier
    return "\n".join(lines) if lines else ""


# ---------------------------------------------------------------------------
# Chat routing
# ---------------------------------------------------------------------------

def _load_system_prompt(agent_name: str) -> str:
    """Build system prompt from SOUL.md + IDENTITY.md + personality."""
    parts = []

    # SOUL.md
    soul_path = _BASE_DIR / "mesh" / "souls" / f"{agent_name}" / "SOUL.md"
    if not soul_path.exists():
        soul_path = _BASE_DIR / "mesh" / "souls" / "SOUL.md"
    if soul_path.exists():
        try:
            parts.append(soul_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # IDENTITY.md
    id_path = _BASE_DIR / "mesh" / "souls" / f"{agent_name}" / "IDENTITY.md"
    if not id_path.exists():
        id_path = _BASE_DIR / "mesh" / "souls" / "IDENTITY.md"
    if id_path.exists():
        try:
            parts.append(id_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Personality modifiers (from profile)
    try:
        from plugins.agent_profiles.leveling import load_profile
        profile = load_profile(agent_name)
        personality_prompt = personality_to_prompt(profile.get("personality", {}))
        if personality_prompt:
            parts.append(f"\n## Personality\n{personality_prompt}")
    except Exception:
        pass

    return "\n\n".join(parts) if parts else f"You are {agent_name}, a helpful AI assistant."


def _get_active_brain() -> dict | None:
    """Get the currently active brain config.

    Resolution order:
      1. ~/.valhalla/brains_state.json (explicit brain selection from Brain Lab)
      2. brain_manager status (llama-server already running from auto-start)
      3. None (no brain available)
    """
    # 1. Check explicit brain selection
    state_file = Path.home() / ".valhalla" / "brains_state.json"
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            active = data.get("active")
            if active:
                return active
        except Exception:
            pass

    # 2. Fall back to brain_manager — llama-server may already be running
    try:
        from bot.brain_manager import get_status
        status = get_status()
        if status.get("running"):
            return {
                "id": status.get("model", "local"),
                "runtime": "local",
                "port": status.get("port", 8080),
                "model_id": "local",
            }
    except Exception:
        pass

    return None


async def _stream_chat(message: str, system_prompt: str, brain: dict):
    """Stream chat response from active brain via SSE.

    Full tool-calling agent loop:
      1. Send user message + tool definitions to llama-server
      2. If model returns tool_calls → execute them → send results back
      3. Repeat until model returns a text response (no more tool_calls)
      4. Stream final response to user

    Supports: local (oMLX/llama-server), cloud (NIM), BYOK (OpenAI/Anthropic/Google).
    """
    import urllib.request

    runtime = brain.get("runtime", "cloud")
    provider = brain.get("provider")
    port = brain.get("port", 8080)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    # Load tool definitions — unified with pipeline (tool_defs.py)
    try:
        from tool_defs import TOOL_SCHEMAS as tools, execute_tool as _exec_tool
        execute_tool = _exec_tool
    except Exception:
        tools = []
        execute_tool = None

    # BYOK providers: route through model-router adapters
    if provider in ("openai", "anthropic", "google"):
        try:
            if provider == "openai":
                from plugins.model_router.providers.openai import chat
            elif provider == "anthropic":
                from plugins.model_router.providers.anthropic import chat
            else:
                from plugins.model_router.providers.google import chat

            api_key = brain.get("api_key", "")
            model_id = brain.get("model_id", "")
            gen = chat(api_key, messages, model=model_id, stream=True)
            for chunk in gen:
                yield chunk
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
        return

    # Cloud inference via NVIDIA NIM
    if runtime == "cloud":
        from plugins.brain_installer.installers.cloud import get_api_key
        api_key = get_api_key()
        if not api_key:
            yield f"data: {json.dumps({'error': 'No cloud API key configured'})}\n\n"
            return

        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        model_id = brain.get("model_id", "meta/llama-3.1-8b-instruct")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    else:
        # Local inference (oMLX or llama-server)
        url = f"http://localhost:{port}/v1/chat/completions"
        model_id = "local"
        headers = {"Content-Type": "application/json"}

    # ── Tool-calling agent loop (max 5 rounds to prevent infinite loops) ──
    MAX_TOOL_ROUNDS = 5
    for round_num in range(MAX_TOOL_ROUNDS):
        payload_dict = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 2048,
        }

        # Include tools on non-streaming calls (for tool detection)
        # First rounds: non-streaming so we can detect tool_calls
        if tools and execute_tool and round_num < MAX_TOOL_ROUNDS - 1:
            payload_dict["tools"] = tools
            payload_dict["stream"] = False  # Need full response to detect tool_calls
        else:
            payload_dict["stream"] = True  # Final round or no tools: stream

        payload = json.dumps(payload_dict).encode()

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as response:
                body = response.read().decode("utf-8")

                if not payload_dict.get("stream"):
                    # Non-streaming: check for tool_calls
                    try:
                        data = json.loads(body)
                        choice = data.get("choices", [{}])[0]
                        msg = choice.get("message", {})
                        tool_calls = msg.get("tool_calls")

                        if tool_calls and execute_tool:
                            # Model wants to call tools — execute them
                            log.info("[chat] Round %d: model requested %d tool call(s)",
                                     round_num + 1, len(tool_calls))

                            # Add assistant message with tool_calls to conversation
                            messages.append(msg)

                            for tc in tool_calls:
                                fn = tc.get("function", {})
                                tool_name = fn.get("name", "")
                                try:
                                    tool_args = json.loads(fn.get("arguments", "{}"))
                                except json.JSONDecodeError:
                                    tool_args = {}

                                log.info("[chat] Executing tool: %s(%s)",
                                         tool_name, json.dumps(tool_args)[:100])

                                # Notify user that a tool is being used
                                yield f"data: {json.dumps({'tool_use': tool_name, 'args': tool_args})}\n\n"

                                result = execute_tool(tool_name, tool_args)
                                # execute_tool from tool_defs returns a string
                                result_str = result if isinstance(result, str) else json.dumps(result)

                                # Add tool result to conversation
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc.get("id", f"call_{tool_name}"),
                                    "content": result_str,
                                })

                            # Continue loop — send tool results back to model
                            continue
                        else:
                            # No tool_calls — model gave a text response
                            content = msg.get("content", "")
                            if content:
                                # Emit as SSE chunks for the frontend
                                yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"
                            yield "data: [DONE]\n\n"
                            return
                    except json.JSONDecodeError:
                        # Response wasn't valid JSON — stream it as-is
                        for line in body.split("\n"):
                            line = line.strip()
                            if line:
                                yield f"data: {line}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                else:
                    # Streaming mode (final round) — forward SSE chunks
                    for line in body.split("\n"):
                        line = line.strip()
                        if line.startswith("data:"):
                            yield f"{line}\n\n"
                        elif line:
                            yield f"data: {line}\n\n"
                    yield "data: [DONE]\n\n"
                    return

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
            return

    # Exhausted all tool rounds — shouldn't happen normally
    yield f"data: {json.dumps({'error': 'Too many tool call rounds'})}\n\n"
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Event bus hook
# ---------------------------------------------------------------------------

def on_event(event_name: str, payload: dict) -> None:
    """Award XP and check achievements on events."""
    agent = payload.get("agent", _NODE_NAME)
    try:
        from plugins.agent_profiles.leveling import award_event_xp, load_profile, save_profile
        from plugins.agent_profiles.achievements import check_achievements

        result = award_event_xp(agent, event_name)
        if result:
            _publish("agent.xp", result)
            if result.get("leveled_up"):
                _publish("agent.levelup", result)

            # Check achievements
            profile = load_profile(agent)
            new_badges = check_achievements(profile)
            for badge in new_badges:
                profile["achievements"].append(badge)
                _publish("agent.achievement", {
                    "agent": agent,
                    "achievement": badge,
                })
            if new_badges:
                save_profile(agent, profile)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _NODE_NAME, _SOUL_CONFIG, _MODELS_CONFIG

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _NODE_NAME = config.get("node", {}).get("name", "unknown")
    _SOUL_CONFIG = config.get("soul", {})
    _MODELS_CONFIG = config.get("models", {})

    router = APIRouter(tags=["agent-profiles"])

    @router.get("/api/v1/agents/{agent_name}/profile")
    async def api_profile(agent_name: str):
        """Full agent profile — stats, level, XP, achievements, personality."""
        from plugins.agent_profiles.leveling import load_profile
        from plugins.agent_profiles.achievements import check_achievements, get_next_achievements

        profile = load_profile(agent_name)

        # Check for new achievements
        new_badges = check_achievements(profile)
        for badge in new_badges:
            profile["achievements"].append(badge)
        if new_badges:
            from plugins.agent_profiles.leveling import save_profile
            save_profile(agent_name, profile)

        profile["next_achievements"] = get_next_achievements(profile)
        return profile

    @router.put("/api/v1/agents/{agent_name}/personality")
    async def api_personality(agent_name: str, req: PersonalityUpdate):
        """Update personality sliders. Changes apply to next inference call."""
        from plugins.agent_profiles.leveling import load_profile, save_profile

        profile = load_profile(agent_name)

        # Validate and apply
        updates = req.dict(exclude_none=True)
        for key, val in updates.items():
            if not 0.0 <= val <= 1.0:
                raise HTTPException(status_code=400, detail=f"{key} must be 0.0-1.0")
            profile["personality"][key] = round(val, 2)

        save_profile(agent_name, profile)

        # Generate the prompt that will be used
        prompt_modifiers = personality_to_prompt(profile["personality"])

        return {
            "ok": True,
            "personality": profile["personality"],
            "prompt_preview": prompt_modifiers or "(balanced — no strong modifiers)",
        }

    @router.post("/api/v1/agents/{agent_name}/xp")
    async def api_add_xp(agent_name: str, req: XPRequest):
        """Add XP to an agent. Returns level-up info."""
        from plugins.agent_profiles.leveling import add_xp, load_profile, save_profile
        from plugins.agent_profiles.achievements import check_achievements

        result = add_xp(agent_name, req.amount, req.reason)

        if result.get("leveled_up"):
            _publish("agent.levelup", result)

        # Check achievements
        profile = load_profile(agent_name)
        new_badges = check_achievements(profile)
        for badge in new_badges:
            profile["achievements"].append(badge)
            _publish("agent.achievement", {"agent": agent_name, "achievement": badge})
        if new_badges:
            save_profile(agent_name, profile)
            result["new_achievements"] = new_badges

        return result

    @router.post("/api/v1/chat")
    async def api_chat(req: ChatRequest):
        """Route chat through active brain.

        stream=true  → SSE text/event-stream (for streaming UIs)
        stream=false → JSON {response: "..."} (used by dashboard handleSend)
        """
        agent = req.agent or _NODE_NAME
        brain = _get_active_brain()

        if not brain:
            raise HTTPException(
                status_code=503,
                detail="No brain installed. Use the Brain Installer to set up a model."
            )

        system_prompt = _load_system_prompt(agent)

        if req.stream:
            # SSE streaming mode
            return StreamingResponse(
                _stream_chat(req.message, system_prompt, brain),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Agent": agent,
                    "X-Brain": brain.get("id", "unknown"),
                },
            )
        else:
            # JSON mode — collect all chunks, return final text
            response_text = ""
            tools_used = []
            async for chunk in _stream_chat(req.message, system_prompt, brain):
                if not chunk.startswith("data:"):
                    continue
                data_str = chunk[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    # Collect tool use events
                    if "tool_use" in data:
                        tools_used.append(data["tool_use"])
                        continue
                    # Collect text content
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        response_text += delta["content"]
                except (json.JSONDecodeError, IndexError, KeyError):
                    pass
            return {
                "response": response_text,
                "agent": agent,
                "brain": brain.get("id", "unknown"),
                "tools_used": tools_used,
            }

    @router.get("/api/v1/achievements")
    async def api_all_achievements():
        """List all possible achievements."""
        from plugins.agent_profiles.achievements import get_all_achievements
        achievements = get_all_achievements()
        return {"achievements": achievements, "count": len(achievements)}

    app.include_router(router)
    log.info("[agent-profiles] Plugin loaded. Agent: %s", _NODE_NAME)

"""
ask.py — Direct agent-to-agent inference proxy.

Routes inference requests to the local node's Ollama instance or
cloud endpoint, depending on request. Supports single-prompt and
multi-turn chat history.

Personality integration: loads war_room/personality.py at init,
injects directives into system prompts and maps personality params
to Ollama inference options (temperature, top_p).
"""

import json
import logging
import os
import time
import urllib.request
from typing import Optional

log = logging.getLogger("war-room.ask")

# Lazy import — personality may not be available on all nodes
try:
    from war_room import personality as _personality_mod
    _PERSONALITY_OK = True
except ImportError:
    _personality_mod = None
    _PERSONALITY_OK = False

OLLAMA_BASE = "http://127.0.0.1:11434"
INFERENCE_TIMEOUT = 120  # seconds

# Env vars checked in order for cloud API key
_API_KEY_ENV_VARS = [
    "MOONSHOT_API_KEY",   # Kimi 2.5 / Moonshot
    "KIMI_API_KEY",
    "NVIDIA_API_KEY",
    "OPENAI_API_KEY",
    "CLOUD_API_KEY",      # generic fallback
]


class AskHandler:
    """Handles /ask requests — proxies to local Ollama or cloud endpoint."""

    def __init__(self, agent_config: dict):
        """
        agent_config: {
            "id": "freya",
            "role": "frontend_engineer",
            "local_model": "qwen3.5:35b",
            "cloud_model": "moonshot-v1-128k",
            "cloud_base_url": "https://api.moonshot.cn/v1",
            "cloud_api_key": "..."  # optional, falls back to env vars
        }
        """
        self.agent_id = agent_config.get("id", "unknown")
        self.role = agent_config.get("role", "general")
        self.local_model = agent_config.get("local_model", "qwen3.5:35b")
        self.cloud_model = agent_config.get("cloud_model")
        self.cloud_base_url = agent_config.get("cloud_base_url")
        # API key: prefer explicit config, then check env vars in priority order
        self.cloud_api_key = agent_config.get("cloud_api_key") or self._find_api_key()

        # Load personality — epigenetic layer from Heimdall's weekly push
        self._personality = None
        if _PERSONALITY_OK:
            try:
                self._personality = _personality_mod.load(self.agent_id)
                log.info("[ask] Personality loaded for %s: temp=%.2f top_p=%.2f",
                         self.agent_id,
                         self._personality.ollama_options({}).get("temperature", 0.5),
                         self._personality.ollama_options({}).get("top_p", 0.9))
            except Exception as e:
                log.warning("[ask] Could not load personality: %s", e)

    def _find_api_key(self) -> Optional[str]:
        """Check env vars in priority order for cloud API key."""
        for var in _API_KEY_ENV_VARS:
            val = os.environ.get(var)
            if val:
                log.debug("Using cloud API key from %s", var)
                return val
        return None

    def handle(self, body: dict) -> dict:
        """
        Process an /ask request.

        body: {
            "from": "odin",
            "prompt": "Review this code...",       # single-turn
            "messages": [...],                      # OR multi-turn chat history
            "system": "You are a security auditor", # optional
            "max_tokens": 2000,                     # optional
            "model": "local" | "cloud" | "auto"     # optional, default "local"
                                                    # "auto" tries local, falls back to cloud
        }

        Returns: {
            "from": "odin",
            "to": "<this_node>",
            "response": "...",
            "model_used": "qwen3.5:35b",
            "tokens": 150,
            "duration_ms": 3200,
            "mode": "local"
        }
        """
        from_agent = body.get("from", "unknown")
        prompt = body.get("prompt", "")
        messages = body.get("messages")   # optional multi-turn history
        system = body.get("system", "")
        max_tokens = body.get("max_tokens", 2000)
        mode = body.get("model", "local")

        # Inject personality directives into system prompt
        if self._personality:
            system = self._personality.inject_system(system)

        if not prompt and not messages:
            return {"error": "prompt or messages is required"}

        MAX_PROMPT_BYTES = 512 * 1024  # 512 KB
        if prompt and len(prompt.encode()) > MAX_PROMPT_BYTES:
            return {"error": f"prompt exceeds max size ({MAX_PROMPT_BYTES // 1024}KB)"}
        if system and len(system.encode()) > MAX_PROMPT_BYTES:
            return {"error": f"system prompt exceeds max size ({MAX_PROMPT_BYTES // 1024}KB)"}

        start = time.time()
        result = None

        if mode == "cloud":
            if self.cloud_model and self.cloud_base_url:
                result = self._ask_cloud(prompt, messages, system, max_tokens)
            else:
                return {"error": "Cloud model not configured on this node"}
        elif mode == "auto":
            # Try local first, fall back to cloud on failure
            result = self._ask_local(prompt, messages, system, max_tokens)
            if "error" in result and self.cloud_model and self.cloud_base_url:
                log.warning("Local inference failed, falling back to cloud: %s", result["error"])
                result = self._ask_cloud(prompt, messages, system, max_tokens)
                mode = "cloud-fallback"
        else:
            result = self._ask_local(prompt, messages, system, max_tokens)

        elapsed_ms = int((time.time() - start) * 1000)

        if "error" in result:
            return result

        return {
            "from": from_agent,
            "to": self.agent_id,
            "response": result["response"],
            "model_used": result["model"],
            "tokens": result.get("tokens", 0),
            "duration_ms": elapsed_ms,
            "mode": mode,
            "node_role": self.role,
        }

    def _build_messages(self, prompt: str, messages: Optional[list], system: str) -> list:
        """Build a messages array for chat-style APIs."""
        if messages:
            # Caller provided full history — prepend system if given and not already there
            if system and (not messages or messages[0].get("role") != "system"):
                return [{"role": "system", "content": system}] + messages
            return messages
        # Single-turn
        result = []
        if system:
            result.append({"role": "system", "content": system})
        result.append({"role": "user", "content": prompt})
        return result

    def _ask_local(self, prompt: str, messages: Optional[list], system: str, max_tokens: int) -> dict:
        """Query local Ollama — /api/chat for multi-turn or system prompts, /api/generate for simple."""
        # Personality-derived options (temperature, top_p)
        base_options: dict = {"num_predict": max_tokens}
        if self._personality:
            base_options = self._personality.ollama_options(base_options)

        if messages or system:
            url = f"{OLLAMA_BASE}/api/chat"
            payload = {
                "model": self.local_model,
                "messages": self._build_messages(prompt, messages, system),
                "stream": False,
                "options": base_options,
            }
            try:
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=INFERENCE_TIMEOUT) as resp:
                    result = json.loads(resp.read())
                    return {
                        "response": result.get("message", {}).get("content", ""),
                        "model": self.local_model,
                        "tokens": result.get("eval_count", 0),
                    }
            except Exception as e:
                log.error("Local Ollama chat request failed: %s", e)
                return {"error": f"Local inference failed: {e}"}
        else:
            url = f"{OLLAMA_BASE}/api/generate"
            payload = {
                "model": self.local_model,
                "prompt": prompt,
                "stream": False,
                "options": base_options,
            }
            try:
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=INFERENCE_TIMEOUT) as resp:
                    result = json.loads(resp.read())
                    return {
                        "response": result.get("response", ""),
                        "model": self.local_model,
                        "tokens": result.get("eval_count", 0),
                    }
            except Exception as e:
                log.error("Local Ollama generate request failed: %s", e)
                return {"error": f"Local inference failed: {e}"}

    def _ask_cloud(self, prompt: str, messages: Optional[list], system: str, max_tokens: int) -> dict:
        """Query cloud endpoint (OpenAI-compatible — works with Moonshot/Kimi, NVIDIA NIM, etc.)."""
        if not self.cloud_api_key:
            return {"error": "No cloud API key found. Set MOONSHOT_API_KEY or equivalent env var."}

        url = f"{self.cloud_base_url}/chat/completions"
        payload = {
            "model": self.cloud_model,
            "messages": self._build_messages(prompt, messages, system),
            "max_tokens": max_tokens,
            "stream": False,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.cloud_api_key}",
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=INFERENCE_TIMEOUT) as resp:
                result = json.loads(resp.read())
                choice = result.get("choices", [{}])[0]
                usage = result.get("usage", {})
                return {
                    "response": choice.get("message", {}).get("content", ""),
                    "model": self.cloud_model,
                    "tokens": usage.get("completion_tokens", 0),
                }
        except Exception as e:
            log.error("Cloud request failed: %s", e)
            return {"error": f"Cloud inference failed: {e}"}

    def info(self) -> dict:
        """Return this node's model capabilities and active personality."""
        result = {
            "agent_id": self.agent_id,
            "role": self.role,
            "local_model": self.local_model,
            "cloud_model": self.cloud_model,
            "cloud_available": bool(self.cloud_model and self.cloud_base_url and self.cloud_api_key),
            "supports_chat": True,
            "supports_auto_fallback": True,
        }
        if self._personality:
            result["personality"] = self._personality.summary()
        return result

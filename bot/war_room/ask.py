"""
ask.py — Direct agent-to-agent inference proxy.

Routes inference requests to the local node's Ollama instance or
cloud NVIDIA NIM endpoint, depending on request.
"""

import json
import logging
import os
import threading
import time
import urllib.request
from typing import Optional

log = logging.getLogger("war-room.ask")

# Heimdall cost reporter — configurable, falls back to known IP
_HEIMDALL_LOG_COST_URL = os.environ.get(
    "HEIMDALL_LOG_COST_URL",
    "http://100.108.153.23:8765/log-cost"
)


def _report_cost_to_heimdall(node: str, model: str, provider: str,
                              tokens_in: int, tokens_out: int,
                              cost_usd: float = 0.0, task_ref: str = None):
    """Fire-and-forget POST to Heimdall's /log-cost. Never blocks the caller."""
    def _send():
        try:
            payload = json.dumps({
                "node":       node,
                "model":      model,
                "provider":   provider,
                "tokens_in":  tokens_in,
                "tokens_out": tokens_out,
                "cost_usd":   cost_usd,
                "task_ref":   task_ref,
            }).encode()
            req = urllib.request.Request(
                _HEIMDALL_LOG_COST_URL, data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # silent — never let cost logging break inference
    t = threading.Thread(target=_send, daemon=True)
    t.start()

OLLAMA_BASE = "http://127.0.0.1:11434"
INFERENCE_TIMEOUT = 120  # seconds


class AskHandler:
    """Handles /ask requests — proxies to local Ollama or cloud NVIDIA NIM."""

    def __init__(self, agent_config: dict):
        """
        agent_config: {
            "id": "odin",
            "role": "orchestrator",
            "local_model": "qwen3.5:27b",
            "cloud_model": "z-ai/glm5",
            "cloud_base_url": "https://integrate.api.nvidia.com/v1",
            "cloud_api_key": "..."  # optional, from env
        }
        """
        self.agent_id = agent_config.get("id", "unknown")
        self.role = agent_config.get("role", "general")
        self.local_model = agent_config.get("local_model", "qwen3.5:27b")
        self.cloud_model = agent_config.get("cloud_model")
        self.cloud_base_url = agent_config.get("cloud_base_url")
        # API key: prefer explicit config, fall back to env var
        self.cloud_api_key = (
            agent_config.get("cloud_api_key")
            or os.environ.get("NVIDIA_API_KEY")
        )

    def handle(self, body: dict) -> dict:
        """
        Process an /ask request.

        body: {
            "from": "odin",
            "prompt": "Review this code...",
            "system": "You are a security auditor",  # optional
            "max_tokens": 2000,                       # optional
            "model": "local" | "cloud"                # optional, default "local"
        }

        Returns: {
            "from": "odin",
            "to": "<this_node>",
            "response": "...",
            "model_used": "qwen3.5:27b",
            "tokens": 150,
            "duration_ms": 3200,
            "mode": "local"
        }
        """
        from_agent = body.get("from", "unknown")
        prompt = body.get("prompt", "")
        system = body.get("system", "")
        max_tokens = body.get("max_tokens", 2000)
        mode = body.get("model", "local")

        if not prompt:
            return {"error": "prompt is required"}
        # Guard against absurdly large prompts flooding the node
        MAX_PROMPT_BYTES = 512 * 1024  # 512 KB
        if len(prompt.encode()) > MAX_PROMPT_BYTES:
            return {"error": f"prompt exceeds max size ({MAX_PROMPT_BYTES // 1024}KB)"}
        if len(system.encode()) > MAX_PROMPT_BYTES:
            return {"error": f"system prompt exceeds max size ({MAX_PROMPT_BYTES // 1024}KB)"}

        start = time.time()

        if mode == "cloud" and self.cloud_model and self.cloud_base_url:
            result = self._ask_cloud(prompt, system, max_tokens)
        else:
            result = self._ask_local(prompt, system, max_tokens)

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

    def _ask_local(self, prompt: str, system: str, max_tokens: int) -> dict:
        """Query local Ollama instance."""
        url = f"{OLLAMA_BASE}/api/generate"
        payload = {
            "model": self.local_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system

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
            log.error("Local Ollama request failed: %s", e)
            return {"error": f"Local inference failed: {e}"}

    def _ask_cloud(self, prompt: str, system: str, max_tokens: int) -> dict:
        """Query NVIDIA NIM cloud endpoint (OpenAI-compatible API)."""
        url = f"{self.cloud_base_url}/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.cloud_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
        }

        headers = {"Content-Type": "application/json"}
        if self.cloud_api_key:
            headers["Authorization"] = f"Bearer {self.cloud_api_key}"

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=INFERENCE_TIMEOUT) as resp:
                result = json.loads(resp.read())
                choice = result.get("choices", [{}])[0]
                usage  = result.get("usage", {})
                tokens_in  = usage.get("prompt_tokens", 0)
                tokens_out = usage.get("completion_tokens", 0)
                # Report cloud cost to Heimdall (fire-and-forget)
                provider = "nvidia" if "nvidia" in (self.cloud_base_url or "") else "cloud"
                _report_cost_to_heimdall(
                    node=self.agent_id,
                    model=self.cloud_model,
                    provider=provider,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                )
                return {
                    "response": choice.get("message", {}).get("content", ""),
                    "model": self.cloud_model,
                    "tokens": tokens_out,
                }
        except Exception as e:
            log.error("Cloud NIM request failed: %s", e)
            return {"error": f"Cloud inference failed: {e}"}

    def info(self) -> dict:
        """Return this node's model capabilities."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "local_model": self.local_model,
            "cloud_model": self.cloud_model,
            "cloud_available": bool(self.cloud_model and self.cloud_base_url),
        }

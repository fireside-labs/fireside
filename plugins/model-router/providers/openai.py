"""
model-router/providers/openai.py — OpenAI API adapter.

Bring-your-own-key provider for GPT-4o, o1, etc.
Same interface as local brain — personality + memory applied regardless.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Generator

API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o"


def validate_key(api_key: str) -> dict:
    """Validate an OpenAI API key."""
    try:
        req = urllib.request.Request(
            f"{API_BASE}/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            models = [m["id"] for m in data.get("data", [])[:5]]
            return {"ok": True, "models": models}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def chat(
    api_key: str,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    stream: bool = False,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> dict | Generator:
    """Send chat request to OpenAI."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": stream,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()

    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    if stream:
        return _stream_response(req)
    else:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            content = data["choices"][0]["message"]["content"]
            return {
                "ok": True,
                "content": content,
                "model": model,
                "usage": data.get("usage"),
            }


def _stream_response(req) -> Generator:
    """Stream SSE response."""
    with urllib.request.urlopen(req, timeout=120) as r:
        for line in r:
            decoded = line.decode("utf-8").strip()
            if decoded.startswith("data:"):
                yield decoded + "\n\n"
    yield "data: [DONE]\n\n"


def get_info() -> dict:
    return {
        "provider": "openai",
        "default_model": DEFAULT_MODEL,
        "models": ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "gpt-3.5-turbo"],
        "supports_streaming": True,
    }

"""
model-router/providers/anthropic.py — Anthropic API adapter.

Bring-your-own-key for Claude 4, Claude 3.5, etc.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Generator

API_BASE = "https://api.anthropic.com/v1"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
API_VERSION = "2023-06-01"


def validate_key(api_key: str) -> dict:
    """Validate an Anthropic API key."""
    try:
        payload = json.dumps({
            "model": DEFAULT_MODEL,
            "max_tokens": 5,
            "messages": [{"role": "user", "content": "hi"}],
        }).encode()
        req = urllib.request.Request(
            f"{API_BASE}/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": API_VERSION,
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return {"ok": True, "model": data.get("model")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def chat(
    api_key: str,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    stream: bool = False,
    max_tokens: int = 2048,
    system: str = "",
) -> dict | Generator:
    """Send chat request to Anthropic."""
    # Anthropic uses separate system param
    user_messages = [m for m in messages if m["role"] != "system"]
    system_msg = system or next((m["content"] for m in messages if m["role"] == "system"), "")

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": user_messages,
        "stream": stream,
    }
    if system_msg:
        body["system"] = system_msg

    payload = json.dumps(body).encode()

    req = urllib.request.Request(
        f"{API_BASE}/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
        },
    )

    if stream:
        return _stream_response(req)
    else:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            content = data["content"][0]["text"]
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
        "provider": "anthropic",
        "default_model": DEFAULT_MODEL,
        "models": [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        "supports_streaming": True,
    }

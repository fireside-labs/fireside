"""
model-router/providers/google.py — Google Gemini API adapter.

Bring-your-own-key for Gemini 2.5, etc.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Generator

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-2.5-flash"


def validate_key(api_key: str) -> dict:
    """Validate a Google API key."""
    try:
        url = f"{API_BASE}/models?key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            models = [m.get("name", "").split("/")[-1] for m in data.get("models", [])[:5]]
            return {"ok": True, "models": models}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def chat(
    api_key: str,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    stream: bool = False,
    max_tokens: int = 2048,
) -> dict | Generator:
    """Send chat request to Gemini."""
    # Convert OpenAI-style messages to Gemini format
    contents = []
    system_instruction = None

    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        elif msg["role"] == "user":
            contents.append({
                "role": "user",
                "parts": [{"text": msg["content"]}],
            })
        elif msg["role"] == "assistant":
            contents.append({
                "role": "model",
                "parts": [{"text": msg["content"]}],
            })

    body = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        body["systemInstruction"] = {
            "parts": [{"text": system_instruction}],
        }

    action = "streamGenerateContent" if stream else "generateContent"
    url = f"{API_BASE}/models/{model}:{action}?key={api_key}"

    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    if stream:
        return _stream_response(req)
    else:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            else:
                content = ""
            return {
                "ok": True,
                "content": content,
                "model": model,
                "usage": data.get("usageMetadata"),
            }


def _stream_response(req) -> Generator:
    """Stream response (Gemini uses JSON array streaming)."""
    with urllib.request.urlopen(req, timeout=120) as r:
        for line in r:
            decoded = line.decode("utf-8").strip()
            if decoded:
                yield f"data: {decoded}\n\n"
    yield "data: [DONE]\n\n"


def get_info() -> dict:
    return {
        "provider": "google",
        "default_model": DEFAULT_MODEL,
        "models": [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ],
        "supports_streaming": True,
    }

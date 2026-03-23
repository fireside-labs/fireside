"""
installers/cloud.py — Cloud model setup (multi-provider).

Supports:
  - NVIDIA NIM (free tier)
  - OpenAI (GPT-4o, o1, etc.)
  - Anthropic (Claude Sonnet 4, Haiku, etc.)
  - Google (Gemini 2.5 Pro, Flash, etc.)

No GPU required — validates API key and tests cloud model availability.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from pathlib import Path

log = logging.getLogger("valhalla.brain-installer.cloud")

CREDENTIALS_DIR = Path.home() / ".valhalla"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials"

# Provider API endpoints
PROVIDER_CONFIG = {
    "nvidia_nim": {
        "name": "NVIDIA NIM",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "test_model": "meta/llama-3.1-8b-instruct",
        "key_prefix": "nvapi-",
        "cred_key": "nvidia_api_key",
        "auth_header": "Authorization",
        "auth_format": "Bearer {key}",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "test_model": "gpt-4o-mini",
        "key_prefix": "sk-",
        "cred_key": "openai_api_key",
        "auth_header": "Authorization",
        "auth_format": "Bearer {key}",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "test_model": "claude-3-5-haiku-20241022",
        "key_prefix": "sk-ant-",
        "cred_key": "anthropic_api_key",
        "auth_header": "x-api-key",
        "auth_format": "{key}",
        "extra_headers": {"anthropic-version": "2023-06-01"},
        "endpoint": "/messages",
        "request_format": "anthropic",
    },
    "google": {
        "name": "Google AI",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "test_model": "gemini-2.5-flash",
        "key_prefix": "AI",
        "cred_key": "google_api_key",
        "endpoint_format": "/models/{model}:generateContent?key={key}",
        "request_format": "google",
    },
}


def is_available() -> bool:
    """Cloud is always available (just needs internet + API key)."""
    return True


def has_api_key(provider: str = "nvidia_nim") -> bool:
    """Check if an API key is configured for the given provider."""
    config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["nvidia_nim"])
    cred_key = config["cred_key"]

    env_key = cred_key.upper()
    if os.environ.get(env_key):
        return True

    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            return bool(creds.get(cred_key))
        except Exception:
            pass
    return False


def get_api_key(provider: str = "nvidia_nim") -> str | None:
    """Get the API key for a provider from env or credential store."""
    config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["nvidia_nim"])
    cred_key = config["cred_key"]

    env_key = cred_key.upper()
    key = os.environ.get(env_key)
    if key:
        return key

    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            return creds.get(cred_key)
        except Exception:
            pass
    return None


def save_api_key(key: str, provider: str = "nvidia_nim") -> dict:
    """Save API key to credential store."""
    config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["nvidia_nim"])
    cred_key = config["cred_key"]

    try:
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

        creds = {}
        if CREDENTIALS_FILE.exists():
            try:
                creds = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        creds[cred_key] = key
        CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2), encoding="utf-8")

        try:
            os.chmod(str(CREDENTIALS_FILE), 0o600)
        except OSError:
            pass

        log.info("[cloud] %s API key saved to %s", config["name"], CREDENTIALS_FILE)
        return {"ok": True, "path": str(CREDENTIALS_FILE), "provider": provider}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def validate_api_key(key: str, provider: str = "nvidia_nim") -> dict:
    """Validate an API key with a test call to the provider."""
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        return {"ok": False, "error": f"Unknown provider: {provider}"}

    try:
        request_format = config.get("request_format", "openai")

        if request_format == "google":
            # Google uses URL-based auth
            model = config["test_model"]
            url = config["base_url"] + f"/models/{model}:generateContent?key={key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": "Hi"}]}],
                "generationConfig": {"maxOutputTokens": 5},
            }).encode()
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
            })
        elif request_format == "anthropic":
            # Anthropic uses x-api-key header + /messages endpoint
            url = config["base_url"] + "/messages"
            payload = json.dumps({
                "model": config["test_model"],
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "Hi"}],
            }).encode()
            headers = {
                "Content-Type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            }
            req = urllib.request.Request(url, data=payload, headers=headers)
        else:
            # OpenAI-compatible (OpenAI, NVIDIA NIM)
            url = config["base_url"] + "/chat/completions"
            payload = json.dumps({
                "model": config["test_model"],
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            }).encode()
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            })

        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            # All formats return some valid response on success
            return {"ok": True, "message": f"{config['name']} API key valid ✅"}

    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"ok": False, "error": "Invalid API key"}
        if e.code == 403:
            return {"ok": False, "error": "Access denied — check your key permissions"}
        if e.code == 429:
            return {"ok": True, "message": "API key valid (rate limited — try again later)"}
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def detect_provider(key: str) -> str:
    """Auto-detect provider from API key prefix."""
    if key.startswith("nvapi-"):
        return "nvidia_nim"
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("sk-"):
        return "openai"
    if key.startswith("AI"):
        return "google"
    # Default to nvidia_nim
    return "nvidia_nim"


def get_provider_status() -> dict:
    """Get status of all cloud providers."""
    status = {}
    for provider_id, config in PROVIDER_CONFIG.items():
        has_key = has_api_key(provider_id)
        status[provider_id] = {
            "name": config["name"],
            "has_key": has_key,
            "key_masked": _mask_key(get_api_key(provider_id)) if has_key else "Not configured",
        }
    return status


def get_install_info() -> dict:
    """Return cloud installer info."""
    return {
        "runtime": "cloud",
        "name": "Cloud (Multi-provider)",
        "available": True,
        "providers": get_provider_status(),
        "platform": "Any (internet required)",
    }


def _mask_key(key: str | None) -> str:
    """Mask API key for safe display."""
    if not key:
        return "Not configured"
    if len(key) < 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


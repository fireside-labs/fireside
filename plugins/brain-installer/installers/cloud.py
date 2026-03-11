"""
installers/cloud.py — Cloud model setup (NVIDIA NIM free tier).

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

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


def is_available() -> bool:
    """Cloud is always available (just needs internet + API key)."""
    return True


def has_api_key() -> bool:
    """Check if NVIDIA API key is configured."""
    # Check env var first
    if os.environ.get("NVIDIA_API_KEY"):
        return True
    # Check credentials file
    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            return bool(creds.get("nvidia_api_key"))
        except Exception:
            pass
    return False


def get_api_key() -> str | None:
    """Get the NVIDIA API key from env or credential store."""
    key = os.environ.get("NVIDIA_API_KEY")
    if key:
        return key
    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            return creds.get("nvidia_api_key")
        except Exception:
            pass
    return None


def save_api_key(key: str) -> dict:
    """Save API key to credential store (NOT valhalla.yaml)."""
    try:
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

        creds = {}
        if CREDENTIALS_FILE.exists():
            try:
                creds = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        creds["nvidia_api_key"] = key
        CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2), encoding="utf-8")

        # Set restrictive permissions (owner read/write only)
        os.chmod(str(CREDENTIALS_FILE), 0o600)

        log.info("[cloud] API key saved to %s", CREDENTIALS_FILE)
        return {"ok": True, "path": str(CREDENTIALS_FILE)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def validate_api_key(key: str) -> dict:
    """Validate an API key with a test call."""
    try:
        payload = json.dumps({
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
        }).encode()

        req = urllib.request.Request(
            f"{NIM_BASE_URL}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            if "choices" in data:
                return {"ok": True, "message": "API key valid ✅"}

        return {"ok": False, "error": "Unexpected response"}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"ok": False, "error": "Invalid API key"}
        if e.code == 429:
            return {"ok": True, "message": "API key valid (rate limited — try again later)"}
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_model(model_id: str, key: str | None = None) -> dict:
    """Test if a specific cloud model is available."""
    api_key = key or get_api_key()
    if not api_key:
        return {"ok": False, "error": "No API key configured"}

    try:
        payload = json.dumps({
            "model": model_id,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 5,
        }).encode()

        req = urllib.request.Request(
            f"{NIM_BASE_URL}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as r:
            return {"ok": True, "model": model_id}
    except Exception as e:
        return {"ok": False, "error": str(e), "model": model_id}


def get_install_info() -> dict:
    """Return cloud installer info."""
    return {
        "runtime": "cloud",
        "name": "Cloud (NVIDIA NIM)",
        "available": True,
        "has_key": has_api_key(),
        "key_masked": _mask_key(get_api_key()),
        "platform": "Any (internet required)",
    }


def _mask_key(key: str | None) -> str:
    """Mask API key for safe display."""
    if not key:
        return "Not configured"
    if len(key) < 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"

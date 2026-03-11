"""
voice/tts.py — Text-to-Speech via Kokoro (CPU only, zero VRAM).

Kokoro is a lightweight TTS engine that runs on CPU.
Sounds natural, fast enough for real-time streaming.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("valhalla.voice.tts")

_VOICE = "af_default"
_SPEED = 1.0

# Built-in voice packs
VOICES = {
    "af_default": {"name": "Default (Female)", "lang": "en", "style": "neutral"},
    "am_default": {"name": "Default (Male)", "lang": "en", "style": "neutral"},
    "af_warm": {"name": "Warm (Female)", "lang": "en", "style": "warm"},
    "am_deep": {"name": "Deep (Male)", "lang": "en", "style": "authoritative"},
    "af_bright": {"name": "Bright (Female)", "lang": "en", "style": "energetic"},
}


def is_installed() -> bool:
    """Check if kokoro TTS is installed."""
    try:
        import kokoro  # noqa: F401
        return True
    except ImportError:
        return False


def install() -> dict:
    """Install kokoro TTS."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "kokoro", "soundfile", "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": str(e)}


def synthesize(text: str, voice: str = "", speed: float = 0.0) -> dict:
    """Synthesize text to audio.

    Returns path to generated wav file.
    """
    v = voice or _VOICE
    s = speed or _SPEED

    try:
        import kokoro
        import soundfile as sf
        import tempfile

        pipeline = kokoro.KPipeline(lang_code="a")
        generator = pipeline(text, voice=v, speed=s)

        # Collect audio samples
        audio_chunks = []
        for _, _, audio in generator:
            audio_chunks.append(audio)

        if not audio_chunks:
            return {"ok": False, "error": "No audio generated"}

        import numpy as np
        audio = np.concatenate(audio_chunks)

        out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(out.name, audio, 24000)

        return {
            "ok": True,
            "path": out.name,
            "voice": v,
            "duration_s": round(len(audio) / 24000, 2),
        }
    except ImportError:
        return {"ok": False, "error": "Kokoro TTS not installed. Run POST /api/v1/voice/enable"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_voice(voice_id: str) -> dict:
    """Set the active voice."""
    global _VOICE
    _VOICE = voice_id
    return {"ok": True, "voice": voice_id}


def set_speed(speed: float) -> dict:
    """Set speech speed (0.5 to 2.0)."""
    global _SPEED
    _SPEED = max(0.5, min(2.0, speed))
    return {"ok": True, "speed": _SPEED}


def get_voices() -> list:
    """Get available voices."""
    # Built-in + custom voice packs from ~/.valhalla/voices/
    voices = []
    for vid, vinfo in VOICES.items():
        voices.append({
            "id": vid,
            "name": vinfo["name"],
            "lang": vinfo["lang"],
            "style": vinfo["style"],
            "active": vid == _VOICE,
        })

    # Custom voice packs
    custom_dir = Path.home() / ".valhalla" / "voices"
    if custom_dir.exists():
        for vf in custom_dir.glob("*.json"):
            try:
                vdata = json.loads(vf.read_text())
                voices.append({
                    "id": vdata.get("id", vf.stem),
                    "name": vdata.get("name", vf.stem),
                    "lang": vdata.get("lang", "en"),
                    "style": vdata.get("style", "custom"),
                    "active": vdata.get("id", vf.stem) == _VOICE,
                    "custom": True,
                })
            except Exception:
                pass

    return voices


def get_info() -> dict:
    """Get TTS engine info."""
    return {
        "engine": "kokoro",
        "voice": _VOICE,
        "speed": _SPEED,
        "installed": is_installed(),
        "vram_required_gb": 0,
        "voices_count": len(VOICES),
    }

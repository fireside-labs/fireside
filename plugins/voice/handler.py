"""
voice/handler.py — Voice I/O API.

Routes:
  GET  /api/v1/voice/status   — Voice capability + status
  POST /api/v1/voice/enable   — Download + load STT/TTS models
  POST /api/v1/voice/disable  — Unload models, free VRAM
  GET  /api/v1/voice/voices   — List installed voices
  PUT  /api/v1/voice/select   — Switch active voice
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("valhalla.voice")

_BASE_DIR = Path(".")
_ENABLED = False


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


def _get_free_vram() -> float:
    """Estimate free VRAM after main brain."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "consumer_handler",
            str(_BASE_DIR / "plugins" / "consumer-api" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        total = mod._detect_vram_gb()
        # Assume brain uses ~60% of VRAM
        return round(total * 0.4, 1)
    except Exception:
        return 0.0


class VoiceSelectRequest(BaseModel):
    voice_id: str
    speed: float = 1.0


def register_routes(app, config: dict) -> None:
    global _BASE_DIR

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))

    router = APIRouter(tags=["voice"])

    @router.get("/api/v1/voice/status")
    async def api_status():
        """Voice capability detection."""
        from plugins.voice.stt import get_info as stt_info
        from plugins.voice.tts import get_info as tts_info

        free_vram = _get_free_vram()
        stt = stt_info()
        tts = tts_info()

        stt_possible = free_vram >= 1.5 or stt["loaded"]
        tts_possible = True  # CPU only

        if stt_possible and tts_possible:
            availability = "available"
        elif tts_possible:
            availability = "tts_only"
        else:
            availability = "not_recommended"

        return {
            "enabled": _ENABLED,
            "availability": availability,
            "free_vram_gb": free_vram,
            "stt": stt,
            "tts": tts,
            "tip": None if stt_possible else "Use a smaller brain to free VRAM for voice",
        }

    @router.post("/api/v1/voice/enable")
    async def api_enable():
        """Download and load voice models."""
        global _ENABLED
        from plugins.voice.stt import is_installed as stt_ok, install as stt_install, load_model
        from plugins.voice.tts import is_installed as tts_ok, install as tts_install

        results = {}

        # Install STT if needed
        if not stt_ok():
            r = stt_install()
            results["stt_install"] = r
            if not r.get("ok"):
                raise HTTPException(status_code=500, detail=f"STT install failed: {r.get('error')}")

        # Install TTS if needed
        if not tts_ok():
            r = tts_install()
            results["tts_install"] = r
            if not r.get("ok"):
                raise HTTPException(status_code=500, detail=f"TTS install failed: {r.get('error')}")

        # Load STT model
        r = load_model("medium")
        results["stt_load"] = r
        if not r.get("ok"):
            raise HTTPException(status_code=500, detail=f"STT load failed: {r.get('error')}")

        _ENABLED = True
        _publish("voice.enabled", {"stt": "whisper-medium", "tts": "kokoro"})
        return {"ok": True, "enabled": True, **results}

    @router.post("/api/v1/voice/disable")
    async def api_disable():
        """Unload models and free VRAM."""
        global _ENABLED
        from plugins.voice.stt import unload_model
        unload_model()
        _ENABLED = False
        _publish("voice.disabled", {})
        return {"ok": True, "enabled": False}

    @router.get("/api/v1/voice/voices")
    async def api_voices():
        """List available voices."""
        from plugins.voice.tts import get_voices
        voices = get_voices()
        return {"voices": voices, "count": len(voices)}

    @router.put("/api/v1/voice/select")
    async def api_select(req: VoiceSelectRequest):
        """Switch active voice."""
        from plugins.voice.tts import set_voice, set_speed
        set_voice(req.voice_id)
        if req.speed != 1.0:
            set_speed(req.speed)
        return {"ok": True, "voice": req.voice_id, "speed": req.speed}

    app.include_router(router)
    log.info("[voice] Plugin loaded. Enabled: %s", _ENABLED)

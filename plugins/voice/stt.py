"""
voice/stt.py — Speech-to-Text via faster-whisper (Whisper, local).

Uses CTranslate2 backend for fastest inference.
Whisper medium needs ~1.5GB VRAM.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("valhalla.voice.stt")

_MODEL = None
_MODEL_SIZE = "medium"


def is_installed() -> bool:
    """Check if faster-whisper is installed."""
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def install() -> dict:
    """Install faster-whisper."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "faster-whisper", "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": str(e)}


def load_model(model_size: str = "medium") -> dict:
    """Load Whisper model."""
    global _MODEL, _MODEL_SIZE
    try:
        from faster_whisper import WhisperModel
        _MODEL_SIZE = model_size
        _MODEL = WhisperModel(
            model_size,
            device="auto",
            compute_type="auto",
        )
        log.info("[stt] Loaded Whisper %s", model_size)
        return {"ok": True, "model": model_size}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def transcribe(audio_path: str, language: str = "en") -> dict:
    """Transcribe audio file to text."""
    if not _MODEL:
        return {"ok": False, "error": "STT model not loaded"}

    try:
        segments, info = _MODEL.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        return {
            "ok": True,
            "text": text,
            "language": info.language,
            "duration": info.duration,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def transcribe_bytes(audio_data: bytes, language: str = "en") -> dict:
    """Transcribe raw audio bytes."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
        f.write(audio_data)
        f.flush()
        return transcribe(f.name, language)


def unload_model() -> dict:
    """Unload model to free VRAM."""
    global _MODEL
    _MODEL = None
    log.info("[stt] Model unloaded")
    return {"ok": True}


def get_info() -> dict:
    """Get STT engine info."""
    return {
        "engine": "faster-whisper",
        "model": _MODEL_SIZE,
        "loaded": _MODEL is not None,
        "installed": is_installed(),
        "vram_required_gb": 1.5,
    }

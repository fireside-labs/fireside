"""
Voice Input — Fireside Plugin.

CPU-only speech-to-text using faster-whisper (CTranslate2 backend).
No VRAM needed — runs alongside the LLM without conflict.

Model: whisper-base (142 MB) — downloaded when user enables the plugin.
Latency: ~1-2 sec on mid-range CPU for short phrases.

Routes:
    POST /tools/voice/enable     — Enable voice: downloads Whisper model
    POST /tools/voice/disable    — Disable voice: unloads model from memory
    POST /tools/voice/transcribe — Transcribe audio (multipart upload)
    GET  /tools/voice/status     — Check if whisper model is loaded
"""

import logging
import os
import tempfile
import threading
from pathlib import Path

log = logging.getLogger("valhalla.voice")

# Model config — base is the sweet spot (142 MB, fast, good quality)
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE", "int8")  # int8 = fastest on CPU

_model = None
_model_loading = False
_download_progress = {"status": "idle", "message": ""}  # idle, downloading, ready, error


def _load_model_sync():
    """Load the Whisper model (blocks until done). Called from background thread."""
    global _model, _model_loading, _download_progress
    if _model is not None:
        _download_progress = {"status": "ready", "message": "Model loaded"}
        return True

    _model_loading = True
    _download_progress = {"status": "downloading", "message": f"Downloading whisper-{MODEL_SIZE} model..."}

    try:
        from faster_whisper import WhisperModel
        log.info("[voice] Loading whisper '%s' model (device=%s, compute=%s)...",
                 MODEL_SIZE, WHISPER_DEVICE, COMPUTE_TYPE)
        _download_progress = {"status": "downloading", "message": f"Loading whisper-{MODEL_SIZE} into memory..."}
        _model = WhisperModel(MODEL_SIZE, device=WHISPER_DEVICE, compute_type=COMPUTE_TYPE)
        _download_progress = {"status": "ready", "message": "Voice input ready"}
        log.info("[voice] Whisper model loaded successfully")
        return True
    except ImportError:
        _download_progress = {"status": "error", "message": "faster-whisper not installed"}
        log.error("[voice] faster-whisper not installed. Run: pip install faster-whisper")
        return False
    except Exception as e:
        _download_progress = {"status": "error", "message": str(e)}
        log.error("[voice] Failed to load whisper model: %s", e)
        return False
    finally:
        _model_loading = False


def enable_voice() -> dict:
    """
    Enable voice input: download + load the Whisper model.
    Called when user enables voice from the store/settings.
    Runs in background thread so it doesn't block the API.
    """
    global _download_progress
    if _model is not None:
        return {"ok": True, "status": "ready", "message": "Voice already enabled"}
    if _model_loading:
        return {"ok": True, "status": "downloading", "message": "Model download in progress..."}

    _download_progress = {"status": "downloading", "message": "Starting download..."}

    def _bg():
        _load_model_sync()

    thread = threading.Thread(target=_bg, daemon=True)
    thread.start()

    return {
        "ok": True,
        "status": "downloading",
        "message": f"Downloading whisper-{MODEL_SIZE} model (~142 MB). This is a one-time setup.",
    }


def disable_voice() -> dict:
    """Disable voice: unload model from memory."""
    global _model, _download_progress
    _model = None
    _download_progress = {"status": "idle", "message": "Voice disabled"}
    log.info("[voice] Model unloaded, voice disabled")
    return {"ok": True, "message": "Voice disabled, model unloaded from memory"}


def transcribe_audio(audio_path: str, language: str = None) -> dict:
    """
    Transcribe an audio file to text using Whisper.

    Args:
        audio_path: Path to audio file (wav, mp3, webm, ogg, m4a)
        language: Optional language code (e.g. 'en'). Auto-detected if not set.

    Returns:
        {"ok": True, "text": "...", "language": "en", "segments": [...]}
    """
    if _model is None:
        if _model_loading:
            return {"ok": False, "error": "Model is still loading. Please wait..."}
        return {"ok": False, "error": "Voice not enabled. Enable it from Settings → Plugins."}

    if not os.path.exists(audio_path):
        return {"ok": False, "error": f"Audio file not found: {audio_path}"}

    try:
        segments, info = _model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # Skip silence — faster
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        # Collect all segments
        text_parts = []
        segment_list = []
        for segment in segments:
            text_parts.append(segment.text.strip())
            segment_list.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
            })

        full_text = " ".join(text_parts)

        return {
            "ok": True,
            "text": full_text,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 2),
            "segments": segment_list,
        }

    except Exception as e:
        log.error("[voice] Transcription failed: %s", e)
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# FastAPI route registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict = None):
    """Register voice transcription routes."""
    from fastapi import UploadFile, File as FastFile, Form

    @app.post("/tools/voice/enable")
    async def handle_enable():
        """Enable voice: download + load the Whisper model."""
        return enable_voice()

    @app.post("/tools/voice/disable")
    async def handle_disable():
        """Disable voice: unload model from memory."""
        return disable_voice()

    @app.get("/tools/voice/download-progress")
    async def handle_progress():
        """Check download/loading progress."""
        return {"ok": True, **_download_progress, "model_loaded": _model is not None}

    @app.post("/tools/voice/transcribe")
    async def handle_transcribe(
        file: UploadFile = FastFile(...),
        language: str = Form(default=None),
    ):
        """Transcribe uploaded audio to text."""
        # Save to temp file
        suffix = Path(file.filename).suffix if file.filename else ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = transcribe_audio(tmp_path, language=language)
            return result
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    @app.get("/tools/voice/status")
    async def handle_status():
        """Check if Whisper model is loaded and ready."""
        try:
            import faster_whisper
            installed = True
        except ImportError:
            installed = False

        return {
            "ok": True,
            "installed": installed,
            "model_loaded": _model is not None,
            "model_loading": _model_loading,
            "model_size": MODEL_SIZE,
            "device": WHISPER_DEVICE,
            "compute_type": COMPUTE_TYPE,
            "download_status": _download_progress.get("status", "idle"),
        }

    log.info("[voice] Routes registered (with enable/disable)")


"""
Voice Input — Fireside Plugin.

CPU-only speech-to-text using faster-whisper (CTranslate2 backend).
No VRAM needed — runs alongside the LLM without conflict.

Model: whisper-base (142 MB) — auto-downloaded on first use.
Latency: ~1-2 sec on mid-range CPU for short phrases.

Routes:
    POST /tools/voice/transcribe — Transcribe audio (multipart upload)
    GET  /tools/voice/status     — Check if whisper model is loaded
"""

import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger("valhalla.voice")

# Model config — base is the sweet spot (142 MB, fast, good quality)
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE", "int8")  # int8 = fastest on CPU

_model = None
_model_loading = False


def _get_model():
    """Lazy-load the Whisper model on first transcription request."""
    global _model, _model_loading
    if _model is not None:
        return _model
    if _model_loading:
        return None

    _model_loading = True
    try:
        from faster_whisper import WhisperModel
        log.info("[voice] Loading whisper '%s' model (device=%s, compute=%s)...",
                 MODEL_SIZE, WHISPER_DEVICE, COMPUTE_TYPE)
        _model = WhisperModel(MODEL_SIZE, device=WHISPER_DEVICE, compute_type=COMPUTE_TYPE)
        log.info("[voice] Whisper model loaded successfully")
        return _model
    except ImportError:
        log.error("[voice] faster-whisper not installed. Run: pip install faster-whisper")
        return None
    except Exception as e:
        log.error("[voice] Failed to load whisper model: %s", e)
        return None
    finally:
        _model_loading = False


def transcribe_audio(audio_path: str, language: str = None) -> dict:
    """
    Transcribe an audio file to text using Whisper.

    Args:
        audio_path: Path to audio file (wav, mp3, webm, ogg, m4a)
        language: Optional language code (e.g. 'en'). Auto-detected if not set.

    Returns:
        {"ok": True, "text": "...", "language": "en", "segments": [...]}
    """
    model = _get_model()
    if model is None:
        return {
            "ok": False,
            "error": "Whisper model not available. Install: pip install faster-whisper",
        }

    if not os.path.exists(audio_path):
        return {"ok": False, "error": f"Audio file not found: {audio_path}"}

    try:
        segments, info = model.transcribe(
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
        model_ready = _model is not None
        try:
            import faster_whisper
            installed = True
        except ImportError:
            installed = False

        return {
            "ok": True,
            "installed": installed,
            "model_loaded": model_ready,
            "model_size": MODEL_SIZE,
            "device": WHISPER_DEVICE,
            "compute_type": COMPUTE_TYPE,
        }

    log.info("[voice] Routes registered: /tools/voice/transcribe, /tools/voice/status")

"""
companion/nllb.py — NLLB Translation Wrapper.

Uses Meta's NLLB-200-distilled-600M model for offline translation.
Supports 200 languages. ~600MB download.

API: POST /api/v1/companion/translate
  - source_lang (auto-detect if empty)
  - target_lang
  - text
  → translated text

Priority languages: Spanish, Chinese, Arabic, Hindi, Korean, Tagalog,
Vietnamese, French, German, Japanese, Portuguese, Russian, Urdu, Bengali, Turkish.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

log = logging.getLogger("valhalla.companion.nllb")

# ---------------------------------------------------------------------------
# Language codes (NLLB format: xxx_Xxxx)
# ---------------------------------------------------------------------------

LANGUAGES = {
    # Priority languages
    "en": {"nllb": "eng_Latn", "name": "English"},
    "es": {"nllb": "spa_Latn", "name": "Spanish"},
    "zh": {"nllb": "zho_Hans", "name": "Chinese (Simplified)"},
    "zh-tw": {"nllb": "zho_Hant", "name": "Chinese (Traditional)"},
    "ar": {"nllb": "arb_Arab", "name": "Arabic"},
    "hi": {"nllb": "hin_Deva", "name": "Hindi"},
    "ko": {"nllb": "kor_Hang", "name": "Korean"},
    "tl": {"nllb": "tgl_Latn", "name": "Tagalog"},
    "vi": {"nllb": "vie_Latn", "name": "Vietnamese"},
    "fr": {"nllb": "fra_Latn", "name": "French"},
    "de": {"nllb": "deu_Latn", "name": "German"},
    "ja": {"nllb": "jpn_Jpan", "name": "Japanese"},
    "pt": {"nllb": "por_Latn", "name": "Portuguese"},
    "ru": {"nllb": "rus_Cyrl", "name": "Russian"},
    "ur": {"nllb": "urd_Arab", "name": "Urdu"},
    "bn": {"nllb": "ben_Beng", "name": "Bengali"},
    "tr": {"nllb": "tur_Latn", "name": "Turkish"},
    # Additional common languages
    "it": {"nllb": "ita_Latn", "name": "Italian"},
    "nl": {"nllb": "nld_Latn", "name": "Dutch"},
    "pl": {"nllb": "pol_Latn", "name": "Polish"},
    "th": {"nllb": "tha_Thai", "name": "Thai"},
    "id": {"nllb": "ind_Latn", "name": "Indonesian"},
    "ms": {"nllb": "zsm_Latn", "name": "Malay"},
    "sv": {"nllb": "swe_Latn", "name": "Swedish"},
    "da": {"nllb": "dan_Latn", "name": "Danish"},
    "no": {"nllb": "nob_Latn", "name": "Norwegian"},
    "fi": {"nllb": "fin_Latn", "name": "Finnish"},
    "el": {"nllb": "ell_Grek", "name": "Greek"},
    "he": {"nllb": "heb_Hebr", "name": "Hebrew"},
    "uk": {"nllb": "ukr_Cyrl", "name": "Ukrainian"},
    "ro": {"nllb": "ron_Latn", "name": "Romanian"},
    "hu": {"nllb": "hun_Latn", "name": "Hungarian"},
    "cs": {"nllb": "ces_Latn", "name": "Czech"},
    "sw": {"nllb": "swh_Latn", "name": "Swahili"},
    "am": {"nllb": "amh_Ethi", "name": "Amharic"},
    "fa": {"nllb": "pes_Arab", "name": "Persian"},
    "ta": {"nllb": "tam_Taml", "name": "Tamil"},
    "te": {"nllb": "tel_Telu", "name": "Telugu"},
    "mr": {"nllb": "mar_Deva", "name": "Marathi"},
    "my": {"nllb": "mya_Mymr", "name": "Burmese"},
    "km": {"nllb": "khm_Khmr", "name": "Khmer"},
}

# Model state
_model = None
_tokenizer = None
_installed = False


# ---------------------------------------------------------------------------
# Auto-detect language (heuristic)
# ---------------------------------------------------------------------------

# Script-based detection patterns
_SCRIPT_PATTERNS = [
    ("ja", re.compile(r"[\u3040-\u309F\u30A0-\u30FF]")),          # Hiragana/Katakana
    ("ko", re.compile(r"[\uAC00-\uD7AF]")),                       # Hangul
    ("zh", re.compile(r"[\u4E00-\u9FFF]")),                        # CJK
    ("ar", re.compile(r"[\u0600-\u06FF]")),                        # Arabic
    ("hi", re.compile(r"[\u0900-\u097F]")),                        # Devanagari
    ("bn", re.compile(r"[\u0980-\u09FF]")),                        # Bengali
    ("th", re.compile(r"[\u0E00-\u0E7F]")),                        # Thai
    ("ta", re.compile(r"[\u0B80-\u0BFF]")),                        # Tamil
    ("te", re.compile(r"[\u0C00-\u0C7F]")),                        # Telugu
    ("my", re.compile(r"[\u1000-\u109F]")),                        # Myanmar
    ("km", re.compile(r"[\u1780-\u17FF]")),                        # Khmer
    ("he", re.compile(r"[\u0590-\u05FF]")),                        # Hebrew
    ("ru", re.compile(r"[\u0400-\u04FF]")),                        # Cyrillic
    ("el", re.compile(r"[\u0370-\u03FF]")),                        # Greek
    ("am", re.compile(r"[\u1200-\u137F]")),                        # Ethiopic
]

# Common word patterns for Latin-script languages
_WORD_PATTERNS = {
    "es": ["el", "la", "los", "las", "de", "en", "que", "por", "con", "una", "es", "está"],
    "fr": ["le", "la", "les", "de", "des", "un", "une", "et", "est", "que", "dans", "pour"],
    "de": ["der", "die", "das", "und", "ist", "ein", "eine", "mit", "auf", "nicht", "den"],
    "pt": ["o", "a", "os", "as", "de", "em", "que", "por", "com", "uma", "não"],
    "it": ["il", "la", "di", "che", "non", "è", "un", "una", "per", "del", "con"],
    "nl": ["de", "het", "een", "van", "en", "is", "dat", "op", "voor", "niet"],
    "tr": ["bir", "ve", "bu", "için", "ile", "olan", "gibi", "daha"],
    "id": ["yang", "dan", "di", "ini", "itu", "dengan", "untuk", "dari"],
    "tl": ["ang", "ng", "sa", "na", "mga", "at", "ay", "ko", "ka"],
    "vi": ["của", "và", "là", "trong", "có", "được", "một", "này"],
}


def detect_language(text: str) -> str:
    """Auto-detect language from text. Returns ISO 639-1 code."""
    if not text or not text.strip():
        return "en"

    # Check script-based patterns first
    for lang, pattern in _SCRIPT_PATTERNS:
        if pattern.search(text):
            return lang

    # Word-frequency check for Latin-script languages
    words = set(text.lower().split())
    best_lang = "en"
    best_score = 0

    for lang, markers in _WORD_PATTERNS.items():
        score = sum(1 for m in markers if m in words)
        if score > best_score:
            best_score = score
            best_lang = lang

    # Need at least 2 marker words to override English default
    return best_lang if best_score >= 2 else "en"


def get_nllb_code(lang: str) -> str:
    """Convert ISO 639-1 to NLLB code."""
    info = LANGUAGES.get(lang)
    if info:
        return info["nllb"]
    return "eng_Latn"


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

def is_installed() -> bool:
    """Check if NLLB model is available."""
    try:
        import transformers  # noqa
        return True
    except ImportError:
        return False


def install() -> dict:
    """Install NLLB dependencies."""
    import subprocess
    try:
        subprocess.check_call(
            ["pip", "install", "transformers", "sentencepiece", "torch"],
            stdout=subprocess.DEVNULL,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def load_model():
    """Load the NLLB model (lazy, first-use)."""
    global _model, _tokenizer, _installed
    if _model is not None:
        return

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        model_name = "facebook/nllb-200-distilled-600M"
        log.info("[nllb] Loading %s...", model_name)
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        _installed = True
        log.info("[nllb] Model loaded.")
    except Exception as e:
        log.error("[nllb] Failed to load model: %s", e)
        raise


def translate(text: str, target_lang: str, source_lang: str = "") -> dict:
    """Translate text using NLLB-200.

    Args:
        text: Text to translate
        target_lang: ISO 639-1 target language code
        source_lang: ISO 639-1 source language (auto-detect if empty)

    Returns:
        dict with translated text, detected source, confidence info
    """
    if not text or not text.strip():
        return {"ok": False, "error": "Empty text"}

    # Auto-detect source
    detected = source_lang or detect_language(text)
    source_nllb = get_nllb_code(detected)
    target_nllb = get_nllb_code(target_lang)

    if source_nllb == target_nllb:
        return {
            "ok": True,
            "translated": text,
            "source_lang": detected,
            "target_lang": target_lang,
            "note": "Source and target are the same language",
        }

    # Try NLLB model
    try:
        load_model()
        _tokenizer.src_lang = source_nllb
        inputs = _tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
        target_token_id = _tokenizer.convert_tokens_to_ids(target_nllb)
        outputs = _model.generate(
            **inputs,
            forced_bos_token_id=target_token_id,
            max_new_tokens=512,
        )
        translated = _tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]

        return {
            "ok": True,
            "translated": translated,
            "source_lang": detected,
            "target_lang": target_lang,
            "model": "nllb-200-distilled-600M",
        }
    except ImportError:
        # Fallback: return original with note
        return {
            "ok": False,
            "error": "NLLB model not installed. Run: pip install transformers sentencepiece torch",
            "source_lang": detected,
            "original": text,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "source_lang": detected}


def get_languages() -> list:
    """List all supported languages."""
    return [
        {"code": code, "name": info["name"], "nllb": info["nllb"]}
        for code, info in sorted(LANGUAGES.items(), key=lambda x: x[1]["name"])
    ]


def get_info() -> dict:
    """Get translation engine info."""
    return {
        "engine": "NLLB-200",
        "model": "nllb-200-distilled-600M",
        "size_mb": 600,
        "languages": len(LANGUAGES),
        "installed": is_installed(),
        "offline": True,
    }

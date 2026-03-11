"""
Tests for Sprint 14 — Translation + Message Guardian.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO_ROOT = Path(os.path.dirname(__file__)).parent


def _load_module(plugin_name: str, filename: str = "handler.py"):
    filepath = REPO_ROOT / "plugins" / plugin_name / filename
    safe_name = f"test_{plugin_name}_{filename}".replace("/", "_").replace(".py", "").replace("-", "_")
    spec = importlib.util.spec_from_file_location(safe_name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# NLLB Translation
# ---------------------------------------------------------------------------

class TestNLLBLanguages:
    def test_language_count(self):
        mod = _load_module("companion", "nllb.py")
        assert len(mod.LANGUAGES) >= 37

    def test_priority_languages_present(self):
        mod = _load_module("companion", "nllb.py")
        priority = ["en", "es", "zh", "ar", "hi", "ko", "tl", "vi",
                     "fr", "de", "ja", "pt", "ru", "ur", "bn", "tr"]
        for lang in priority:
            assert lang in mod.LANGUAGES, f"Missing priority language: {lang}"

    def test_nllb_codes_format(self):
        mod = _load_module("companion", "nllb.py")
        for code, info in mod.LANGUAGES.items():
            # NLLB codes are xxx_Xxxx format
            nllb = info["nllb"]
            assert "_" in nllb, f"Invalid NLLB code for {code}: {nllb}"

    def test_get_languages_list(self):
        mod = _load_module("companion", "nllb.py")
        langs = mod.get_languages()
        assert len(langs) >= 37
        assert all("code" in l and "name" in l for l in langs)

    def test_get_info(self):
        mod = _load_module("companion", "nllb.py")
        info = mod.get_info()
        assert info["engine"] == "NLLB-200"
        assert info["size_mb"] == 600
        assert info["offline"] is True


class TestLanguageDetection:
    def test_detect_japanese(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("こんにちは世界") == "ja"

    def test_detect_korean(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("안녕하세요") == "ko"

    def test_detect_chinese(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("你好世界") == "zh"

    def test_detect_arabic(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("مرحبا بالعالم") == "ar"

    def test_detect_russian(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("Привет мир") == "ru"

    def test_detect_spanish(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("el gato está en la casa") == "es"

    def test_detect_french(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("le chat est dans la maison") == "fr"

    def test_default_english(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("hello world") == "en"

    def test_empty_string(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("") == "en"

    def test_detect_hindi(self):
        mod = _load_module("companion", "nllb.py")
        assert mod.detect_language("नमस्ते दुनिया") == "hi"

    def test_same_lang_passthrough(self):
        """Translate from English to English should return same text."""
        mod = _load_module("companion", "nllb.py")
        result = mod.translate("hello", "en", "en")
        assert result["ok"]
        assert result["translated"] == "hello"


# ---------------------------------------------------------------------------
# Message Guardian
# ---------------------------------------------------------------------------

class TestSentiment:
    def test_angry(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.classify_sentiment("I hate this stupid thing!")
        assert result["label"] == "angry"

    def test_sad(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.classify_sentiment("I'm so sorry, I feel lonely and sad")
        assert result["label"] == "sad"

    def test_happy(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.classify_sentiment("This is amazing and wonderful! Love it!")
        assert result["label"] == "happy"

    def test_neutral(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.classify_sentiment("The meeting is at 3pm")
        assert result["label"] == "neutral"


class TestRegretDetection:
    def test_late_night(self):
        mod = _load_module("companion", "guardian.py")
        flags = mod.detect_regret_flags("hey what's up", hour=3)
        types = [f["type"] for f in flags]
        assert "late_night" in types

    def test_all_caps(self):
        mod = _load_module("companion", "guardian.py")
        flags = mod.detect_regret_flags("I CANNOT BELIEVE YOU DID THIS TO ME")
        types = [f["type"] for f in flags]
        assert "all_caps" in types

    def test_ex_partner(self):
        mod = _load_module("companion", "guardian.py")
        flags = mod.detect_regret_flags("I miss you", recipient="my ex girlfriend")
        types = [f["type"] for f in flags]
        assert "ex_partner" in types

    def test_reply_all(self):
        mod = _load_module("companion", "guardian.py")
        flags = mod.detect_regret_flags("reply all: you're all incompetent")
        types = [f["type"] for f in flags]
        assert "reply_all" in types

    def test_profanity(self):
        mod = _load_module("companion", "guardian.py")
        flags = mod.detect_regret_flags("what the fuck is this shit")
        types = [f["type"] for f in flags]
        assert "profanity" in types

    def test_clean_message_no_flags(self):
        mod = _load_module("companion", "guardian.py")
        flags = mod.detect_regret_flags("See you at the meeting tomorrow", hour=14)
        assert len(flags) == 0


class TestGuardianAnalysis:
    def test_high_risk(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.analyze_message(
            "I HATE YOU AND I NEVER WANT TO SEE YOU AGAIN",
            hour=3, recipient="my ex", species="cat",
        )
        assert result["risk_level"] == "high"
        assert "2am" in result["warning"].lower() or "sure" in result["warning"].lower()

    def test_no_risk(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.analyze_message("See you at 3pm!", hour=14)
        assert result["risk_level"] in ("none", "low")

    def test_species_warnings(self):
        mod = _load_module("companion", "guardian.py")
        for species in ["cat", "dog", "penguin", "fox", "owl", "dragon"]:
            result = mod.analyze_message(
                "I HATE EVERYTHING", hour=3, species=species,
            )
            assert result["warning"], f"No warning for {species}"

    def test_softer_version(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.suggest_softer("you always do this wrong")
        assert "it sometimes feels like" in result.lower()

    def test_empty_message(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.analyze_message("")
        assert result["risk_level"] == "none"

    def test_actions_provided(self):
        mod = _load_module("companion", "guardian.py")
        result = mod.analyze_message("WHAT THE FUCK", hour=3)
        assert "send_anyway" in result["actions"]
        assert "edit" in result["actions"]


# ---------------------------------------------------------------------------
# Plugin files
# ---------------------------------------------------------------------------

class TestPluginFiles:
    def test_nllb_exists(self):
        assert (REPO_ROOT / "plugins" / "companion" / "nllb.py").exists()

    def test_guardian_exists(self):
        assert (REPO_ROOT / "plugins" / "companion" / "guardian.py").exists()

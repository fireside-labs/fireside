"""
Tests for Sprint 9 — Voice + Payments + Alerts + Model Router.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
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
# Voice STT
# ---------------------------------------------------------------------------

class TestVoiceSTT:
    def test_stt_info(self):
        mod = _load_module("voice", "stt.py")
        info = mod.get_info()
        assert info["engine"] == "faster-whisper"
        assert info["vram_required_gb"] == 1.5

    def test_stt_not_loaded(self):
        mod = _load_module("voice", "stt.py")
        result = mod.transcribe("/nonexistent.wav")
        assert not result["ok"]
        assert "not loaded" in result["error"]


# ---------------------------------------------------------------------------
# Voice TTS
# ---------------------------------------------------------------------------

class TestVoiceTTS:
    def test_tts_info(self):
        mod = _load_module("voice", "tts.py")
        info = mod.get_info()
        assert info["engine"] == "kokoro"
        assert info["vram_required_gb"] == 0

    def test_builtin_voices(self):
        mod = _load_module("voice", "tts.py")
        voices = mod.get_voices()
        assert len(voices) >= 5
        names = [v["name"] for v in voices]
        assert any("Female" in n for n in names)
        assert any("Male" in n for n in names)

    def test_set_voice(self):
        mod = _load_module("voice", "tts.py")
        result = mod.set_voice("am_deep")
        assert result["ok"]
        assert result["voice"] == "am_deep"

    def test_set_speed(self):
        mod = _load_module("voice", "tts.py")
        result = mod.set_speed(1.5)
        assert result["ok"]
        assert result["speed"] == 1.5

    def test_speed_clamped(self):
        mod = _load_module("voice", "tts.py")
        mod.set_speed(999)
        assert mod._SPEED == 2.0


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class TestPayments:
    def test_webhook_signature_bad(self):
        mod = _load_module("payments")
        assert not mod.verify_webhook_signature(b"test", "bad", "secret")

    def test_handler_has_routes(self):
        mod = _load_module("payments")
        assert hasattr(mod, "register_routes")

    def test_purchases_persistence(self):
        mod = _load_module("payments")
        f = mod._purchases_file()
        # Should not crash
        purchases = mod._load_purchases()
        assert isinstance(purchases, list)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class TestAlerts:
    def test_alert_rules_defined(self):
        mod = _load_module("alerts")
        assert len(mod.ALERT_RULES) >= 5

    def test_alert_rules_have_fields(self):
        mod = _load_module("alerts")
        for rid, rule in mod.ALERT_RULES.items():
            assert "name" in rule
            assert "desc" in rule
            assert "icon" in rule
            assert "trigger_event" in rule

    def test_on_event_exists(self):
        mod = _load_module("alerts")
        assert hasattr(mod, "on_event")

    def test_event_processing(self):
        mod = _load_module("alerts")
        # Should not crash on unknown event
        mod.on_event("unknown.event", {"data": 1})


# ---------------------------------------------------------------------------
# Model Router — OpenAI Provider
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    def test_info(self):
        mod = _load_module("model-router", "providers/openai.py")
        info = mod.get_info()
        assert info["provider"] == "openai"
        assert "gpt-4o" in info["models"]
        assert info["supports_streaming"]

    def test_bad_key(self):
        mod = _load_module("model-router", "providers/openai.py")
        result = mod.validate_key("bad-key")
        assert not result.get("ok")


# ---------------------------------------------------------------------------
# Model Router — Anthropic Provider
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    def test_info(self):
        mod = _load_module("model-router", "providers/anthropic.py")
        info = mod.get_info()
        assert info["provider"] == "anthropic"
        assert any("claude" in m for m in info["models"])

    def test_bad_key(self):
        mod = _load_module("model-router", "providers/anthropic.py")
        result = mod.validate_key("bad-key")
        assert not result.get("ok")


# ---------------------------------------------------------------------------
# Model Router — Google Provider
# ---------------------------------------------------------------------------

class TestGoogleProvider:
    def test_info(self):
        mod = _load_module("model-router", "providers/google.py")
        info = mod.get_info()
        assert info["provider"] == "google"
        assert any("gemini" in m for m in info["models"])

    def test_bad_key(self):
        mod = _load_module("model-router", "providers/google.py")
        result = mod.validate_key("bad-key")
        assert not result.get("ok")


# ---------------------------------------------------------------------------
# Bug Fixes
# ---------------------------------------------------------------------------

class TestBugFixes:
    def test_philosopher_rename(self):
        """Master Debater renamed to Philosopher."""
        mod = _load_module("agent_profiles", "achievements.py")
        assert mod.ACHIEVEMENTS["debate_win_10"]["name"] == "Philosopher"


# ---------------------------------------------------------------------------
# Plugin Structure
# ---------------------------------------------------------------------------

class TestPluginStructure:
    def test_voice_manifest(self):
        assert (REPO_ROOT / "plugins" / "voice" / "plugin.yaml").exists()

    def test_payments_manifest(self):
        assert (REPO_ROOT / "plugins" / "payments" / "plugin.yaml").exists()

    def test_alerts_manifest(self):
        assert (REPO_ROOT / "plugins" / "alerts" / "plugin.yaml").exists()

    def test_model_router_providers(self):
        providers = REPO_ROOT / "plugins" / "model-router" / "providers"
        assert (providers / "openai.py").exists()
        assert (providers / "anthropic.py").exists()
        assert (providers / "google.py").exists()

    def test_total_plugins_now_22(self):
        plugins_dir = REPO_ROOT / "plugins"
        dirs = [d for d in plugins_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")]
        assert len(dirs) >= 22, f"Expected 22, found {len(dirs)}: {[d.name for d in dirs]}"

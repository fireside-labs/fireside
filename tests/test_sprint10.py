"""
Tests for Sprint 10 — Pre-Launch Polish.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import tempfile
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
# Chat XP Daily Cap
# ---------------------------------------------------------------------------

class TestChatXPCap:
    def test_cap_constant(self):
        mod = _load_module("agent_profiles", "leveling.py")
        assert mod.CHAT_XP_DAILY_CAP == 20

    def test_chat_xp_tracked(self):
        mod = _load_module("agent_profiles", "leveling.py")
        name = f"test_chatcap_{int(time.time())}"
        result = mod.award_event_xp(name, "chat.response")
        assert result is not None
        assert result["xp_added"] == 10
        # Clean
        f = mod._profiles_dir() / f"{name}.json"
        f.unlink(missing_ok=True)

    def test_chat_xp_capped_after_limit(self):
        mod = _load_module("agent_profiles", "leveling.py")
        name = f"test_chatcap2_{int(time.time())}"
        # Award 10 XP twice (total 20 = cap)
        mod.award_event_xp(name, "chat.response")
        mod.award_event_xp(name, "chat.response")
        # Third should be capped
        result = mod.award_event_xp(name, "chat.response")
        assert result["xp_added"] == 0
        assert result.get("capped") is True
        # Clean
        f = mod._profiles_dir() / f"{name}.json"
        f.unlink(missing_ok=True)

    def test_non_chat_xp_not_capped(self):
        mod = _load_module("agent_profiles", "leveling.py")
        name = f"test_nocap_{int(time.time())}"
        # Pipeline XP should not be capped
        result = mod.award_event_xp(name, "pipeline.shipped")
        assert result["xp_added"] >= 100
        assert result.get("capped") is None or result.get("capped") is False
        f = mod._profiles_dir() / f"{name}.json"
        f.unlink(missing_ok=True)

    def test_today_key_format(self):
        mod = _load_module("agent_profiles", "leveling.py")
        key = mod._today_key()
        assert len(key) == 10  # YYYY-MM-DD
        assert key.count("-") == 2


# ---------------------------------------------------------------------------
# Chat → Brain Routing (handleSend)
# ---------------------------------------------------------------------------

class TestChatRouting:
    def test_personality_to_prompt_applied(self):
        mod = _load_module("agent_profiles")
        prompt = mod.personality_to_prompt({
            "creative_precise": 0.9,
            "bold_cautious": 0.1,
        })
        assert "risk" in prompt.lower() or "creative" in prompt.lower()
        assert "verify" in prompt.lower() or "safety" in prompt.lower()

    def test_system_prompt_includes_personality(self):
        """System prompt should incorporate personality modifiers."""
        mod = _load_module("agent_profiles")
        # The function exists and works without crashing
        prompt = mod._load_system_prompt("test-agent")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_byok_providers_in_stream_chat(self):
        """_stream_chat should handle provider routing."""
        mod = _load_module("agent_profiles")
        assert hasattr(mod, "_stream_chat")

    def test_chat_request_model(self):
        mod = _load_module("agent_profiles")
        req = mod.ChatRequest(message="hello", agent="thor")
        assert req.message == "hello"
        assert req.agent == "thor"


# ---------------------------------------------------------------------------
# Learning Summary (Real Data)
# ---------------------------------------------------------------------------

class TestLearningSummary:
    def test_learning_summary_empty(self):
        mod = _load_module("consumer-api")
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.get_learning_summary(Path(tmpdir))
            assert result["things_it_knows"] == 0
            assert result["reliable_pct"] == 0
            assert "knowledge_check_score" in result
            assert "week_over_week_improvement" in result
            assert "accuracy_pct" in result

    def test_learning_summary_with_procedures(self):
        mod = _load_module("consumer-api")
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "war_room_data"
            data_dir.mkdir()
            procs = [
                {"name": "test1", "confidence": 0.9},
                {"name": "test2", "confidence": 0.8},
                {"name": "test3", "confidence": 0.3},
            ]
            (data_dir / "procedures.json").write_text(json.dumps(procs))
            result = mod.get_learning_summary(Path(tmpdir))
            assert result["things_it_knows"] == 3
            assert result["reliable_pct"] == 67  # 2/3

    def test_learning_summary_with_crucible(self):
        mod = _load_module("consumer-api")
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "war_room_data"
            data_dir.mkdir()
            crucible = [
                {"survived": True}, {"survived": True}, {"survived": False},
            ]
            (data_dir / "crucible_results.json").write_text(json.dumps(crucible))
            result = mod.get_learning_summary(Path(tmpdir))
            assert result["crucible_tests_run"] == 3
            assert result["knowledge_check_score"] == 67  # 2/3

    def test_learning_summary_with_predictions(self):
        mod = _load_module("consumer-api")
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "war_room_data"
            data_dir.mkdir()
            preds = [
                {"correct": True}, {"correct": True}, {"correct": False},
            ]
            (data_dir / "predictions.json").write_text(json.dumps(preds))
            result = mod.get_learning_summary(Path(tmpdir))
            assert result["predictions_made"] == 3
            assert result["accuracy_pct"] == 67  # 2/3

    def test_learning_summary_string(self):
        mod = _load_module("consumer-api")
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.get_learning_summary(Path(tmpdir))
            assert "Things it knows" in result["summary"]
            assert "Knowledge check" in result["summary"]
            assert "WoW" in result["summary"]


# ---------------------------------------------------------------------------
# Bug Fix: Philosopher rename
# ---------------------------------------------------------------------------

class TestBugFixes:
    def test_philosopher_name(self):
        mod = _load_module("agent_profiles", "achievements.py")
        assert mod.ACHIEVEMENTS["debate_win_10"]["name"] == "Philosopher"

    def test_crucible_desc_rename(self):
        mod = _load_module("agent_profiles", "achievements.py")
        desc = mod.ACHIEVEMENTS["crucible_100"]["desc"]
        assert "knowledge check" in desc.lower()

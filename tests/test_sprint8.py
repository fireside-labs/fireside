"""
Tests for Sprint 8 — Agent Profiles (RPG) + Desktop Packaging.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
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
# Leveling System
# ---------------------------------------------------------------------------

class TestLeveling:
    def test_default_profile(self):
        mod = _load_module("agent_profiles", "leveling.py")
        profile = mod._default_profile("test-agent")
        assert profile["level"] == 1
        assert profile["xp"] == 0
        assert profile["name"] == "test-agent"
        assert "personality" in profile

    def test_add_xp(self):
        mod = _load_module("agent_profiles", "leveling.py")
        # Use a unique temp agent
        name = f"test_xp_{int(time.time())}"
        result = mod.add_xp(name, 250, "test")
        assert result["xp_added"] == 250
        assert result["total_xp"] == 250
        assert result["level"] == 1
        assert not result["leveled_up"]
        # Cleanup
        f = mod._profiles_dir() / f"{name}.json"
        f.unlink(missing_ok=True)

    def test_level_up(self):
        mod = _load_module("agent_profiles", "leveling.py")
        name = f"test_lvl_{int(time.time())}"
        mod.add_xp(name, 499, "almost")
        result = mod.add_xp(name, 2, "level up!")
        assert result["leveled_up"]
        assert result["level"] == 2
        f = mod._profiles_dir() / f"{name}.json"
        f.unlink(missing_ok=True)

    def test_get_level_info(self):
        mod = _load_module("agent_profiles", "leveling.py")
        info = mod.get_level_info(1250)
        assert info["level"] == 3
        assert info["xp_in_level"] == 250
        assert info["progress_pct"] == 50

    def test_xp_rewards_defined(self):
        mod = _load_module("agent_profiles", "leveling.py")
        assert mod.XP_REWARDS["pipeline.shipped"] == 100
        assert mod.XP_REWARDS["crucible.survived"] == 50
        assert mod.XP_REWARDS["socratic.won"] == 75

    def test_award_event_xp(self):
        mod = _load_module("agent_profiles", "leveling.py")
        name = f"test_evt_{int(time.time())}"
        result = mod.award_event_xp(name, "pipeline.shipped")
        assert result is not None
        assert result["xp_added"] >= 100  # base + streak bonus
        f = mod._profiles_dir() / f"{name}.json"
        f.unlink(missing_ok=True)

    def test_unknown_event_returns_none(self):
        mod = _load_module("agent_profiles", "leveling.py")
        result = mod.award_event_xp("test", "unknown.event")
        assert result is None

    def test_update_skill(self):
        mod = _load_module("agent_profiles", "leveling.py")
        name = f"test_skill_{int(time.time())}"
        mod.update_skill(name, "python", 5)
        profile = mod.load_profile(name)
        assert profile["stats"]["skills"]["python"] == 5
        f = mod._profiles_dir() / f"{name}.json"
        f.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------

class TestAchievements:
    def test_all_achievements_defined(self):
        mod = _load_module("agent_profiles", "achievements.py")
        assert len(mod.ACHIEVEMENTS) >= 18

    def test_check_achievements_streak(self):
        mod = _load_module("agent_profiles", "achievements.py")
        profile = {
            "level": 1, "xp": 0,
            "stats": {
                "streak": 10, "tasks_completed": 10,
                "knowledge_count": 0, "crucible_survival": 0,
                "debates_won": 0, "debates_total": 0, "skills": {},
            },
            "achievements": [],
        }
        new = mod.check_achievements(profile)
        ids = [a["id"] for a in new]
        assert "streak_3" in ids
        assert "streak_5" in ids
        assert "streak_10" in ids
        assert "tasks_10" in ids

    def test_no_duplicate_achievements(self):
        mod = _load_module("agent_profiles", "achievements.py")
        profile = {
            "level": 5, "xp": 2500,
            "stats": {
                "streak": 3, "tasks_completed": 10,
                "knowledge_count": 0, "crucible_survival": 0,
                "debates_won": 0, "debates_total": 0, "skills": {},
            },
            "achievements": [{"id": "streak_3"}],  # Already has this
        }
        new = mod.check_achievements(profile)
        ids = [a["id"] for a in new]
        assert "streak_3" not in ids  # Should not re-award

    def test_get_all_achievements(self):
        mod = _load_module("agent_profiles", "achievements.py")
        all_a = mod.get_all_achievements()
        assert len(all_a) >= 18
        assert all("id" in a and "name" in a and "emoji" in a for a in all_a)

    def test_get_next_achievements(self):
        mod = _load_module("agent_profiles", "achievements.py")
        profile = {
            "level": 1, "xp": 0,
            "stats": {
                "streak": 0, "tasks_completed": 0,
                "knowledge_count": 0, "crucible_survival": 0,
                "debates_won": 0, "debates_total": 0, "skills": {},
            },
            "achievements": [],
        }
        nexts = mod.get_next_achievements(profile, limit=3)
        assert len(nexts) == 3


# ---------------------------------------------------------------------------
# Personality → Prompt
# ---------------------------------------------------------------------------

class TestPersonality:
    def test_personality_to_prompt_creative(self):
        mod = _load_module("agent_profiles")
        prompt = mod.personality_to_prompt({"creative_precise": 0.9})
        assert "creative" in prompt.lower() or "risk" in prompt.lower()

    def test_personality_to_prompt_cautious(self):
        mod = _load_module("agent_profiles")
        prompt = mod.personality_to_prompt({"bold_cautious": 0.1})
        assert "verify" in prompt.lower() or "safety" in prompt.lower()

    def test_personality_to_prompt_balanced(self):
        mod = _load_module("agent_profiles")
        prompt = mod.personality_to_prompt({
            "creative_precise": 0.5,
            "verbose_concise": 0.5,
            "bold_cautious": 0.5,
            "warm_formal": 0.5,
        })
        assert prompt == ""  # Balanced = no strong modifiers


# ---------------------------------------------------------------------------
# Desktop Packaging
# ---------------------------------------------------------------------------

class TestDesktopPackaging:
    def test_tauri_config_exists(self):
        cfg = REPO_ROOT / "tauri" / "src-tauri" / "tauri.conf.json"
        assert cfg.exists()
        data = json.loads(cfg.read_text())
        assert data["productName"] == "Valhalla"

    def test_tauri_main_rs_exists(self):
        main = REPO_ROOT / "tauri" / "src-tauri" / "src" / "main.rs"
        assert main.exists()
        content = main.read_text()
        assert "bifrost" in content
        assert "tauri" in content.lower()

    def test_windows_installer_exists(self):
        ps1 = REPO_ROOT / "install.ps1"
        assert ps1.exists()
        content = ps1.read_text()
        assert "winget" in content
        assert "valhalla" in content.lower()

    def test_tauri_csp_locked(self):
        cfg = REPO_ROOT / "tauri" / "src-tauri" / "tauri.conf.json"
        data = json.loads(cfg.read_text())
        csp = data["app"]["security"]["csp"]
        assert "localhost" in csp
        assert "self" in csp


# ---------------------------------------------------------------------------
# Plugin Structure
# ---------------------------------------------------------------------------

class TestPluginStructure:
    def test_agent_profiles_manifest(self):
        assert (REPO_ROOT / "plugins" / "agent_profiles" / "plugin.yaml").exists()

    def test_agent_profiles_handler(self):
        mod = _load_module("agent_profiles")
        assert hasattr(mod, "register_routes")
        assert hasattr(mod, "on_event")

    def test_total_plugins_now_19(self):
        plugins_dir = REPO_ROOT / "plugins"
        dirs = [d for d in plugins_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")]
        assert len(dirs) >= 19, f"Expected 19, found {len(dirs)}: {[d.name for d in dirs]}"

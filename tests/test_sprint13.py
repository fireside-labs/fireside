"""
Tests for Sprint 13 — Pocket Companion.
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
# CompanionSim Engine (Valkyrie-approved: single happiness bar)
# ---------------------------------------------------------------------------

class TestCompanionSim:
    def test_default_companion(self):
        mod = _load_module("companion", "sim.py")
        c = mod.default_companion("Luna", "cat", "Odin")
        assert c["name"] == "Luna"
        assert c["species"] == "cat"
        assert c["owner"] == "Odin"
        assert c["happiness"] == 80
        assert c["level"] == 1
        assert c["streak_days"] == 0

    def test_single_happiness_bar(self):
        """Valkyrie approved: 3 bars → single happiness."""
        mod = _load_module("companion", "sim.py")
        c = mod.default_companion("Test", "cat")
        assert "happiness" in c
        assert "hunger" not in c
        assert "mood" not in c
        assert "energy" not in c

    def test_all_species(self):
        mod = _load_module("companion", "sim.py")
        assert len(mod.SPECIES) == 6

    def test_food_items(self):
        mod = _load_module("companion", "sim.py")
        assert len(mod.FOOD_ITEMS) == 4
        assert "fish" in mod.FOOD_ITEMS
        assert "happiness" in mod.FOOD_ITEMS["fish"]

    def test_feed(self):
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("Test", "dog")
        state["happiness"] = 50
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._state_file
            mod._state_file = lambda: Path(tmpdir) / "state.json"
            result = mod.feed(state, "fish")
            assert result["ok"]
            assert state["happiness"] == 65  # 50 + 15
            mod._state_file = orig

    def test_feed_unknown_food(self):
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("Test", "cat")
        result = mod.feed(state, "pizza")
        assert not result.get("ok")

    def test_feed_includes_owner_name(self):
        """Valkyrie: pet says user's name."""
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("Luna", "cat", "Odin")
        state["happiness"] = 50
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._state_file
            mod._state_file = lambda: Path(tmpdir) / "state.json"
            result = mod.feed(state, "fish")
            assert "Odin" in result["message"]
            mod._state_file = orig

    def test_walk_events_per_species(self):
        mod = _load_module("companion", "sim.py")
        for species in mod.SPECIES:
            events = mod.WALK_EVENTS.get(species, [])
            assert len(events) == 5, f"{species} should have 5 walk events"

    def test_walk(self):
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("Rex", "dog")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._state_file
            mod._state_file = lambda: Path(tmpdir) / "state.json"
            result = mod.walk(state)
            assert result["ok"]
            assert "event" in result
            assert result["xp_gained"] > 0
            mod._state_file = orig

    def test_wandered_off_blocks_walk(self):
        """Valkyrie: at 0 happiness, pet wanders off."""
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("Sleepy", "owl")
        state["wandered_off"] = True
        result = mod.walk(state)
        assert not result.get("ok")
        assert "wandered" in result["error"].lower()

    def test_feeding_brings_back_wanderer(self):
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("Lost", "cat")
        state["wandered_off"] = True
        state["happiness"] = 0
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._state_file
            mod._state_file = lambda: Path(tmpdir) / "state.json"
            result = mod.feed(state, "cake")
            assert result["ok"]
            assert not state["wandered_off"]
            mod._state_file = orig

    def test_xp_leveling(self):
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("XPTest", "fox")
        state["xp"] = 19
        leveled = mod._add_xp(state, 5)
        assert leveled
        assert state["level"] == 2

    def test_mood_prefix(self):
        mod = _load_module("companion", "sim.py")
        state = {"species": "cat", "happiness": 90}
        prefix = mod.get_mood_prefix(state)
        assert "purr" in prefix.lower()
        state = {"species": "dog", "happiness": 10}
        prefix = mod.get_mood_prefix(state)
        assert "whimper" in prefix.lower()

    def test_total_walk_events_30(self):
        mod = _load_module("companion", "sim.py")
        total = sum(len(events) for events in mod.WALK_EVENTS.values())
        assert total == 30

    def test_slow_decay_rate(self):
        """Valkyrie: ~1% per 12 min, not 60s."""
        mod = _load_module("companion", "sim.py")
        # 1/12 ≈ 0.083 per minute
        assert mod.DECAY_PER_MINUTE < 0.1
        assert mod.DECAY_PER_MINUTE > 0.05

    def test_status_message_miss(self):
        """Valkyrie: below 30% → 'misses you'."""
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("Buddy", "dog", "Odin")
        state["happiness"] = 20
        status = mod.get_status(state)
        assert "misses" in status["status_message"].lower()

    def test_streak_tracking(self):
        mod = _load_module("companion", "sim.py")
        state = mod.default_companion("Streak", "fox")
        state = mod._check_streak(state)
        assert state["streak_days"] == 1
        assert state["last_check_in"] is not None


# ---------------------------------------------------------------------------
# Task Queue
# ---------------------------------------------------------------------------

class TestTaskQueue:
    def test_task_types(self):
        mod = _load_module("companion", "queue.py")
        assert len(mod.TASK_TYPES) == 6

    def test_add_task(self):
        mod = _load_module("companion", "queue.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._queue_file
            mod._queue_file = lambda: Path(tmpdir) / "queue.json"
            result = mod.add_task("draft_text", {"to": "Mom"})
            assert result["ok"]
            assert result["task"]["type"] == "draft_text"
            assert result["task"]["status"] == "pending"
            mod._queue_file = orig

    def test_add_unknown_task(self):
        mod = _load_module("companion", "queue.py")
        result = mod.add_task("fly_to_moon")
        assert not result.get("ok")

    def test_complete_task(self):
        mod = _load_module("companion", "queue.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._queue_file
            mod._queue_file = lambda: Path(tmpdir) / "queue.json"
            added = mod.add_task("quick_math", {"expr": "2+2"})
            result = mod.complete_task(added["task"]["id"], "4")
            assert result["ok"]
            assert result["task"]["status"] == "completed"
            mod._queue_file = orig

    def test_queue_stats(self):
        mod = _load_module("companion", "queue.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._queue_file
            mod._queue_file = lambda: Path(tmpdir) / "queue.json"
            mod.add_task("weather")
            mod.add_task("quick_math")
            stats = mod.get_stats()
            assert stats["total"] == 2
            assert stats["pending"] == 2
            mod._queue_file = orig

    def test_filter_by_status(self):
        mod = _load_module("companion", "queue.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._queue_file
            mod._queue_file = lambda: Path(tmpdir) / "queue.json"
            t1 = mod.add_task("weather")
            mod.add_task("quick_math")
            mod.complete_task(t1["task"]["id"], "sunny")
            pending = mod.get_queue("pending")
            assert len(pending) == 1
            mod._queue_file = orig


# ---------------------------------------------------------------------------
# Plugin Structure
# ---------------------------------------------------------------------------

class TestPluginStructure:
    def test_companion_manifest(self):
        assert (REPO_ROOT / "plugins" / "companion" / "plugin.yaml").exists()

    def test_companion_sim(self):
        assert (REPO_ROOT / "plugins" / "companion" / "sim.py").exists()

    def test_companion_queue(self):
        assert (REPO_ROOT / "plugins" / "companion" / "queue.py").exists()

    def test_companion_handler(self):
        assert (REPO_ROOT / "plugins" / "companion" / "handler.py").exists()

    def test_total_plugins_26(self):
        plugins_dir = REPO_ROOT / "plugins"
        dirs = [d for d in plugins_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")]
        assert len(dirs) >= 26, f"Expected ≥26, found {len(dirs)}"

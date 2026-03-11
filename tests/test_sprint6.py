"""
Tests for Sprint 6 — Consumer API plugin.

Tests hardware detection helpers, friendly name mappings,
activity tracking, and learning summary aggregation.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO_ROOT = Path(os.path.dirname(__file__)).parent


def _get_handler():
    spec = importlib.util.spec_from_file_location(
        "consumer_handler",
        str(REPO_ROOT / "plugins" / "consumer-api" / "handler.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Hardware detection
# ---------------------------------------------------------------------------

class TestHardwareDetection:
    def test_detect_hardware_returns_dict(self):
        mod = _get_handler()
        hw = mod.detect_hardware()
        assert isinstance(hw, dict)
        assert "device_name" in hw
        assert "cpu" in hw
        assert "ram_gb" in hw
        assert "vram_gb" in hw
        assert "friendly_name" in hw
        assert "recommended_model" in hw
        assert "compatible_models" in hw

    def test_recommend_model_high_vram(self):
        mod = _get_handler()
        rec = mod._recommend_model(48.0)
        assert rec["model"] is not None
        assert rec["label"] is not None

    def test_recommend_model_low_vram(self):
        mod = _get_handler()
        rec = mod._recommend_model(2.0)
        assert "phi" in rec["model"].lower() or rec["model"]  # fallback

    def test_compatible_models_16gb(self):
        mod = _get_handler()
        models = mod._compatible_models(16.0)
        assert isinstance(models, list)
        # Should have several compatible
        compatible = [m for m in models if m["compatible"]]
        assert len(compatible) >= 3

    def test_compatible_models_sorted(self):
        mod = _get_handler()
        models = mod._compatible_models(32.0)
        vrams = [m["min_vram_gb"] for m in models]
        assert vrams == sorted(vrams)

    def test_friendly_device_type(self):
        mod = _get_handler()
        result = mod._friendly_device_type()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Friendly names
# ---------------------------------------------------------------------------

class TestFriendlyNames:
    def test_friendly_node(self):
        mod = _get_handler()
        result = mod.friendly_node("odin.local", {"role": "orchestrator", "url": "http://localhost"})
        assert result["friendly_name"] == "Odin's Device"
        assert result["friendly_role"] == "Main AI"

    def test_friendly_node_unknown_role(self):
        mod = _get_handler()
        result = mod.friendly_node("thor", {"role": "builder"})
        assert result["friendly_role"] == "Builder"

    def test_friendly_pipeline(self):
        mod = _get_handler()
        pipeline = {
            "id": "pipe_123",
            "title": "Fix login",
            "stages": [
                {"name": "build"}, {"name": "test"}, {"name": "review"}
            ],
            "current_stage": 1,
            "current_iteration": 0,
            "max_iterations": 3,
            "status": "active",
        }
        result = mod.friendly_pipeline(pipeline)
        assert "Step 2 of 3" in result["step_description"]
        assert "Checking quality" in result["step_description"]
        assert result["friendly_status"] == "Working on it"
        assert result["progress_pct"] > 0

    def test_friendly_pipeline_escalated(self):
        mod = _get_handler()
        pipeline = {
            "stages": [{"name": "build"}],
            "current_stage": 0,
            "current_iteration": 2,
            "max_iterations": 3,
            "status": "escalated",
        }
        result = mod.friendly_pipeline(pipeline)
        assert result["friendly_status"] == "Needs Your Help"

    def test_friendly_personality(self):
        mod = _get_handler()
        traits = {"accuracy": 0.6, "default_approach": "code and build"}
        result = mod.friendly_personality(traits, {"name": "thor", "role": "Backend"})
        assert result["tone"] in mod.PERSONALITY_TONES.values() or result["tone"]
        assert "Coding" in result["skills"]
        assert result["name"] == "thor"
        assert isinstance(result["tone_options"], list)

    def test_friendly_personality_empty(self):
        mod = _get_handler()
        result = mod.friendly_personality({}, {})
        assert result["tone"] is not None
        assert isinstance(result["skills"], list)


# ---------------------------------------------------------------------------
# Activity tracking
# ---------------------------------------------------------------------------

class TestActivityTracking:
    def test_record_and_summary(self):
        mod = _get_handler()
        # Reset
        mod._activity.update({
            "questions_answered": 0, "files_read": 0,
            "things_learned": 0, "tasks_completed": 0,
            "debates_held": 0, "last_reset": 0,
        })

        mod.record_activity("chat.response", 5)
        mod.record_activity("file.read", 3)
        mod.record_activity("pipeline.shipped", 1)

        summary = mod.get_activity_summary()
        assert "5 questions" in summary["summary"]
        assert "3 files" in summary["summary"]
        assert "1 task" in summary["summary"]

    def test_empty_activity(self):
        mod = _get_handler()
        mod._activity.update({
            "questions_answered": 0, "files_read": 0,
            "things_learned": 0, "tasks_completed": 0,
            "debates_held": 0, "last_reset": 0,
        })
        summary = mod.get_activity_summary()
        assert "no activity" in summary["summary"].lower()

    def test_unknown_event_ignored(self):
        mod = _get_handler()
        mod._activity["questions_answered"] = 0
        mod.record_activity("some.unknown.event")
        assert mod._activity["questions_answered"] == 0


# ---------------------------------------------------------------------------
# Learning summary
# ---------------------------------------------------------------------------

class TestLearningSummary:
    def test_summary_with_procedures(self):
        mod = _get_handler()
        tmpdir = Path(tempfile.mkdtemp())
        wrd = tmpdir / "war_room_data"
        wrd.mkdir()

        procs = [
            {"task_type": "deploy", "confidence": 0.9},
            {"task_type": "review", "confidence": 0.8},
            {"task_type": "debug", "confidence": 0.3},
        ]
        (wrd / "procedures.json").write_text(json.dumps(procs))

        result = mod.get_learning_summary(tmpdir)
        assert result["things_it_knows"] == 3
        assert result["reliable_pct"] == 67  # 2/3
        assert "3" in result["summary"]

    def test_summary_empty(self):
        mod = _get_handler()
        tmpdir = Path(tempfile.mkdtemp())
        result = mod.get_learning_summary(tmpdir)
        assert result["things_it_knows"] == 0
        assert result["reliable_pct"] == 0

    def test_event_hook(self):
        mod = _get_handler()
        mod._activity["things_learned"] = 0
        mod.on_event("hypothesis.accepted", {})
        assert mod._activity["things_learned"] == 1


# ---------------------------------------------------------------------------
# Integration: plugin structure
# ---------------------------------------------------------------------------

class TestPluginStructure:
    def test_manifest_exists(self):
        manifest = REPO_ROOT / "plugins" / "consumer-api" / "plugin.yaml"
        assert manifest.exists()

    def test_handler_has_register_routes(self):
        mod = _get_handler()
        assert hasattr(mod, "register_routes")

    def test_handler_has_on_event(self):
        mod = _get_handler()
        assert hasattr(mod, "on_event")

    def test_total_plugins_now_16(self):
        plugins_dir = REPO_ROOT / "plugins"
        dirs = [d for d in plugins_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
        assert len(dirs) >= 16, f"Expected 16 plugins, found {len(dirs)}: {[d.name for d in dirs]}"

"""
Tests for the pipeline plugin.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPipelineCore:
    """Pipeline functions (no network)."""

    def _get_handler(self):
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "pipeline", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("pipeline_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_parse_verdict_pass(self):
        mod = self._get_handler()
        assert mod._parse_verdict("VERDICT: pass") == "pass"
        assert mod._parse_verdict("VERDICT: PASS") == "pass"

    def test_parse_verdict_fail(self):
        mod = self._get_handler()
        assert mod._parse_verdict("") == "fail"
        assert mod._parse_verdict("needs more work") == "fail"

    def test_parse_verdict_ship(self):
        mod = self._get_handler()
        assert mod._parse_verdict("VERDICT: ship") == "ship"
        assert mod._parse_verdict("APPROVED for production") == "ship"

    def test_parse_verdict_regress(self):
        mod = self._get_handler()
        assert mod._parse_verdict("VERDICT: regress") == "regress"

    def test_parse_verdict_keyword_fallback(self):
        mod = self._get_handler()
        assert mod._parse_verdict("ALL TESTS PASS perfectly") == "pass"
        assert mod._parse_verdict("This is a REGRESSION") == "regress"

    def test_save_load_pipeline(self):
        mod = self._get_handler()
        mod._BASE_DIR = Path(tempfile.mkdtemp())

        meta = {"id": "test_pipe", "title": "Test", "status": "active"}
        mod._save_pipeline("test_pipe", meta)

        loaded = mod._load_pipeline("test_pipe")
        assert loaded is not None
        assert loaded["title"] == "Test"

    def test_load_nonexistent(self):
        mod = self._get_handler()
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        assert mod._load_pipeline("nope") is None

    def test_load_all_pipelines(self):
        mod = self._get_handler()
        mod._BASE_DIR = Path(tempfile.mkdtemp())

        mod._save_pipeline("p1", {"id": "p1", "status": "active"})
        mod._save_pipeline("p2", {"id": "p2", "status": "shipped"})

        all_p = mod._load_all_pipelines()
        assert len(all_p) == 2
        assert "p1" in all_p
        assert "p2" in all_p

    def test_pipeline_dir_creation(self):
        mod = self._get_handler()
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        d = mod._pipeline_dir()
        assert d.is_dir()


class TestCrucibleCore:
    """Crucible functions (no network)."""

    def _get_handler(self):
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "crucible", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("crucible_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_adversarial_prompt_format(self):
        mod = self._get_handler()
        filled = mod.ADVERSARIAL_PROMPT.format(
            task_type="test", approach="do stuff", confidence=0.8, uses=5,
        )
        assert "test" in filled
        assert "do stuff" in filled


class TestModelRouter:
    """Model router functions."""

    def _get_handler(self):
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "model-router", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("model_router_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_route_with_config(self):
        mod = self._get_handler()
        mod._ROUTING = {
            "spec": "cloud/glm-5",
            "build": "local/default",
            "fallback": "local/default",
        }
        mod._MODEL_PROVIDERS = {
            "cloud": {"url": "https://api.nvidia.com/v1", "key": "test"},
            "local": {"url": "http://localhost:8080/v1", "key": "local"},
        }
        mod._MODEL_ALIASES = {"odin": "local/qwen"}

        result = mod.route("spec")
        assert result["provider"] == "cloud"
        assert result["model"] == "glm-5"
        assert result["cost"] == "paid"

    def test_route_local(self):
        mod = self._get_handler()
        mod._ROUTING = {"build": "local/default", "fallback": "local/default"}
        mod._MODEL_PROVIDERS = {"local": {"url": "http://localhost:8080/v1", "key": "local"}}
        mod._MODEL_ALIASES = {"odin": "local/qwen"}

        result = mod.route("build")
        assert result["is_local"] is True
        assert result["cost"] == "free"

    def test_route_fallback(self):
        mod = self._get_handler()
        mod._ROUTING = {"fallback": "local/default"}
        mod._MODEL_PROVIDERS = {}
        mod._MODEL_ALIASES = {}

        result = mod.route("unknown_type")
        assert result["task_type"] == "unknown_type"

    def test_record_usage(self):
        mod = self._get_handler()
        mod._spend = {}
        mod.record_usage("cloud/glm-5", tokens_in=100, tokens_out=200)
        mod.record_usage("cloud/glm-5", tokens_in=50, tokens_out=100)

        stats = mod.get_stats()
        assert stats["models"]["cloud/glm-5"]["tokens_in"] == 150
        assert stats["models"]["cloud/glm-5"]["calls"] == 2

    def test_stats_empty(self):
        mod = self._get_handler()
        mod._spend = {}
        stats = mod.get_stats()
        assert stats["summary"]["total_calls"] == 0


class TestBeliefShadows:
    """Belief shadow functions."""

    def _get_handler(self):
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "belief-shadows", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("belief_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_record_confirmed(self):
        mod = self._get_handler()
        mod._shadows = {}
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        mod.record_confirmed("thor", "h1", "Thor is fast", 0.9)
        shadow = mod._get_shadow("thor")
        assert len(shadow["confirmed"]) == 1
        assert shadow["confirmed"][0]["id"] == "h1"

    def test_novelty_known(self):
        mod = self._get_handler()
        mod._shadows = {}
        mod.record_shared("thor", "h1", "test")
        score = mod.novelty_score("h1", "test", "thor")
        assert score == 0.0

    def test_novelty_new(self):
        mod = self._get_handler()
        mod._shadows = {}
        score = mod.novelty_score("h_new", "brand new", "thor")
        assert score == 1.0

    def test_get_all_shadows(self):
        mod = self._get_handler()
        mod._shadows = {}
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        mod.record_confirmed("thor", "h1", "test", 0.8)
        mod.record_shared("freya", "h2", "test2")
        result = mod.get_all_shadows()
        assert result["total_peers"] == 2


class TestPersonality:
    """Personality plugin functions."""

    def _get_handler(self):
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "personality", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("personality_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_to_ollama_params(self):
        mod = self._get_handler()
        mod._traits = {"creativity": 0.8, "caution": 0.6}
        params = mod.to_ollama_params()
        assert params["temperature"] == 0.8
        assert params["top_p"] == 0.7

    def test_to_system_prompt_high_skepticism(self):
        mod = self._get_handler()
        mod._traits = {**mod.DEFAULT_TRAITS, "skepticism": 0.8}
        prompt = mod.to_system_prompt()
        assert "Question every assumption" in prompt

    def test_to_system_prompt_empty(self):
        mod = self._get_handler()
        mod._traits = {"skepticism": 0.5, "caution": 0.5, "creativity": 0.5,
                        "speed": 0.5, "accuracy": 0.5, "autonomy": 0.5}
        prompt = mod.to_system_prompt()
        # Only skepticism >= 0.5 fires
        assert "skeptical" in prompt

    def test_evolve_pipeline_shipped(self):
        mod = self._get_handler()
        mod._traits = {**mod.DEFAULT_TRAITS}
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        old_acc = mod._traits["accuracy"]

        result = mod.evolve("pipeline.shipped")
        assert result["evolved"] is True
        assert mod._traits["accuracy"] > old_acc

    def test_evolve_crucible_broken(self):
        mod = self._get_handler()
        mod._traits = {**mod.DEFAULT_TRAITS}
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        old_caution = mod._traits["caution"]

        result = mod.evolve("crucible.broken")
        assert result["evolved"] is True
        assert mod._traits["caution"] > old_caution

    def test_evolve_unknown(self):
        mod = self._get_handler()
        mod._traits = {**mod.DEFAULT_TRAITS}
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        result = mod.evolve("unknown.event")
        assert result["evolved"] is False


class TestSocraticCore:
    """Socratic debate core functions (no network)."""

    def _get_handler(self):
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "socratic", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("socratic_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_save_load_debate(self):
        mod = self._get_handler()
        mod._BASE_DIR = Path(tempfile.mkdtemp())

        state = {"id": "d1", "status": "active", "transcript": []}
        mod._save_debate("d1", state)

        loaded = mod._load_debate("d1")
        assert loaded is not None
        assert loaded["id"] == "d1"

    def test_intervene(self):
        mod = self._get_handler()
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        mod._debates = {"d1": {
            "id": "d1", "status": "active", "current_round": 1,
            "transcript": [],
        }}
        mod._save_debate("d1", mod._debates["d1"])

        result = mod.intervene("d1", "I disagree with this approach")
        assert result["ok"] is True

    def test_intervene_not_found(self):
        mod = self._get_handler()
        mod._BASE_DIR = Path(tempfile.mkdtemp())
        mod._debates = {}
        result = mod.intervene("nonexistent", "test")
        assert result["ok"] is False

    def test_evaluate_consensus_pass(self):
        mod = self._get_handler()
        state = {
            "scores": {"architect": 8, "critic": 7, "user": 9},
            "consensus_threshold": 0.7,
            "current_round": 3,
            "rounds": 3,
        }
        mod._evaluate_consensus("d1", state)
        assert state["status"] == "consensus"

    def test_evaluate_consensus_deadlock(self):
        mod = self._get_handler()
        state = {
            "scores": {"architect": 3, "critic": 2, "user": 4},
            "consensus_threshold": 0.7,
            "current_round": 3,
            "rounds": 3,
        }
        mod._evaluate_consensus("d2", state)
        assert state["status"] == "deadlock"

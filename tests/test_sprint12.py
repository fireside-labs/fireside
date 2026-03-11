"""
Tests for Sprint 12 — Adaptive Thinking + Task Persistence + Context Compaction.
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
# Adaptive Thinking
# ---------------------------------------------------------------------------

class TestAdaptiveThinking:
    def test_simple_question(self):
        mod = _load_module("adaptive-thinking")
        result = mod.classify_question("What is Python?")
        assert result["system"] == 1
        assert result["config"]["max_tokens"] == 256

    def test_complex_question(self):
        mod = _load_module("adaptive-thinking")
        result = mod.classify_question(
            "Can you compare and contrast the architecture of "
            "microservices vs monolith, step by step, with trade-offs?"
        )
        assert result["system"] == 2
        assert result["config"]["max_tokens"] == 2048

    def test_greeting_is_simple(self):
        mod = _load_module("adaptive-thinking")
        result = mod.classify_question("Hello!")
        assert result["system"] == 1

    def test_code_is_complex(self):
        mod = _load_module("adaptive-thinking")
        result = mod.classify_question("```python\ndef foo():\n    pass\n```")
        assert result["system"] == 2

    def test_yes_no_is_simple(self):
        mod = _load_module("adaptive-thinking")
        result = mod.classify_question("Is Python a programming language?")
        assert result["system"] == 1

    def test_score_range(self):
        mod = _load_module("adaptive-thinking")
        result = mod.classify_question("test")
        assert 0.0 <= result["score"] <= 1.0


# ---------------------------------------------------------------------------
# Task Persistence
# ---------------------------------------------------------------------------

class TestTaskPersistence:
    def test_create_task(self):
        mod = _load_module("task-persistence")
        with tempfile.TemporaryDirectory() as tmpdir:
            mod._TASKS_DIR = Path(tmpdir)
            task = mod.create_task("Test task", "desc", "thor", 5)
            assert task["status"] == "in_progress"
            assert task["total_steps"] == 5
            assert task["current_step"] == 0

    def test_checkpoint(self):
        mod = _load_module("task-persistence")
        with tempfile.TemporaryDirectory() as tmpdir:
            mod._TASKS_DIR = Path(tmpdir)
            task = mod.create_task("CP test", "", "thor", 3)
            result = mod.checkpoint(task["id"], 1, {"data": "hello"})
            assert result["ok"]
            # Verify persistence
            loaded = mod.load_task(task["id"])
            assert loaded["current_step"] == 1
            assert len(loaded["checkpoints"]) == 1

    def test_complete_task(self):
        mod = _load_module("task-persistence")
        with tempfile.TemporaryDirectory() as tmpdir:
            mod._TASKS_DIR = Path(tmpdir)
            task = mod.create_task("Done test", "", "thor", 1)
            result = mod.complete_task(task["id"])
            assert result["ok"]
            loaded = mod.load_task(task["id"])
            assert loaded["status"] == "completed"

    def test_scan_interrupted(self):
        mod = _load_module("task-persistence")
        with tempfile.TemporaryDirectory() as tmpdir:
            mod._TASKS_DIR = Path(tmpdir)
            mod.create_task("Task A", "", "thor", 3)
            mod.create_task("Task B", "", "thor", 2)
            interrupted = mod.scan_interrupted()
            assert len(interrupted) == 2

    def test_resume_task(self):
        mod = _load_module("task-persistence")
        with tempfile.TemporaryDirectory() as tmpdir:
            mod._TASKS_DIR = Path(tmpdir)
            task = mod.create_task("Resume test", "", "thor", 5)
            mod.checkpoint(task["id"], 3, {})
            result = mod.resume_task(task["id"])
            assert result["ok"]
            assert result["resume_from_step"] == 3

    def test_nonexistent_task(self):
        mod = _load_module("task-persistence")
        with tempfile.TemporaryDirectory() as tmpdir:
            mod._TASKS_DIR = Path(tmpdir)
            result = mod.checkpoint("nonexistent", 1)
            assert not result["ok"]


# ---------------------------------------------------------------------------
# Context Compactor
# ---------------------------------------------------------------------------

class TestContextCompactor:
    def test_no_compaction_needed(self):
        mod = _load_module("context-compactor")
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = mod.compact(messages, context_window=8192)
        assert not result["compacted"]

    def test_compaction_triggered(self):
        mod = _load_module("context-compactor")
        # Create enough messages to exceed 75% of a small window
        messages = [{"role": "system", "content": "System prompt."}]
        for i in range(30):
            messages.append({"role": "user", "content": f"This is message number {i} with enough content to use tokens."})
            messages.append({"role": "assistant", "content": f"Response to message {i}. Here is some longer content to fill the context."})

        result = mod.compact(messages, context_window=200, keep_recent=4)
        assert result["compacted"]
        assert result["stats"]["messages_compressed"] > 0
        assert result["stats"]["savings_pct"] > 0

    def test_keeps_recent_messages(self):
        mod = _load_module("context-compactor")
        messages = [{"role": "system", "content": "System."}]
        for i in range(20):
            messages.append({"role": "user", "content": f"Message {i} " * 20})
            messages.append({"role": "assistant", "content": f"Reply {i} " * 20})

        result = mod.compact(messages, context_window=300, keep_recent=4)
        if result["compacted"]:
            assert result["stats"]["messages_kept"] == 4

    def test_token_estimation(self):
        mod = _load_module("context-compactor")
        # ~4 chars per token
        assert mod.estimate_tokens("hello world") >= 2
        assert mod.estimate_tokens("a" * 100) == 25

    def test_summarize_messages(self):
        mod = _load_module("context-compactor")
        messages = [
            {"role": "user", "content": "How do I install Python on Mac?"},
            {"role": "assistant", "content": "You can install Python using Homebrew. Run brew install python3."},
        ]
        summary = mod.summarize_messages(messages)
        assert "User" in summary
        assert "AI" in summary


# ---------------------------------------------------------------------------
# Plugin Structure
# ---------------------------------------------------------------------------

class TestPluginStructure:
    def test_adaptive_thinking_manifest(self):
        assert (REPO_ROOT / "plugins" / "adaptive-thinking" / "plugin.yaml").exists()

    def test_task_persistence_manifest(self):
        assert (REPO_ROOT / "plugins" / "task-persistence" / "plugin.yaml").exists()

    def test_context_compactor_manifest(self):
        assert (REPO_ROOT / "plugins" / "context-compactor" / "plugin.yaml").exists()

    def test_total_plugins_now_25(self):
        plugins_dir = REPO_ROOT / "plugins"
        dirs = [d for d in plugins_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")]
        assert len(dirs) >= 25, f"Expected 25, found {len(dirs)}: {[d.name for d in dirs]}"

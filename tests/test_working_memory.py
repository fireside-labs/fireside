"""
Tests for the working-memory plugin.
"""
from __future__ import annotations

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestWorkingMemory:
    """WorkingMemory class unit tests."""

    def _get_wm_class(self):
        """Import WorkingMemory class from plugin handler."""
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "working-memory", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("wm_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.WorkingMemory

    def test_observe_and_recall(self):
        """Test basic observe/recall cycle."""
        WM = self._get_wm_class()
        wm = WM(max_items=5)

        wm.observe("The sky is blue", importance=0.8, source="test")
        results = wm.recall(top_k=5)

        assert len(results) == 1
        assert results[0]["content"] == "The sky is blue"
        assert results[0]["importance"] == 0.8

    def test_lru_eviction(self):
        """Test that oldest items are evicted when max_items is reached."""
        WM = self._get_wm_class()
        wm = WM(max_items=3)

        wm.observe("item 1")
        wm.observe("item 2")
        wm.observe("item 3")
        wm.observe("item 4")  # should evict item 1

        results = wm.recall(top_k=10)
        contents = [r["content"] for r in results]

        assert "item 1" not in contents
        assert len(results) == 3

    def test_recall_with_query(self):
        """Test keyword-based recall filtering."""
        WM = self._get_wm_class()
        wm = WM(max_items=10)

        wm.observe("Python is a programming language", source="wiki")
        wm.observe("The weather is sunny today", source="chat")
        wm.observe("Python framework Flask is popular", source="wiki")

        results = wm.recall(query="Python", top_k=5)
        assert len(results) == 2
        assert all("python" in r["content"].lower() for r in results)

    def test_observe_refresh(self):
        """Test that re-observing the same content refreshes it."""
        WM = self._get_wm_class()
        wm = WM(max_items=5)

        wm.observe("hello world")
        time.sleep(0.01)
        wm.observe("hello world")  # should refresh, not add duplicate

        status = wm.status()
        assert status["items"] == 1

    def test_as_prompt_context(self):
        """Test prompt context formatting."""
        WM = self._get_wm_class()
        wm = WM(max_items=5)

        wm.observe("Memory item A", importance=0.9, source="test")
        wm.observe("Memory item B", importance=0.7, source="api")

        ctx = wm.as_prompt_context(max_tokens=2000)

        assert "[WORKING MEMORY" in ctx
        assert "Memory item A" in ctx
        assert "[END WORKING MEMORY]" in ctx

    def test_prompt_context_empty(self):
        """Test prompt context returns empty string when no items."""
        WM = self._get_wm_class()
        wm = WM(max_items=5)

        ctx = wm.as_prompt_context()
        assert ctx == ""

    def test_status_fields(self):
        """Test status dict has all expected fields."""
        WM = self._get_wm_class()
        wm = WM(max_items=5)

        wm.observe("test item")
        status = wm.status()

        assert "items" in status
        assert "capacity" in status
        assert "hits" in status
        assert "misses" in status
        assert "hit_rate" in status
        assert "contents" in status
        assert status["items"] == 1
        assert status["capacity"] == 5

    def test_clear(self):
        """Test clearing working memory."""
        WM = self._get_wm_class()
        wm = WM(max_items=5)

        wm.observe("item 1")
        wm.observe("item 2")
        wm.clear()

        assert wm.status()["items"] == 0

    def test_hits_and_misses(self):
        """Test hit/miss tracking."""
        WM = self._get_wm_class()
        wm = WM(max_items=5)

        wm.observe("Python code")

        wm.recall(query="Python")  # hit
        wm.recall(query="nonexistent")  # miss

        status = wm.status()
        assert status["hits"] >= 1
        assert status["misses"] >= 1

    def test_estimate_tokens(self):
        """Test token estimation."""
        WM = self._get_wm_class()
        tokens = WM.estimate_tokens("hello world")  # 11 chars → ~2-3 tokens
        assert tokens >= 1
        assert tokens < 10

        assert WM.estimate_tokens("") == 0

"""
Tests for the predictions plugin — predictive processing engine.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPredictionsHelpers:
    """Test helper functions that don't require Ollama."""

    def _get_handler(self):
        """Import predictions handler module."""
        import importlib.util
        handler_path = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "predictions", "handler.py"
        )
        spec = importlib.util.spec_from_file_location("pred_handler", handler_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_cosine_sim_identical(self):
        """Identical vectors should have similarity 1.0."""
        mod = self._get_handler()
        vec = [1.0, 2.0, 3.0]
        assert abs(mod._cosine_sim(vec, vec) - 1.0) < 0.001

    def test_cosine_sim_orthogonal(self):
        """Orthogonal vectors should have similarity 0.0."""
        mod = self._get_handler()
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(mod._cosine_sim(a, b)) < 0.001

    def test_cosine_sim_opposite(self):
        """Opposite vectors should have similarity -1.0."""
        mod = self._get_handler()
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(mod._cosine_sim(a, b) - (-1.0)) < 0.001

    def test_cosine_sim_zero_vector(self):
        """Zero vector should return 0.0."""
        mod = self._get_handler()
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert mod._cosine_sim(a, b) == 0.0

    def test_synthesize_expected_code(self):
        """Test topic matching for code-related queries."""
        mod = self._get_handler()
        result = mod._synthesize_expected("How do I fix this Python bug?")
        assert "implementation" in result.lower() or "function" in result.lower()

    def test_synthesize_expected_memory(self):
        """Test topic matching for memory-related queries."""
        mod = self._get_handler()
        result = mod._synthesize_expected("Do you remember what I said earlier?")
        assert "earlier" in result.lower() or "conversation" in result.lower() or "recall" in result.lower()

    def test_synthesize_expected_general(self):
        """Test fallback for general queries."""
        mod = self._get_handler()
        result = mod._synthesize_expected("What is the meaning of life?")
        assert len(result) > 20  # should return something meaningful

    def test_get_stats_empty(self):
        """Test stats when no predictions have been scored."""
        mod = self._get_handler()
        stats = mod.get_stats()
        assert stats["total"] == 0
        assert stats["avg_error"] == 0.0
        assert stats["recent"] == []

    def test_predict_returns_none_without_ollama(self):
        """Predict returns None when Ollama is not available."""
        mod = self._get_handler()
        # With a broken endpoint, predict should return None gracefully
        old_endpoint = mod._EMBED_ENDPOINT
        mod._EMBED_ENDPOINT = "http://127.0.0.1:99999"  # broken

        result = mod.predict("test query")

        mod._EMBED_ENDPOINT = old_endpoint  # restore
        assert result is None

    def test_score_returns_none_for_unknown_hash(self):
        """Scoring an unknown query hash should return None."""
        mod = self._get_handler()
        result = mod.score("nonexistent_hash", "some response")
        assert result is None

    def test_score_returns_none_for_none_hash(self):
        """Scoring None hash should return None."""
        mod = self._get_handler()
        result = mod.score(None, "some response")
        assert result is None

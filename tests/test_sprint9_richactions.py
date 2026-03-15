"""
tests/test_sprint9_richactions.py — Sprint 9 Rich Actions + Cross-Context Search tests.

Validates Thor's 3 tasks:
  1. Rich action response builder (5 action types)
  2. Cross-context search (POST /api/v1/companion/query)
  3. Privacy email update (GET /api/v1/privacy-contact)

Run:  python -m pytest tests/test_sprint9_richactions.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Task 1 — Rich Action Response Builder
# ---------------------------------------------------------------------------

class TestRichActionBuilder(unittest.TestCase):

    def test_build_action_function(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_build_action", src)

    def test_action_type_browse_result(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"browse_result"', src)

    def test_action_type_pipeline_status(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"pipeline_status"', src)

    def test_action_type_pipeline_complete(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"pipeline_complete"', src)

    def test_action_type_memory_recall(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"memory_recall"', src)

    def test_action_type_translation_result(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"translation_result"', src)

    def test_browse_result_fields(self):
        src = _read("plugins/companion/handler.py")
        for field in ["title", "url", "summary", "key_points"]:
            self.assertIn(f'"{field}"', src, f"browse_result missing: {field}")

    def test_pipeline_status_fields(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"percent"', src)
        self.assertIn('"estimated_completion"', src)

    def test_action_includes_timestamp(self):
        src = _read("plugins/companion/handler.py")
        func_start = src.find("def _build_action")
        func_end = src.find("return action", func_start)
        body = src[func_start:func_end]
        self.assertIn("timestamp", body)


# ---------------------------------------------------------------------------
# Task 2 — Cross-Context Search
# ---------------------------------------------------------------------------

class TestCrossContextSearch(unittest.TestCase):

    def test_query_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/query", src)

    def test_post_method(self):
        src = _read("plugins/companion/handler.py")
        idx = src.find("/api/v1/companion/query")
        before = src[max(0, idx - 200):idx]
        self.assertIn(".post(", before)

    def test_min_query_length(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("at least 2 characters", src)

    def test_source_working_memory(self):
        src = _read("plugins/companion/handler.py")
        query_start = src.find("def api_companion_query")
        query_end = src.find("def api_privacy_contact", query_start) if "def api_privacy_contact" in src[query_start:] else len(src)
        body = src[query_start:query_end]
        self.assertIn('"working_memory"', body)

    def test_source_taught_facts(self):
        src = _read("plugins/companion/handler.py")
        query_start = src.find("def api_companion_query")
        body = src[query_start:query_start + 5000]
        self.assertIn('"taught_facts"', body)

    def test_source_chat_history(self):
        src = _read("plugins/companion/handler.py")
        query_start = src.find("def api_companion_query")
        body = src[query_start:query_start + 5000]
        self.assertIn('"chat_history"', body)

    def test_source_hypotheses(self):
        src = _read("plugins/companion/handler.py")
        query_start = src.find("def api_companion_query")
        body = src[query_start:query_start + 5000]
        self.assertIn('"hypotheses"', body)

    def test_capped_at_10(self):
        src = _read("plugins/companion/handler.py")
        query_start = src.find("def api_companion_query")
        body = src[query_start:query_start + 5000]
        self.assertIn("[:10]", body)

    def test_sorted_by_relevance(self):
        src = _read("plugins/companion/handler.py")
        query_start = src.find("def api_companion_query")
        body = src[query_start:query_start + 5000]
        self.assertIn("relevance", body)
        self.assertIn("reverse=True", body)

    def test_result_structure(self):
        src = _read("plugins/companion/handler.py")
        for field in ["source", "content", "relevance", "date"]:
            self.assertIn(f'"{field}"', src)


# ---------------------------------------------------------------------------
# Task 3 — Privacy Email
# ---------------------------------------------------------------------------

class TestPrivacyEmail(unittest.TestCase):

    def test_privacy_contact_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/privacy-contact", src)

    def test_fablefur_email(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("hello@fablefur.com", src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint9Regression(unittest.TestCase):

    def test_waitlist_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/waitlist", src)

    def test_achievements_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/achievements", src)

    def test_ssrf_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_is_url_safe", src)

    def test_websocket_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/ws", src)


if __name__ == "__main__":
    unittest.main()

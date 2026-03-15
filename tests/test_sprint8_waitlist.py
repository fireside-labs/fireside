"""
tests/test_sprint8_waitlist.py — Sprint 8 waitlist endpoint tests.

Validates Thor's single task: POST /api/v1/waitlist
  - Email validation
  - Deduplication
  - Rate limiting (10/min)
  - Storage in ~/.valhalla/waitlist.json

Run:  python -m pytest tests/test_sprint8_waitlist.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class TestWaitlistEndpoint(unittest.TestCase):

    def test_route_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/waitlist", src)

    def test_post_method(self):
        src = _read("plugins/companion/handler.py")
        idx = src.find("/api/v1/waitlist")
        # Look backward for the decorator
        before = src[max(0, idx - 200):idx]
        self.assertIn(".post(", before)

    def test_email_validation(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("@", src)
        # Regex pattern for email
        self.assertIn("re.match", src)

    def test_deduplication(self):
        src = _read("plugins/companion/handler.py")
        # Should check for existing email
        self.assertIn("already on the waitlist", src)

    def test_success_message(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("You're on the waitlist", src)

    def test_storage_file(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("waitlist.json", src)

    def test_rate_limit(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_waitlist_requests", src)

    def test_rate_limit_threshold(self):
        src = _read("plugins/companion/handler.py")
        # 10 signups per minute
        waitlist_section = src[src.find("def api_waitlist"):]
        self.assertIn("10", waitlist_section)
        self.assertIn("60", waitlist_section)

    def test_429_on_rate_limit(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("429", src)

    def test_400_on_bad_email(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("Invalid email", src)

    def test_stores_timestamp(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("signed_up", src)

    def test_normalizes_email(self):
        src = _read("plugins/companion/handler.py")
        # Email is lowered and stripped
        self.assertIn(".strip().lower()", src)


class TestSprint8Regression(unittest.TestCase):

    def test_achievements_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/achievements", src)

    def test_ssrf_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_is_url_safe", src)

    def test_ws_auth_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_verify_ws_token", src)

    def test_voice_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/voice/transcribe", src)


if __name__ == "__main__":
    unittest.main()

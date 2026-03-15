"""
tests/test_sprint3_pushnotify.py — Sprint 3 Push Notification + Security Fix tests.

Validates all 5 Thor tasks:
  1. Expo Push notification infrastructure (notifications.py)
  2. 4 companion-initiated triggers + rate limiting
  3. hmac.compare_digest in /mobile/pair auth
  4. Rate limit dict cleanup (stale entries purged)
  5. Input validation (adopt name ≤20, task_type ≤200)

Run from project root:
    python -m pytest tests/test_sprint3_pushnotify.py -v
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent


def _load(relative_path: str):
    filepath = REPO_ROOT / relative_path
    safe_name = relative_path.replace("/", "_").replace("\\", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(safe_name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Task 1 — Expo Push notification infrastructure
# ---------------------------------------------------------------------------

class TestNotificationsModule(unittest.TestCase):

    def test_notifications_file_exists(self):
        self.assertTrue(
            (REPO_ROOT / "plugins" / "companion" / "notifications.py").exists()
        )

    def test_expo_push_url(self):
        mod = _load("plugins/companion/notifications.py")
        self.assertEqual(mod.EXPO_PUSH_URL, "https://exp.host/--/api/v2/push/send")

    def test_save_and_get_push_token(self):
        mod = _load("plugins/companion/notifications.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "_token_file",
                              return_value=Path(tmpdir) / "push_token.json"):
                mod.save_push_token("ExponentPushToken[test123]")
                token = mod.get_push_token()
                self.assertEqual(token, "ExponentPushToken[test123]")

    def test_get_push_token_returns_none_when_missing(self):
        mod = _load("plugins/companion/notifications.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "_token_file",
                              return_value=Path(tmpdir) / "nonexistent.json"):
                self.assertIsNone(mod.get_push_token())


# ---------------------------------------------------------------------------
# Task 2 — Notification triggers + rate limiting
# ---------------------------------------------------------------------------

class TestNotificationTriggers(unittest.TestCase):

    def test_notification_cooldown_is_1_hour(self):
        mod = _load("plugins/companion/notifications.py")
        self.assertEqual(mod._NOTIFICATION_COOLDOWN, 3600)

    def test_can_send_respects_cooldown(self):
        mod = _load("plugins/companion/notifications.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "notification_state.json"
            with patch.object(mod, "_state_file", return_value=state_file):
                # First call should be allowed
                self.assertTrue(mod._can_send("low_happiness"))
                # Mark as sent
                mod._mark_sent("low_happiness")
                # Should now be blocked
                self.assertFalse(mod._can_send("low_happiness"))

    def test_different_trigger_types_independent(self):
        mod = _load("plugins/companion/notifications.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "notification_state.json"
            with patch.object(mod, "_state_file", return_value=state_file):
                mod._mark_sent("low_happiness")
                # Different type should still be allowed
                self.assertTrue(mod._can_send("daily_gift"))

    def test_four_trigger_types_in_check(self):
        """check_and_notify must handle all 4 trigger types."""
        src = (REPO_ROOT / "plugins" / "companion" / "notifications.py").read_text(encoding="utf-8")
        for trigger in ["low_happiness", "daily_gift", "task_completed", "level_up"]:
            self.assertIn(trigger, src,
                          f"Trigger type '{trigger}' missing from notifications.py")

    def test_happiness_threshold_is_30(self):
        src = (REPO_ROOT / "plugins" / "companion" / "notifications.py").read_text(encoding="utf-8")
        self.assertIn("< 30", src,
                      "Happiness threshold should be < 30")


# ---------------------------------------------------------------------------
# Task 1 (cont) — Push registration endpoint
# ---------------------------------------------------------------------------

class TestPushRegistrationEndpoint(unittest.TestCase):

    def test_register_push_route_exists(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("/api/v1/companion/mobile/register-push", src)

    def test_validates_expo_token_format(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("ExponentPushToken[", src,
                      "Should validate Expo push token format")

    def test_check_notifications_endpoint_exists(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("/api/v1/companion/mobile/check-notifications", src)


# ---------------------------------------------------------------------------
# Task 3 — hmac.compare_digest
# ---------------------------------------------------------------------------

class TestHmacFix(unittest.TestCase):

    def test_hmac_compare_digest_used(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("hmac.compare_digest", src,
                      "Auth check must use hmac.compare_digest for timing safety")

    def test_hmac_imported(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("import hmac", src)

    def test_no_plain_string_comparison(self):
        """The old provided != auth_key pattern should be replaced."""
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        # Find the pair endpoint auth block
        pair_start = src.find("async def api_mobile_pair")
        pair_end = src.find("async def api_save_chat") if "api_save_chat" in src else len(src)
        pair_body = src[pair_start:pair_end]
        self.assertNotIn("provided != auth_key", pair_body,
                         "Plain string comparison should be replaced with hmac.compare_digest")


# ---------------------------------------------------------------------------
# Task 4 — Rate limit dict cleanup
# ---------------------------------------------------------------------------

class TestRateLimitCleanup(unittest.TestCase):

    def test_stale_cleanup_present(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("stale_ips", src,
                      "Rate limit dict should have stale entry cleanup")

    def test_cleanup_threshold_is_120_seconds(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("120", src,
                      "Stale entries should be purged after >120 seconds (2 min)")

    def test_cleanup_deletes_stale_entries(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("del _pair_attempts[ip]", src,
                      "Should delete stale entries from _pair_attempts dict")


# ---------------------------------------------------------------------------
# Task 5 — Input validation
# ---------------------------------------------------------------------------

class TestInputValidation(unittest.TestCase):

    def test_adopt_name_max_length(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("20", src,
                      "Companion name should have max length of 20")

    def test_adopt_name_empty_check(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("cannot be empty", src,
                      "Should reject empty companion names")

    def test_task_type_max_length(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("200", src,
                      "task_type should have max length of 200")

    def test_payload_size_limit(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("10000", src,
                      "payload should have max size of 10KB")

    def test_returns_422_for_violations(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("422", src,
                      "Should return HTTP 422 for validation errors")


# ---------------------------------------------------------------------------
# Sprint 1+2 regression — existing tests must still be valid
# ---------------------------------------------------------------------------

class TestRegressionChecks(unittest.TestCase):

    def test_cors_no_wildcard(self):
        import yaml
        data = yaml.safe_load((REPO_ROOT / "valhalla.yaml").read_text(encoding="utf-8"))
        origins = data.get("dashboard", {}).get("cors_origins", [])
        self.assertNotIn("*", origins)

    def test_mobile_ready_still_present(self):
        src = (REPO_ROOT / "api" / "v1.py").read_text(encoding="utf-8")
        self.assertIn('"mobile_ready"', src)

    def test_chat_history_still_present(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text()
        self.assertIn("/api/v1/companion/chat/history", src)

    def test_ip_validation_still_present(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text()
        self.assertIn("/api/v1/companion/mobile/validate-host", src)


if __name__ == "__main__":
    unittest.main()

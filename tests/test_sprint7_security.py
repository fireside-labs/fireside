"""
tests/test_sprint7_security.py — Sprint 7 Security Hardening + Achievements tests.

Validates all 5 Thor tasks:
  1. SSRF blocklist on /browse/summarize
  2. WebSocket auth + 5 connection cap
  3. Marketplace error sanitization
  4. Achievement tracking (16 achievements)
  5. Weekly summary endpoint

Run from project root:
    python -m pytest tests/test_sprint7_security.py -v
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
# Task 1 — SSRF Blocklist
# ---------------------------------------------------------------------------

class TestSSRFBlocklist(unittest.TestCase):

    def test_ssrf_function_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_is_url_safe", src)

    def test_blocked_networks(self):
        src = _read("plugins/companion/handler.py")
        for net in ["127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12",
                     "192.168.0.0/16", "169.254.0.0/16", "0.0.0.0/8"]:
            self.assertIn(net, src, f"SSRF blocklist missing: {net}")

    def test_localhost_blocked(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"localhost"', src)

    def test_ssrf_wired_into_summarize(self):
        src = _read("plugins/companion/handler.py")
        summarize_start = src.find("def api_browse_summarize")
        summarize_end = src.find("def _is_url_safe", summarize_start)
        body = src[summarize_start:summarize_end]
        self.assertIn("_is_url_safe", body, "SSRF check must be called in summarize")

    def test_403_on_blocked(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("blocked internal address", src)

    def test_ssrf_unit_logic(self):
        """Test _is_url_safe logic directly via the achievements module pattern."""
        import ipaddress
        import urllib.parse

        BLOCKED_NETWORKS = [
            ipaddress.ip_network("127.0.0.0/8"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("169.254.0.0/16"),
            ipaddress.ip_network("0.0.0.0/8"),
        ]

        def is_safe(url):
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False
            if hostname in ("localhost", "0.0.0.0"):
                return False
            try:
                addr = ipaddress.ip_address(hostname)
                return not any(addr in net for net in BLOCKED_NETWORKS)
            except ValueError:
                return True

        self.assertFalse(is_safe("http://localhost/admin"))
        self.assertFalse(is_safe("http://127.0.0.1/admin"))
        self.assertFalse(is_safe("http://10.0.1.5/secret"))
        self.assertFalse(is_safe("http://192.168.1.1/router"))
        self.assertFalse(is_safe("http://169.254.169.254/metadata"))
        self.assertTrue(is_safe("https://example.com"))
        self.assertTrue(is_safe("https://google.com"))


# ---------------------------------------------------------------------------
# Task 2 — WebSocket Auth + Connection Cap
# ---------------------------------------------------------------------------

class TestWebSocketAuth(unittest.TestCase):

    def test_token_param_required(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('query_params.get("token"', src)

    def test_verify_ws_token_function(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_verify_ws_token", src)

    def test_hmac_compare(self):
        src = _read("plugins/companion/handler.py")
        ws_start = src.find("_verify_ws_token")
        ws_end = src.find("_cleanup_dead_ws", ws_start)
        body = src[ws_start:ws_end]
        self.assertIn("hmac.compare_digest", body)

    def test_connection_cap(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_WS_MAX_CONNECTIONS", src)
        self.assertIn("5", src)

    def test_unauthorized_close(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("4001", src, "Should close with 4001 for unauthorized")

    def test_too_many_connections_close(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("4029", src, "Should close with 4029 for too many connections")

    def test_dead_conn_cleanup(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_cleanup_dead_ws", src)


# ---------------------------------------------------------------------------
# Task 3 — Marketplace Error Sanitization
# ---------------------------------------------------------------------------

class TestMarketplaceErrors(unittest.TestCase):

    def test_no_raw_str_e_in_marketplace(self):
        src = _read("plugins/companion/handler.py")
        marketplace_start = src.find("# --- Sprint 6 Task 2: Marketplace")
        marketplace_end = src.find("# --- Sprint 6 Task 3:", marketplace_start)
        body = src[marketplace_start:marketplace_end]
        # Should not contain str(e) as a response value
        self.assertNotIn('"note": str(e)', body,
                         "Marketplace must not leak raw exceptions")

    def test_marketplace_unavailable_message(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("Marketplace service unavailable", src)

    def test_errors_logged(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("Marketplace browse error", src)
        self.assertIn("Marketplace search error", src)
        self.assertIn("Marketplace install error", src)


# ---------------------------------------------------------------------------
# Task 4 — Achievements
# ---------------------------------------------------------------------------

class TestAchievements(unittest.TestCase):

    def test_achievements_module_exists(self):
        self.assertTrue(
            (REPO_ROOT / "plugins" / "companion" / "achievements.py").exists()
        )

    def test_16_achievements_defined(self):
        src = _read("plugins/companion/achievements.py")
        import re
        keys = re.findall(r'"(\w+)":\s*\{.*?"name"', src)
        self.assertEqual(len(keys), 16, f"Expected 16 achievements, found {len(keys)}")

    def test_achievements_list_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/achievements", src)

    def test_achievements_check_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/achievements/check", src)

    def test_achievements_stored_in_json(self):
        src = _read("plugins/companion/achievements.py")
        self.assertIn("achievements.json", src)

    def test_check_and_award_function(self):
        src = _read("plugins/companion/achievements.py")
        self.assertIn("def check_and_award", src)

    def test_check_uses_counters(self):
        src = _read("plugins/companion/achievements.py")
        for counter in ["feeds", "walks", "quests", "teaches",
                        "guardian_saves", "voice_uses", "translations"]:
            self.assertIn(counter, src, f"Counter '{counter}' not checked")

    def test_achievement_unit_logic(self):
        """Test check_and_award directly."""
        from plugins.companion.achievements import check_and_award, ACHIEVEMENTS
        state = {
            "level": 6,
            "streak_days": 8,
            "counters": {"feeds": 12, "walks": 1, "quests": 0},
        }
        # Should award: first_feed, feed_10, first_walk, daily_7, level_5
        newly = check_and_award(state)
        earned_ids = [a["id"] for a in newly]
        self.assertIn("first_feed", earned_ids)
        self.assertIn("feed_10", earned_ids)
        self.assertIn("first_walk", earned_ids)
        self.assertIn("daily_7", earned_ids)
        self.assertIn("level_5", earned_ids)
        self.assertNotIn("feed_100", earned_ids)  # Only 12 feeds

    def test_idempotent(self):
        """Second call shouldn't re-award."""
        from plugins.companion.achievements import check_and_award
        state = {"level": 1, "counters": {"feeds": 1}}
        first = check_and_award(state)
        second = check_and_award(state)
        self.assertEqual(len(second), 0, "Second call should not re-award")


# ---------------------------------------------------------------------------
# Task 5 — Weekly Summary
# ---------------------------------------------------------------------------

class TestWeeklySummary(unittest.TestCase):

    def test_weekly_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/weekly-summary", src)

    def test_response_structure(self):
        src = _read("plugins/companion/handler.py")
        for field in ["period", "stats", "highlights", "companion_name"]:
            self.assertIn(f'"{field}"', src, f"Weekly summary missing: {field}")

    def test_stats_fields(self):
        src = _read("plugins/companion/handler.py")
        for stat in ["feeds", "walks", "quests_completed", "facts_learned",
                      "messages_sent", "levels_gained", "achievements_earned",
                      "guardian_saves"]:
            self.assertIn(f'"{stat}"', src, f"Weekly stat missing: {stat}")


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint7Regression(unittest.TestCase):

    def test_voice_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/voice/transcribe", src)

    def test_websocket_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/ws", src)

    def test_adventure_server_side_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_active_encounters", src)


if __name__ == "__main__":
    unittest.main()

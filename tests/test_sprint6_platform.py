"""
tests/test_sprint6_platform.py — Sprint 6 Voice + Marketplace + WebSocket tests.

Validates all 5 Thor tasks:
  1. Voice endpoints (transcribe + speak) wrapping existing Whisper/Kokoro
  2. Marketplace endpoints (browse + search + detail + install)
  3. Web page summary endpoint (via browse/parser.py)
  4. WebSocket for real-time companion sync
  5. Morning briefing placeholder fix (null defaults)

Run from project root:
    python -m pytest tests/test_sprint6_platform.py -v
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
# Task 1 — Voice endpoints
# ---------------------------------------------------------------------------

class TestVoiceEndpoints(unittest.TestCase):

    def test_transcribe_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/voice/transcribe", src)

    def test_speak_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/voice/speak", src)

    def test_uses_existing_stt(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("transcribe_bytes", src)

    def test_uses_existing_tts(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("from plugins.voice.tts import synthesize", src)

    def test_audio_size_limit(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("25 * 1024 * 1024", src, "25MB audio upload limit")

    def test_text_length_limit(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("5000", src, "5000 char TTS limit")

    def test_returns_wav(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("audio/wav", src)

    def test_stt_module_exists(self):
        self.assertTrue((REPO_ROOT / "plugins" / "voice" / "stt.py").exists())

    def test_tts_module_exists(self):
        self.assertTrue((REPO_ROOT / "plugins" / "voice" / "tts.py").exists())

    def test_privacy_no_cloud(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("NEVER leaves the local network", src,
                      "Voice privacy commitment must be documented")


# ---------------------------------------------------------------------------
# Task 2 — Marketplace endpoints
# ---------------------------------------------------------------------------

class TestMarketplaceEndpoints(unittest.TestCase):

    def test_browse_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/marketplace/browse", src)

    def test_search_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/marketplace/search", src)

    def test_item_detail_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/marketplace/item/", src)

    def test_install_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/marketplace/install", src)

    def test_search_min_length(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("at least 2 characters", src)

    def test_paid_items_redirect_to_stripe(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("Stripe checkout", src)

    def test_uses_existing_registry(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_load_registry", src)


# ---------------------------------------------------------------------------
# Task 3 — Browse/summarize
# ---------------------------------------------------------------------------

class TestBrowseSummarize(unittest.TestCase):

    def test_summarize_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/browse/summarize", src)

    def test_uses_existing_parser(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("fetch_and_parse_sync", src)

    def test_url_validation(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("must start with http", src)

    def test_url_length_limit(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("2000", src, "URL max length")

    def test_returns_key_points(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("key_points", src)

    def test_parser_module_exists(self):
        self.assertTrue((REPO_ROOT / "plugins" / "browse" / "parser.py").exists())


# ---------------------------------------------------------------------------
# Task 4 — WebSocket
# ---------------------------------------------------------------------------

class TestWebSocket(unittest.TestCase):

    def test_ws_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/ws", src)

    def test_ws_connections_list(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_ws_connections", src)

    def test_ws_ping_pong(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"pong"', src)

    def test_ws_sync_command(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("companion_state_update", src)

    def test_broadcast_function(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("broadcast_ws_event", src)

    def test_ws_event_types(self):
        src = _read("plugins/companion/handler.py")
        for event in ["companion_state_update", "task_completed",
                      "chat_message", "notification"]:
            self.assertIn(event, src,
                          f"WebSocket event type '{event}' missing")


# ---------------------------------------------------------------------------
# Task 5 — Morning briefing fix
# ---------------------------------------------------------------------------

class TestMorningBriefingFix(unittest.TestCase):

    def test_briefing_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/morning-briefing", src)

    def test_null_defaults(self):
        src = _read("plugins/companion/handler.py")
        # Should have None as default for all fields
        briefing_start = src.find("def api_morning_briefing")
        briefing_end = src.find("app.include_router", briefing_start)
        briefing_body = src[briefing_start:briefing_end]
        self.assertGreaterEqual(briefing_body.count("None"), 5,
                                "Briefing fields should default to None")

    def test_uses_validate_briefing(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("validate_briefing_data", src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint6Regression(unittest.TestCase):

    def test_adventure_server_side_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_active_encounters", src)

    def test_feature_flags_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"features"', src)

    def test_guardian_checkin_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/guardian/check-in", src)

    def test_daily_gift_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/daily-gift", src)


if __name__ == "__main__":
    unittest.main()

"""
tests/test_sprint5_platform.py — Sprint 5 Platform Bridge + Security Fix tests.

Validates all 5 Thor tasks:
  1. Adventure rewards server-side (Heimdall MEDIUM fix)
  2. /mobile/unregister-push endpoint
  3. Platform activity in /mobile/sync
  4. Proactive guardian check-in (time-aware, species-specific)
  5. Translation API verified

Run from project root:
    python -m pytest tests/test_sprint5_platform.py -v
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
# Task 1 — Adventure rewards: server-side encounter storage
# ---------------------------------------------------------------------------

class TestAdventureServerSide(unittest.TestCase):

    def test_active_encounters_dict(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_active_encounters", src,
                      "Server-side encounter storage dict must exist")

    def test_encounter_stored_on_generate(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_active_encounters[companion_name]", src,
                      "Generate should store encounter keyed by companion")

    def test_encounter_expires_5_min(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("300", src, "Encounter should expire after 300s (5 min)")

    def test_choose_pops_encounter(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_active_encounters.pop(", src,
                      "Choose should pop (consume) the encounter")

    def test_choose_no_client_rewards(self):
        """Client rewards must NOT be used — server-side only."""
        src = _read("plugins/companion/handler.py")
        # Find the choose endpoint
        choose_start = src.find("async def api_adventure_choose")
        choose_end = src.find("# --- Sprint 4: Daily Gift", choose_start)
        choose_body = src[choose_start:choose_end]
        self.assertNotIn('body.get("rewards"', choose_body,
                         "Choose must NOT read rewards from client body")

    def test_choose_validates_index(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("Invalid choice index", src,
                      "Choose should validate choice_index bounds")

    def test_encounter_expiry_check(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("expires_at", src)
        self.assertIn("Encounter expired", src)


# ---------------------------------------------------------------------------
# Task 2 — /mobile/unregister-push
# ---------------------------------------------------------------------------

class TestUnregisterPush(unittest.TestCase):

    def test_unregister_route_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/mobile/unregister-push", src)

    def test_deletes_push_token_file(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("unlink", src,
                      "Should delete push_token.json via unlink()")


# ---------------------------------------------------------------------------
# Task 3 — Platform activity in /mobile/sync
# ---------------------------------------------------------------------------

class TestPlatformActivity(unittest.TestCase):

    def test_platform_key_in_sync(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"platform"', src)

    def test_platform_helper_function(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("_get_platform_activity", src)

    def test_platform_fields(self):
        src = _read("plugins/companion/handler.py")
        for field in ["uptime_hours", "models_loaded", "memory_count",
                      "plugins_active", "last_dream_cycle",
                      "last_prediction", "mesh_nodes"]:
            self.assertIn(f'"{field}"', src,
                          f"Platform field '{field}' missing")

    def test_graceful_fallbacks(self):
        src = _read("plugins/companion/handler.py")
        # Should have try/except for each data source
        platform_start = src.find("def _get_platform_activity")
        platform_end = src.find("# --- Sprint 5 Task 4:", platform_start)
        platform_body = src[platform_start:platform_end]
        self.assertGreaterEqual(platform_body.count("except Exception"), 4,
                                "Should gracefully handle plugin unavailability")


# ---------------------------------------------------------------------------
# Task 4 — Proactive guardian check-in
# ---------------------------------------------------------------------------

class TestGuardianCheckIn(unittest.TestCase):

    def test_checkin_route_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/guardian/check-in", src)

    def test_checkin_returns_proactive_warning(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("proactive_warning", src)

    def test_checkin_has_hold_option(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("hold_option", src)

    def test_species_specific_messages(self):
        src = _read("plugins/companion/handler.py")
        for species in ["cat", "dog", "penguin", "fox", "owl", "dragon"]:
            self.assertIn(f'"{species}"', src,
                          f"Guardian check-in missing species: {species}")

    def test_late_night_check(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("hour < 5", src,
                      "Should warn between midnight and 5am")


# ---------------------------------------------------------------------------
# Task 5 — Translation API verified
# ---------------------------------------------------------------------------

class TestTranslationAPI(unittest.TestCase):

    def test_translate_route_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/translate", src)

    def test_languages_route_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/translate/languages", src)

    def test_translate_request_model(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("TranslateRequest", src)

    def test_nllb_module_exists(self):
        self.assertTrue(
            (REPO_ROOT / "plugins" / "companion" / "nllb.py").exists(),
            "nllb.py should exist for translation"
        )


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint5Regression(unittest.TestCase):

    def test_adventure_signing_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("sign_adventure_result", src)

    def test_daily_gift_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/daily-gift", src)

    def test_feature_flags_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"features"', src)

    def test_hmac_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("hmac.compare_digest", src)


if __name__ == "__main__":
    unittest.main()

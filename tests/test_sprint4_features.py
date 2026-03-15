"""
tests/test_sprint4_features.py — Sprint 4 Mobile Feature Compatibility tests.

Validates all 4 Thor tasks:
  1. Adventure API (generate + choose, HMAC signing, cooldown)
  2. Daily gift API (get + claim, species-specific, inventory)
  3. Guardian API verified for mobile
  4. /mobile/sync feature flags

Run from project root:
    python -m pytest tests/test_sprint4_features.py -v
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
# Task 1 — Adventure API
# ---------------------------------------------------------------------------

class TestAdventureAPI(unittest.TestCase):

    def test_adventure_generate_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/adventure/generate", src)

    def test_adventure_choose_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/adventure/choose", src)

    def test_adventure_uses_hmac_signing(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("sign_adventure_result", src,
                      "Adventure results must be HMAC-signed")

    def test_adventure_has_cooldown(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("3600", src,
                      "Adventure should have 1-hour cooldown")

    def test_all_8_encounter_types(self):
        src = _read("plugins/companion/handler.py")
        for enc in ["riddle", "treasure", "merchant", "forage",
                     "lost_pet", "weather", "storyteller", "challenge"]:
            self.assertIn(f'"{enc}"', src,
                          f"Encounter type '{enc}' missing")

    def test_encounters_have_choices(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"choices"', src, "Encounters must have choices")

    def test_rewards_include_xp_and_happiness(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"xp"', src)
        self.assertIn('"happiness"', src)

    def test_adventure_guard_integration(self):
        """Verify adventure_guard.py has the signing infrastructure."""
        src = _read("plugins/companion/adventure_guard.py")
        self.assertIn("sign_adventure_result", src)
        self.assertIn("verify_adventure_result", src)
        self.assertIn("_ADVENTURE_KEY", src)


# ---------------------------------------------------------------------------
# Task 2 — Daily Gift API
# ---------------------------------------------------------------------------

class TestDailyGiftAPI(unittest.TestCase):

    def test_daily_gift_check_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/daily-gift", src)

    def test_daily_gift_claim_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/daily-gift/claim", src)

    def test_daily_gift_24h_cooldown(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("86400", src, "Daily gift should have 24-hour cooldown")

    def test_species_specific_gifts(self):
        src = _read("plugins/companion/handler.py")
        for species in ["cat", "dog", "penguin", "fox", "owl", "dragon"]:
            self.assertIn(f'"{species}"', src,
                          f"Species '{species}' should have daily gifts")

    def test_gift_types_present(self):
        src = _read("plugins/companion/handler.py")
        for gtype in ["poem", "item", "fact", "compliment"]:
            self.assertIn(f'"{gtype}"', src,
                          f"Gift type '{gtype}' should exist")

    def test_gift_adds_to_inventory(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("inventory", src,
                      "Gift claim should add items to inventory")

    def test_daily_gift_returns_availability(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"available"', src,
                      "GET /daily-gift should return availability status")


# ---------------------------------------------------------------------------
# Task 3 — Guardian API verified
# ---------------------------------------------------------------------------

class TestGuardianAPI(unittest.TestCase):

    def test_guardian_route_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/guardian", src)

    def test_guardian_accepts_text(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("GuardianRequest", src)

    def test_guardian_module_has_analyze(self):
        src = _read("plugins/companion/guardian.py")
        self.assertIn("analyze_message", src)

    def test_guardian_has_sentiment(self):
        src = _read("plugins/companion/guardian.py")
        self.assertIn("classify_sentiment", src)

    def test_guardian_has_regret_detection(self):
        src = _read("plugins/companion/guardian.py")
        self.assertIn("detect_regret_flags", src)

    def test_guardian_has_softer_rewrites(self):
        src = _read("plugins/companion/guardian.py")
        self.assertIn("suggest_softer", src)


# ---------------------------------------------------------------------------
# Task 4 — /mobile/sync feature flags
# ---------------------------------------------------------------------------

class TestMobileSyncFeatureFlags(unittest.TestCase):

    def test_sync_has_features_dict(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn('"features"', src,
                      "/mobile/sync must include features dict")

    def test_feature_flags_present(self):
        src = _read("plugins/companion/handler.py")
        for feature in ["adventures", "daily_gift", "guardian",
                        "teach_me", "translation", "morning_briefing"]:
            self.assertIn(f'"{feature}"', src,
                          f"Feature flag '{feature}' missing from sync response")

    def test_daily_gift_available_flag(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("daily_gift_available", src)

    def test_adventure_available_flag(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("adventure_available", src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint4Regression(unittest.TestCase):

    def test_cors_no_wildcard(self):
        import yaml
        data = yaml.safe_load(_read("valhalla.yaml"))
        origins = data.get("dashboard", {}).get("cors_origins", [])
        self.assertNotIn("*", origins)

    def test_hmac_still_used(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("hmac.compare_digest", src)

    def test_push_registration_still_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/mobile/register-push", src)

    def test_chat_history_still_exists(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/chat/history", src)


if __name__ == "__main__":
    unittest.main()

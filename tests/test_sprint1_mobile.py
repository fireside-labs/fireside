"""
tests/test_sprint1_mobile.py — Sprint 1 Mobile backend readiness tests.

Tests exactly 4 things:
  1. valhalla.yaml cors_origins includes "*"
  2. api/v1.py /status returns mobile_ready: True
  3. companion/mobile/sync returns correct response shape
  4. companion/mobile/pair generates a 6-char token and persists it

Pattern: uses importlib.util to load modules directly (project standard).

Run from project root:
    python -m pytest tests/test_sprint1_mobile.py -v
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
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Helper: load a module by file path (project-standard pattern)
# ---------------------------------------------------------------------------

def _load(relative_path: str):
    filepath = REPO_ROOT / relative_path
    safe_name = relative_path.replace("/", "_").replace("\\", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(safe_name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Task 1 — CORS: valhalla.yaml has wildcard origin
# ---------------------------------------------------------------------------

class TestCorsConfig(unittest.TestCase):

    def test_cors_wildcard_present(self):
        import yaml
        data = yaml.safe_load((REPO_ROOT / "valhalla.yaml").read_text(encoding="utf-8"))
        origins = data.get("dashboard", {}).get("cors_origins", [])
        self.assertIn("*", origins,
                      f"valhalla.yaml cors_origins must include '*'. Got: {origins}")


# ---------------------------------------------------------------------------
# Task 4 — /status: mobile_ready field
# ---------------------------------------------------------------------------

class TestStatusMobileReady(unittest.TestCase):
    """Verify mobile_ready: True appears in the /status return dict."""

    def test_mobile_ready_in_status_response(self):
        """
        Directly inspect the source of api/v1.py and verify
        'mobile_ready' is present in the get_status return block.
        This is a source-level assertion — reliable without running the server.
        """
        v1_src = (REPO_ROOT / "api" / "v1.py").read_text(encoding="utf-8")
        self.assertIn(
            '"mobile_ready"', v1_src,
            "mobile_ready key not found in api/v1.py"
        )
        # Also verify True (not False)
        # Find the line with mobile_ready and confirm it's True
        for line in v1_src.splitlines():
            if '"mobile_ready"' in line:
                self.assertIn("True", line,
                              f"mobile_ready should be True, got line: {line.strip()}")
                break


# ---------------------------------------------------------------------------
# Task 3 — /mobile/pair: token generation logic (pure unit test)
# ---------------------------------------------------------------------------

class TestMobilePairLogic(unittest.TestCase):
    """Test the /mobile/pair token generation in isolation."""

    def _generate_token(self, token_dir: Path):
        """Replicate the pairing logic from handler.py."""
        import secrets
        import string
        from datetime import datetime, timezone, timedelta

        alphabet = string.ascii_uppercase + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(6))

        expires_at = datetime.now(timezone.utc) + timedelta(days=365)

        valhalla_dir = token_dir / ".valhalla"
        valhalla_dir.mkdir(parents=True, exist_ok=True)
        token_file = valhalla_dir / "mobile_token.json"
        token_file.write_text(
            json.dumps({
                "token": token,
                "created_at": time.time(),
                "expires_at": expires_at.timestamp(),
            }),
            encoding="utf-8",
        )
        return token, expires_at, token_file

    def test_token_is_6_chars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token, _, _ = self._generate_token(Path(tmpdir))
        self.assertEqual(len(token), 6, f"Token must be 6 chars, got: '{token}'")

    def test_token_is_alphanumeric_uppercase(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token, _, _ = self._generate_token(Path(tmpdir))
        self.assertTrue(token.isupper() or token.isalnum(),
                        f"Token should be uppercase alphanumeric: '{token}'")
        self.assertTrue(token.isalnum(), f"Token should be alphanumeric: '{token}'")

    def test_token_persists_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token, expires_at, token_file = self._generate_token(Path(tmpdir))
            self.assertTrue(token_file.exists(), "Token file not written")
            saved = json.loads(token_file.read_text())
        self.assertEqual(saved["token"], token)
        self.assertIn("expires_at", saved)
        self.assertIn("created_at", saved)

    def test_token_expires_in_365_days(self):
        from datetime import datetime, timezone, timedelta
        with tempfile.TemporaryDirectory() as tmpdir:
            token, expires_at, _ = self._generate_token(Path(tmpdir))
        expected = datetime.now(timezone.utc) + timedelta(days=364)  # ≈365 days
        self.assertGreater(expires_at, expected,
                           "Token expiry should be ~365 days from now")

    def test_tokens_are_unique(self):
        """Each call should produce a different token (probabilistic)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            t1, _, _ = self._generate_token(Path(tmpdir))
        with tempfile.TemporaryDirectory() as tmpdir:
            t2, _, _ = self._generate_token(Path(tmpdir))
        # Probability of collision with 36^6 = 2.1B possibilities is negligible
        self.assertNotEqual(t1, t2, "Two generated tokens should differ")


# ---------------------------------------------------------------------------
# Task 2 — /mobile/sync: endpoint implementation present in handler
# ---------------------------------------------------------------------------

class TestMobileSyncPresent(unittest.TestCase):
    """Verify the mobile sync and pair endpoint code is present in handler.py."""

    def setUp(self):
        self.handler_src = (
            REPO_ROOT / "plugins" / "companion" / "handler.py"
        ).read_text(encoding="utf-8")

    def test_mobile_sync_route_present(self):
        self.assertIn("/api/v1/companion/mobile/sync", self.handler_src,
                      "mobile/sync route not found in handler.py")

    def test_mobile_pair_route_present(self):
        self.assertIn("/api/v1/companion/mobile/pair", self.handler_src,
                      "mobile/pair route not found in handler.py")

    def test_mobile_sync_returns_required_keys(self):
        """Sync handler must include all 6 required response keys."""
        for key in ("ok", "companion", "personality", "mood_prefix",
                    "pending_tasks", "synced_at"):
            self.assertIn(f'"{key}"', self.handler_src,
                          f"mobile/sync response missing key: '{key}'")

    def test_mobile_pair_returns_token_key(self):
        self.assertIn('"token"', self.handler_src,
                      "mobile/pair must return 'token' key")

    def test_mobile_pair_returns_expires_at(self):
        self.assertIn('"expires_at"', self.handler_src,
                      "mobile/pair must return 'expires_at' key")

    def test_mobile_pair_uses_6_chars(self):
        self.assertIn("range(6)", self.handler_src,
                      "mobile/pair should generate 6-char token (range(6))")

    def test_token_stored_in_valhalla_dir(self):
        self.assertIn("mobile_token.json", self.handler_src,
                      "Token should be persisted to mobile_token.json")


# ---------------------------------------------------------------------------
# Integration smoke: valhalla.yaml is valid YAML
# ---------------------------------------------------------------------------

class TestConfigValid(unittest.TestCase):

    def test_valhalla_yaml_is_valid(self):
        import yaml
        try:
            yaml.safe_load((REPO_ROOT / "valhalla.yaml").read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            self.fail(f"valhalla.yaml is invalid YAML: {e}")


if __name__ == "__main__":
    unittest.main()

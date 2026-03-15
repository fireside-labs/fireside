"""
tests/test_sprint1_mobile.py — Sprint 1 Mobile backend readiness tests.

Validates:
  1. CORS wildcard in valhalla.yaml
  2. GET /api/v1/status includes mobile_ready: true
  3. POST /api/v1/companion/mobile/sync returns correct shape
  4. POST /api/v1/companion/mobile/pair generates a token and persists it

Run from project root:
    python -m pytest tests/test_sprint1_mobile.py -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Task 1 — CORS wildcard in valhalla.yaml
# ---------------------------------------------------------------------------

class TestCorsConfig(unittest.TestCase):
    """Verify valhalla.yaml includes wildcard CORS for mobile."""

    def test_cors_wildcard_present(self):
        import yaml
        yaml_path = Path(__file__).parent.parent / "valhalla.yaml"
        self.assertTrue(yaml_path.exists(), "valhalla.yaml not found")
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        cors_origins = data.get("dashboard", {}).get("cors_origins", [])
        self.assertIn("*", cors_origins,
                      "valhalla.yaml cors_origins must include '*' for mobile app")


# ---------------------------------------------------------------------------
# Task 4 — /status includes mobile_ready
# ---------------------------------------------------------------------------

class TestStatusEndpoint(unittest.TestCase):
    """GET /api/v1/status must return mobile_ready: true."""

    def _make_app(self):
        """Build a minimal FastAPI test app with the v1 router."""
        from fastapi import FastAPI
        from api.v1 import init_api

        app = FastAPI()
        config = {
            "node": {"name": "test-node", "role": "orchestrator", "port": 8765},
            "models": {"default": "test-model"},
            "_meta": {"base_dir": str(Path(__file__).parent.parent)},
        }
        router = init_api(config)
        app.include_router(router)
        return app

    def test_status_has_mobile_ready(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        app = self._make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("mobile_ready", data, "/status response is missing 'mobile_ready' field")
        self.assertTrue(data["mobile_ready"], "mobile_ready should be True")

    def test_status_standard_fields(self):
        """Smoke test: existing fields still present alongside new one."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        app = self._make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/status")
        data = resp.json()
        for field in ("node", "role", "status", "model", "uptime_seconds"):
            self.assertIn(field, data, f"Expected field '{field}' missing from /status")


# ---------------------------------------------------------------------------
# Task 2 — /companion/mobile/sync
# ---------------------------------------------------------------------------

class TestMobileSync(unittest.TestCase):
    """/companion/mobile/sync returns correct shape."""

    def _make_companion_app(self):
        from fastapi import FastAPI
        app = FastAPI()

        mock_state = {
            "name": "Luna",
            "species": "cat",
            "level": 3,
            "xp": 40,
            "hunger": 80,
            "mood": 90,
            "energy": 70,
        }

        # Patch all companion sim imports
        with patch.dict("sys.modules", {
            "plugins": MagicMock(),
            "plugins.companion": MagicMock(),
            "plugins.companion.sim": MagicMock(
                load_state=MagicMock(return_value=mock_state),
                get_status=MagicMock(return_value=mock_state),
                get_mood_prefix=MagicMock(return_value="😺 "),
            ),
            "plugins.companion.queue": MagicMock(
                get_queue=MagicMock(return_value=[]),
                add_task=MagicMock(return_value={"ok": True, "task": {}}),
                get_stats=MagicMock(return_value={"total": 0}),
            ),
            "plugins.companion.nllb": MagicMock(),
            "plugins.companion.guardian": MagicMock(),
            "plugins.agent_profiles": MagicMock(),
            "plugins.agent_profiles.leveling": MagicMock(
                load_profile=MagicMock(return_value={"personality": {"tone": "warm"}})
            ),
            "plugin_loader": MagicMock(emit_event=MagicMock()),
        }):
            from plugins.companion.handler import register_routes
            register_routes(app, {})

        return app

    def test_mobile_sync_shape(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        app = self._make_companion_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/companion/mobile/sync")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for key in ("ok", "companion", "personality", "mood_prefix", "pending_tasks", "synced_at"):
            self.assertIn(key, data,
                          f"/mobile/sync response missing required key '{key}'")

    def test_mobile_sync_ok_true(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        app = self._make_companion_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/companion/mobile/sync")
        self.assertTrue(resp.json().get("ok"))

    def test_mobile_sync_no_companion_returns_404(self):
        """Without a companion adopted, sync should return 404."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        from fastapi import FastAPI
        app = FastAPI()
        with patch.dict("sys.modules", {
            "plugins": MagicMock(),
            "plugins.companion": MagicMock(),
            "plugins.companion.sim": MagicMock(
                load_state=MagicMock(return_value=None),  # No companion
                get_status=MagicMock(return_value={}),
                get_mood_prefix=MagicMock(return_value=""),
            ),
            "plugins.companion.queue": MagicMock(get_queue=MagicMock(return_value=[])),
            "plugins.companion.nllb": MagicMock(),
            "plugins.companion.guardian": MagicMock(),
            "plugins.agent_profiles": MagicMock(),
            "plugins.agent_profiles.leveling": MagicMock(),
            "plugin_loader": MagicMock(emit_event=MagicMock()),
        }):
            from plugins.companion.handler import register_routes
            register_routes(app, {})

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/companion/mobile/sync")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Task 3 — /companion/mobile/pair
# ---------------------------------------------------------------------------

class TestMobilePair(unittest.TestCase):
    """/companion/mobile/pair generates and stores a token."""

    def _make_app_with_pair(self):
        from fastapi import FastAPI
        app = FastAPI()
        with patch.dict("sys.modules", {
            "plugins": MagicMock(),
            "plugins.companion": MagicMock(),
            "plugins.companion.sim": MagicMock(
                load_state=MagicMock(return_value={"name": "Luna", "species": "cat"}),
                get_status=MagicMock(return_value={}),
                get_mood_prefix=MagicMock(return_value=""),
                _state_file=MagicMock(return_value=Path(tempfile.mktemp())),
            ),
            "plugins.companion.queue": MagicMock(
                get_queue=MagicMock(return_value=[]),
                add_task=MagicMock(return_value={"ok": True, "task": {}}),
                get_stats=MagicMock(return_value={"total": 0}),
            ),
            "plugins.companion.nllb": MagicMock(),
            "plugins.companion.guardian": MagicMock(),
            "plugins.agent_profiles": MagicMock(),
            "plugins.agent_profiles.leveling": MagicMock(
                load_profile=MagicMock(return_value={"personality": {}})
            ),
            "plugin_loader": MagicMock(emit_event=MagicMock()),
        }):
            from plugins.companion.handler import register_routes
            register_routes(app, {})
        return app

    def test_pair_returns_token(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                app = self._make_app_with_pair()
                client = TestClient(app, raise_server_exceptions=False)
                resp = client.post("/api/v1/companion/mobile/pair")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("token", data)
        self.assertIn("expires_at", data)

    def test_pair_token_is_6_chars(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                app = self._make_app_with_pair()
                client = TestClient(app, raise_server_exceptions=False)
                resp = client.post("/api/v1/companion/mobile/pair")

        token = resp.json().get("token", "")
        self.assertEqual(len(token), 6, f"Token should be 6 chars, got: '{token}'")

    def test_pair_token_alphanumeric(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                app = self._make_app_with_pair()
                client = TestClient(app, raise_server_exceptions=False)
                resp = client.post("/api/v1/companion/mobile/pair")

        token = resp.json().get("token", "")
        self.assertTrue(token.isalnum(), f"Token should be alphanumeric, got: '{token}'")

    def test_pair_persists_token_file(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("httpx not installed — skipping HTTP tests")

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            with patch("pathlib.Path.home", return_value=home):
                app = self._make_app_with_pair()
                client = TestClient(app, raise_server_exceptions=False)
                resp = client.post("/api/v1/companion/mobile/pair")
                expected_token = resp.json().get("token", "")

                token_file = home / ".valhalla" / "mobile_token.json"
                self.assertTrue(token_file.exists(), "Token file not created")
                saved = json.loads(token_file.read_text())
                self.assertEqual(saved["token"], expected_token)
                self.assertIn("expires_at", saved)


if __name__ == "__main__":
    unittest.main()

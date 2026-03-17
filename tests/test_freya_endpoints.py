"""
tests/test_freya_endpoints.py — Freya Verification Suite

Comprehensive live-endpoint testing for the Fireside AI companion backend.
Uses FastAPI TestClient (in-process, no port binding) to validate all
endpoints that the dashboard consumes.

Run:  python -m pytest tests/test_freya_endpoints.py -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# App fixture — creates a fresh FastAPI app via bifrost.create_app()
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Create a TestClient from a fresh Bifrost app.

    Uses the real valhalla.yaml and plugins directory so we test the actual
    wiring, not mocks.
    """
    from fastapi.testclient import TestClient
    from bifrost import create_app

    app = create_app(str(REPO_ROOT / "valhalla.yaml"))
    with TestClient(app) as c:
        yield c


# ===========================================================================
# 0. Health / Smoke Test
# ===========================================================================

class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "node" in data
        assert data["version"] == "2.0.0"


# ===========================================================================
# 1. GET /api/v1/plugins — returns loaded plugins
# ===========================================================================

class TestGetPlugins:
    def test_returns_plugins_list(self, client):
        r = client.get("/api/v1/plugins")
        assert r.status_code == 200
        data = r.json()
        assert "plugins" in data
        assert "count" in data
        assert isinstance(data["plugins"], list)
        # We have 26 plugins enabled in valhalla.yaml; some may fail to load
        # but the endpoint itself must return a list
        assert data["count"] >= 0

    def test_plugin_has_expected_fields(self, client):
        r = client.get("/api/v1/plugins")
        data = r.json()
        if data["count"] > 0:
            p = data["plugins"][0]
            assert "name" in p
            assert "version" in p
            assert "status" in p


# ===========================================================================
# 2. POST /api/v1/plugins/install — loads a plugin
# ===========================================================================

class TestInstallPlugin:
    def test_install_existing_plugin(self, client):
        """Install a plugin that exists in the plugins/ directory."""
        r = client.post(
            "/api/v1/plugins/install",
            json={"name": "watchdog"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["plugin"] == "watchdog"

    def test_install_nonexistent_plugin_returns_404(self, client):
        r = client.post(
            "/api/v1/plugins/install",
            json={"name": "does-not-exist-xyz"},
        )
        assert r.status_code == 404


# ===========================================================================
# 3. GET /api/v1/soul/SOUL.odin.md — returns soul content
# ===========================================================================

class TestGetSoul:
    def test_read_soul_file(self, client):
        # The soul editor reads from mesh/souls/
        r = client.get("/api/v1/soul/SOUL.odin.md")
        assert r.status_code == 200
        data = r.json()
        assert "filename" in data
        assert "content" in data
        assert data["filename"] == "SOUL.odin.md"
        assert len(data["content"]) > 0

    def test_read_identity_file(self, client):
        r = client.get("/api/v1/soul/IDENTITY.odin.md")
        assert r.status_code == 200
        data = r.json()
        assert data["filename"] == "IDENTITY.odin.md"

    def test_nonexistent_soul_returns_404(self, client):
        r = client.get("/api/v1/soul/DOESNOTEXIST.md")
        assert r.status_code == 404

    def test_path_traversal_blocked(self, client):
        r = client.get("/api/v1/soul/../../valhalla.yaml")
        # FastAPI normalizes '..' before route matching, so the file
        # is either rejected (400) or simply not found (404) — both safe
        assert r.status_code in (400, 404)


# ===========================================================================
# 4. PUT /api/v1/soul/SOUL.odin.md — persists changes
# ===========================================================================

class TestPutSoul:
    def test_write_and_readback(self, client):
        # Read original content
        r = client.get("/api/v1/soul/SOUL.odin.md")
        original = r.json()["content"]

        # Write new content
        test_content = original + "\n<!-- Freya test marker -->"
        r = client.put(
            "/api/v1/soul/SOUL.odin.md",
            json={"content": test_content},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["bytes_written"] > 0

        # Read back and verify
        r = client.get("/api/v1/soul/SOUL.odin.md")
        assert "Freya test marker" in r.json()["content"]

        # Restore original content
        client.put(
            "/api/v1/soul/SOUL.odin.md",
            json={"content": original},
        )


# ===========================================================================
# 5. GET /api/v1/config/keys — returns masked API keys
# ===========================================================================

class TestGetKeys:
    def test_returns_keys_array(self, client):
        r = client.get("/api/v1/config/keys")
        assert r.status_code == 200
        data = r.json()
        assert "keys" in data
        assert isinstance(data["keys"], list)
        # Should always return entries for the 5 known providers
        providers = {k["provider"] for k in data["keys"]}
        assert "openai" in providers
        assert "anthropic" in providers

    def test_keys_have_masked_format(self, client):
        r = client.get("/api/v1/config/keys")
        for key in r.json()["keys"]:
            assert "provider" in key
            assert "connected" in key
            # masked is either None or starts with "..."
            if key["masked"] is not None:
                assert key["masked"].startswith("...")


# ===========================================================================
# 6. POST /api/v1/config/keys — saves a key
# ===========================================================================

class TestPostKeys:
    def test_save_and_verify_key(self, client):
        # Save a test key
        r = client.post(
            "/api/v1/config/keys",
            json={"provider": "replicate", "key": "test-replicate-key-12345"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["provider"] == "replicate"

        # Verify via GET — should show as connected
        r = client.get("/api/v1/config/keys")
        replicate_entry = next(
            (k for k in r.json()["keys"] if k["provider"] == "replicate"), None
        )
        assert replicate_entry is not None
        assert replicate_entry["connected"] is True
        assert replicate_entry["masked"] == "...2345"

    def test_save_empty_key_rejected(self, client):
        r = client.post(
            "/api/v1/config/keys",
            json={"provider": "", "key": ""},
        )
        assert r.status_code == 400


# ===========================================================================
# 7. POST /api/v1/chat — streams SSE with assembled prompt
# ===========================================================================

class TestChat:
    def test_chat_endpoint_exists(self, client):
        """Chat endpoint should exist and respond.

        The agent_profiles plugin registers POST /api/v1/chat with its
        own ChatRequest model ({message, agent?}).
        Without a brain installed, it returns 503.
        With a brain running, it would return SSE.
        """
        r = client.post(
            "/api/v1/chat",
            json={"message": "Hello, how are you?"},
        )
        # 503 = no brain installed (expected in test environment)
        # 200 = brain is running (would return SSE stream)
        assert r.status_code in (200, 503), \
            f"Unexpected status {r.status_code}: {r.text[:200]}"
        if r.status_code == 503:
            data = r.json()
            assert "brain" in data.get("detail", "").lower()

    def test_chat_with_agent_name(self, client):
        """Chat can optionally specify which agent to route to."""
        r = client.post(
            "/api/v1/chat",
            json={"message": "Hello Atlas", "agent": "odin"},
        )
        assert r.status_code in (200, 503)


# ===========================================================================
# 8. GET /api/v1/working-memory — returns memory status
# ===========================================================================

class TestWorkingMemoryStatus:
    def test_returns_status(self, client):
        r = client.get("/api/v1/working-memory")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "capacity" in data
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate" in data
        assert "lancedb_available" in data
        assert "contents" in data


# ===========================================================================
# 9. POST /api/v1/working-memory/observe — adds a memory
# ===========================================================================

class TestWorkingMemoryObserve:
    def test_observe_returns_key(self, client):
        r = client.post(
            "/api/v1/working-memory/observe",
            json={
                "content": "The build passed all tests today",
                "importance": 0.8,
                "source": "freya-test",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "key" in data
        assert data["items"] >= 1

    def test_observe_with_defaults(self, client):
        r = client.post(
            "/api/v1/working-memory/observe",
            json={"content": "Simple observation with defaults"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ===========================================================================
# 10. POST /api/v1/working-memory/recall — queries memory
# ===========================================================================

class TestWorkingMemoryRecall:
    def test_recall_by_query(self, client):
        # First observe something
        client.post(
            "/api/v1/working-memory/observe",
            json={"content": "Python is a great programming language", "source": "test"},
        )

        # Then recall it
        r = client.post(
            "/api/v1/working-memory/recall",
            json={"query": "Python", "top_k": 5},
        )
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert "count" in data
        assert "query" in data
        assert data["query"] == "Python"
        # Should find the Python memory
        assert data["count"] >= 1

    def test_recall_empty_query(self, client):
        r = client.post(
            "/api/v1/working-memory/recall",
            json={"query": "", "top_k": 5},
        )
        assert r.status_code == 200
        data = r.json()
        assert "results" in data


# ===========================================================================
# Bonus: Additional core endpoints the dashboard uses
# ===========================================================================

class TestStatus:
    def test_status_returns_node_info(self, client):
        r = client.get("/api/v1/status")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "online"
        assert "node" in data
        assert "uptime_seconds" in data
        assert "plugins_loaded" in data
        assert "gpu" in data

class TestConfig:
    def test_get_config(self, client):
        r = client.get("/api/v1/config")
        assert r.status_code == 200
        data = r.json()
        assert "config" in data
        assert "raw_yaml" in data

class TestNodes:
    def test_get_nodes(self, client):
        r = client.get("/api/v1/nodes")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "count" in data


# ===========================================================================
# API endpoint inventory — verify all routes are mounted
# ===========================================================================

class TestRouteInventory:
    """Verify that all expected routes are registered on the app."""

    EXPECTED_ROUTES = [
        ("GET", "/health"),
        ("GET", "/api/v1/status"),
        ("GET", "/api/v1/nodes"),
        ("GET", "/api/v1/plugins"),
        ("POST", "/api/v1/plugins/install"),
        ("GET", "/api/v1/config"),
        ("GET", "/api/v1/config/keys"),
        ("POST", "/api/v1/config/keys"),
        ("POST", "/api/v1/chat"),
        ("GET", "/api/v1/soul/{filename:path}"),
        ("PUT", "/api/v1/soul/{filename:path}"),
    ]

    def test_all_routes_registered(self, client):
        """Walk app routes and verify our expected routes exist."""
        app = client.app

        registered = set()
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    registered.add((method, route.path))

        # Also check included routers
        for router in getattr(app, "routes", []):
            if hasattr(router, "routes"):
                for sub in router.routes:
                    if hasattr(sub, "methods") and hasattr(sub, "path"):
                        for method in sub.methods:
                            registered.add((method, sub.path))

        for method, path in self.EXPECTED_ROUTES:
            assert (method, path) in registered, \
                f"Missing route: {method} {path}"

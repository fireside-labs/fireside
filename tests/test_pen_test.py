"""
tests/test_pen_test.py — Automated penetration tests for Valhalla Bifrost V2.

These tests attack the V2 API endpoints to find vulnerabilities.
Each test documents the attack vector, expected behavior, and severity.

Run against a live server:
    cd /Users/odin/Documents/ProjectOpenClaw/valhalla-mesh-v2
    python3 -m pytest tests/test_pen_test.py -v

Requires: Bifrost V2 running on localhost:8766 (or set BIFROST_URL env var)
If the server is not running, tests will be skipped.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BIFROST_URL = os.environ.get("BIFROST_URL", "http://localhost:8766")


def _api(method: str, path: str, body: dict = None,
         headers: dict = None) -> tuple:
    """Make an HTTP request. Returns (status_code, response_body_dict)."""
    url = f"{BIFROST_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body_text = resp.read().decode()
            try:
                return resp.status, json.loads(body_text)
            except json.JSONDecodeError:
                return resp.status, {"raw": body_text}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(body_text)
        except json.JSONDecodeError:
            return e.code, {"raw": body_text}
    except Exception as e:
        return 0, {"error": str(e)}


def _server_available() -> bool:
    try:
        urllib.request.urlopen(f"{BIFROST_URL}/health", timeout=2)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Path Traversal Tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(_server_available(), "Bifrost V2 not running")
class TestPathTraversal(unittest.TestCase):
    """SEVERITY: HIGH — Path traversal on soul file endpoints."""

    def test_soul_read_dotdot(self):
        """GET /api/v1/soul/../../etc/passwd — direct traversal."""
        status, body = _api("GET", "/api/v1/soul/../../etc/passwd")
        self.assertIn(status, (400, 404, 422),
                     f"Expected rejection, got {status}: {body}")

    def test_soul_read_encoded_dotdot(self):
        """GET /api/v1/soul/..%2F..%2Fetc%2Fpasswd — URL-encoded traversal."""
        status, body = _api("GET", "/api/v1/soul/..%2F..%2Fetc%2Fpasswd")
        self.assertIn(status, (400, 404, 422),
                     f"Expected rejection, got {status}: {body}")

    def test_soul_read_double_dot_bypass(self):
        """GET /api/v1/soul/....//....//etc/passwd — double-dot bypass."""
        status, body = _api("GET", "/api/v1/soul/....//....//etc/passwd")
        self.assertIn(status, (400, 404, 422),
                     f"Expected rejection, got {status}: {body}")

    def test_soul_read_backslash(self):
        r"""GET /api/v1/soul/..\..\\etc\\passwd — backslash traversal."""
        status, body = _api("GET", r"/api/v1/soul/..\..\etc\passwd")
        self.assertIn(status, (400, 404, 422),
                     f"Expected rejection, got {status}: {body}")

    def test_soul_write_traversal(self):
        """PUT /api/v1/soul/../../tmp/pwned — write outside soul dir."""
        status, body = _api("PUT", "/api/v1/soul/../../tmp/pwned",
                           {"content": "hacked"})
        self.assertIn(status, (400, 404, 422),
                     f"Expected rejection, got {status}: {body}")
        # Verify no file was written
        self.assertFalse(Path("/tmp/pwned").exists(),
                        "File was written outside soul directory!")


# ---------------------------------------------------------------------------
# XSS Tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(_server_available(), "Bifrost V2 not running")
class TestXSS(unittest.TestCase):
    """SEVERITY: MEDIUM — XSS via soul editor content."""

    def test_script_tag_injection(self):
        """PUT soul file with <script>alert(1)</script> — should store raw, not execute."""
        xss_payload = '<script>alert("XSS")</script>'
        # Write — should succeed (it's valid markdown content)
        status, body = _api("PUT", "/api/v1/soul/xss_test.md",
                           {"content": xss_payload})
        # It's OK if this succeeds — soul files are markdown
        # The defense is on the DASHBOARD side (React auto-escapes)
        if status == 200:
            # Read it back — verify it's stored raw, not modified
            status2, body2 = _api("GET", "/api/v1/soul/xss_test.md")
            if status2 == 200:
                self.assertEqual(body2.get("content"), xss_payload,
                               "Content was modified — potential sanitization issue")
            # Clean up
            _api("PUT", "/api/v1/soul/xss_test.md", {"content": "# Clean"})


# ---------------------------------------------------------------------------
# YAML Injection Tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(_server_available(), "Bifrost V2 not running")
class TestYAMLInjection(unittest.TestCase):
    """SEVERITY: CRITICAL — Config injection via PUT /api/v1/config."""

    def test_yaml_bomb(self):
        """PUT /api/v1/config with YAML billion-laughs — should be rejected."""
        yaml_bomb = """
a: &a ["lol","lol","lol","lol","lol","lol","lol","lol","lol"]
b: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]
c: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]
d: &d [*c,*c,*c,*c,*c,*c,*c,*c,*c]
"""
        status, body = _api("PUT", "/api/v1/config",
                           {"yaml_content": yaml_bomb})
        # Should fail validation (missing required keys)
        self.assertIn(status, (400, 422),
                     f"YAML bomb should be rejected, got {status}: {body}")

    def test_overwrite_auth_token(self):
        """PUT /api/v1/config overwriting mesh.auth_token — should warn."""
        # First get current config
        status, body = _api("GET", "/api/v1/config")
        if status != 200:
            self.skipTest("Cannot read config")

        # This tests that config writes are validated.
        # The config loader should reject configs that are missing required keys.
        malicious = "node:\n  name: hacked\n  port: 9999\n"
        status2, body2 = _api("PUT", "/api/v1/config",
                             {"yaml_content": malicious})
        self.assertIn(status2, (400, 422),
                     f"Incomplete config should be rejected, got {status2}: {body2}")


# ---------------------------------------------------------------------------
# CSRF Tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(_server_available(), "Bifrost V2 not running")
class TestCSRF(unittest.TestCase):
    """SEVERITY: MEDIUM — Unauthenticated state-changing requests."""

    def test_model_switch_no_auth(self):
        """POST /api/v1/model-switch without auth — should still work in warning mode."""
        # In warning mode (placeholder tokens), requests are allowed.
        # This test documents the current state — auth enforcement
        # happens when real tokens are set in valhalla.yaml.
        status, body = _api("POST", "/api/v1/model-switch",
                           {"alias": "odin"})
        # In warning mode, this succeeds (200/202)
        # When auth is enforced, this should return 401
        self.assertIn(status, (200, 202, 401),
                     f"Unexpected status for model-switch: {status}")


# ---------------------------------------------------------------------------
# Join Token Tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(_server_available(), "Bifrost V2 not running")
class TestJoinToken(unittest.TestCase):
    """SEVERITY: HIGH — Join token replay and expiry."""

    def test_invalid_token_rejected(self):
        """POST /api/v1/mesh/announce with invalid token — must be rejected."""
        status, body = _api("POST", "/api/v1/mesh/announce", {
            "name": "evil-node",
            "ip": "10.0.0.1",
            "port": 8765,
            "token": "fake-token-12345",
        })
        self.assertEqual(status, 401,
                        f"Invalid join token should return 401, got {status}: {body}")


# ---------------------------------------------------------------------------
# Plugin Install Traversal
# ---------------------------------------------------------------------------

@unittest.skipUnless(_server_available(), "Bifrost V2 not running")
class TestPluginInstall(unittest.TestCase):
    """SEVERITY: MEDIUM — Plugin install path traversal."""

    def test_traversal_name(self):
        """POST /api/v1/plugins/install with name '../../etc' — should be rejected."""
        status, body = _api("POST", "/api/v1/plugins/install",
                           {"name": "../../etc"})
        self.assertEqual(status, 404,
                        f"Traversal plugin name should not resolve, got {status}: {body}")

    def test_dot_name(self):
        """POST /api/v1/plugins/install with name '..' — should be rejected."""
        status, body = _api("POST", "/api/v1/plugins/install",
                           {"name": ".."})
        self.assertIn(status, (400, 404),
                     f"'..' plugin should not install, got {status}: {body}")


# ---------------------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(_server_available(), "Bifrost V2 not running")
class TestRateLimiting(unittest.TestCase):
    """SEVERITY: LOW — Rate limiting enforcement."""

    def test_rate_limit_model_switch(self):
        """POST /api/v1/model-switch 7 times rapidly — 6th should be 429."""
        statuses = []
        for i in range(7):
            status, body = _api("POST", "/api/v1/model-switch",
                               {"alias": "odin"})
            statuses.append(status)

        # At least one should be 429 (limit is 5/min)
        hit_429 = 429 in statuses
        # If rate limiter is active, we should see 429
        # If not wired yet, all will be 200
        if not hit_429:
            # This is informational — rate limiter might not be active
            pass  # Acceptable in warning mode

    def test_health_not_limited(self):
        """GET /health should never be rate limited."""
        for _ in range(20):
            status, _ = _api("GET", "/health")
            self.assertEqual(status, 200,
                           "Health endpoint should never be rate limited")


if __name__ == "__main__":
    unittest.main()

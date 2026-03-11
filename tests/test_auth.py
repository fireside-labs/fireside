"""
tests/test_auth.py -- Unit tests for Heimdall's auth middleware.

Run: cd /Users/odin/Documents/valhalla-mesh-v2 && python3 -m pytest tests/test_auth.py -v
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from io import BytesIO

# Add middleware to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from middleware.auth import (
    verify_node_token,
    verify_dashboard_key,
    require_auth,
    sanitize_path,
    validate_model_id,
    validate_regex_pattern,
    _is_placeholder,
)


def _make_handler(headers: dict = None, client_ip: str = "192.168.1.100"):
    """Create a mock HTTP handler with the given headers."""
    handler = MagicMock()
    handler.headers = MagicMock()
    handler.headers.get = lambda name, default=None: (headers or {}).get(name, default)
    handler.client_address = (client_ip, 54321)
    handler.path = "/test"
    handler.wfile = BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


class TestVerifyNodeToken(unittest.TestCase):
    """Tests for node-to-node bearer token verification."""

    def test_valid_token(self):
        config = {"mesh": {"auth_token": "secret-token-12345"}}
        handler = _make_handler({"Authorization": "Bearer secret-token-12345",
                                  "X-Bifrost-Node": "thor"})
        result = verify_node_token(handler, config)
        self.assertEqual(result, "thor")
        handler.send_response.assert_not_called()

    def test_invalid_token(self):
        config = {"mesh": {"auth_token": "correct-token"}}
        handler = _make_handler({"Authorization": "Bearer wrong-token"})
        result = verify_node_token(handler, config)
        self.assertIsNone(result)
        handler.send_response.assert_called_with(401)

    def test_missing_header(self):
        config = {"mesh": {"auth_token": "some-token"}}
        handler = _make_handler({})
        result = verify_node_token(handler, config)
        self.assertIsNone(result)
        handler.send_response.assert_called_with(401)

    def test_wrong_scheme(self):
        config = {"mesh": {"auth_token": "some-token"}}
        handler = _make_handler({"Authorization": "Basic dXNlcjpwYXNz"})
        result = verify_node_token(handler, config)
        self.assertIsNone(result)
        handler.send_response.assert_called_with(401)

    def test_no_config_warning_mode(self):
        """No token in config → warning mode, allows through."""
        config = {}
        handler = _make_handler({})
        result = verify_node_token(handler, config)
        self.assertIsNotNone(result)
        self.assertIn("no-auth", result)
        handler.send_response.assert_not_called()

    def test_placeholder_token_rejected(self):
        """Placeholder token should be rejected."""
        config = {"mesh": {"auth_token": "change-me-to-a-long-random-string"}}
        handler = _make_handler({"Authorization": "Bearer change-me-to-a-long-random-string"})
        result = verify_node_token(handler, config)
        self.assertIsNone(result)
        handler.send_response.assert_called_with(401)

    def test_v1_config_fallback(self):
        """Should read from flat 'mesh_auth_token' key (V1 format)."""
        config = {"mesh_auth_token": "v1-token-abc"}
        handler = _make_handler({"Authorization": "Bearer v1-token-abc"})
        result = verify_node_token(handler, config)
        self.assertIsNotNone(result)

    def test_timing_safe_comparison(self):
        """Verify we don't short-circuit on partial match."""
        config = {"mesh": {"auth_token": "a" * 64}}
        handler = _make_handler({"Authorization": "Bearer " + "a" * 63 + "b"})
        result = verify_node_token(handler, config)
        self.assertIsNone(result)


class TestVerifyDashboardKey(unittest.TestCase):
    """Tests for dashboard API key verification."""

    def test_valid_key(self):
        config = {"dashboard": {"auth_key": "dash-key-xyz"}}
        handler = _make_handler({"X-Dashboard-Key": "dash-key-xyz"})
        self.assertTrue(verify_dashboard_key(handler, config))

    def test_invalid_key(self):
        config = {"dashboard": {"auth_key": "correct-key"}}
        handler = _make_handler({"X-Dashboard-Key": "wrong-key"})
        self.assertFalse(verify_dashboard_key(handler, config))
        handler.send_response.assert_called_with(401)

    def test_missing_key(self):
        config = {"dashboard": {"auth_key": "some-key"}}
        handler = _make_handler({})
        self.assertFalse(verify_dashboard_key(handler, config))

    def test_no_config_warning_mode(self):
        config = {}
        handler = _make_handler({})
        self.assertTrue(verify_dashboard_key(handler, config))

    def test_localhost_bypass(self):
        config = {"dashboard": {"auth_key": "some-key", "allow_localhost": True}}
        handler = _make_handler({}, client_ip="127.0.0.1")
        self.assertTrue(verify_dashboard_key(handler, config))

    def test_localhost_bypass_disabled(self):
        config = {"dashboard": {"auth_key": "some-key", "allow_localhost": False}}
        handler = _make_handler({}, client_ip="127.0.0.1")
        self.assertFalse(verify_dashboard_key(handler, config))

    def test_placeholder_key_rejected(self):
        config = {"dashboard": {"auth_key": "change-me-dashboard-key"}}
        handler = _make_handler({"X-Dashboard-Key": "change-me-dashboard-key"})
        self.assertFalse(verify_dashboard_key(handler, config))


class TestRequireAuth(unittest.TestCase):
    """Tests for the combined auth gate."""

    def test_node_auth_passes(self):
        config = {"mesh": {"auth_token": "token-123"}}
        handler = _make_handler({"Authorization": "Bearer token-123"})
        self.assertTrue(require_auth(handler, config, allow_node=True, allow_dashboard=False))

    def test_dashboard_auth_passes(self):
        config = {"dashboard": {"auth_key": "key-456"}}
        handler = _make_handler({"X-Dashboard-Key": "key-456"})
        self.assertTrue(require_auth(handler, config, allow_node=False, allow_dashboard=True))

    def test_no_headers_with_config_rejects(self):
        config = {"mesh": {"auth_token": "token"}, "dashboard": {"auth_key": "key"}}
        handler = _make_handler({})
        self.assertFalse(require_auth(handler, config))

    def test_no_config_warning_mode_allows(self):
        config = {}
        handler = _make_handler({})
        self.assertTrue(require_auth(handler, config))


class TestSanitizePath(unittest.TestCase):
    """Tests for path traversal prevention."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        # Create some test files
        (self.root / "docs").mkdir()
        (self.root / "docs" / "readme.md").write_text("hello")
        (self.root / "secret.txt").write_text("secret")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)

    def test_valid_relative_path(self):
        result = sanitize_path("docs/readme.md", self.root)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "readme.md")

    def test_traversal_blocked(self):
        result = sanitize_path("../../../etc/passwd", self.root)
        self.assertIsNone(result)

    def test_double_dot_in_middle(self):
        result = sanitize_path("docs/../../../etc/shadow", self.root)
        self.assertIsNone(result)

    def test_absolute_path_outside(self):
        result = sanitize_path("/etc/passwd", self.root)
        self.assertIsNone(result)

    def test_empty_path(self):
        result = sanitize_path("", self.root)
        self.assertIsNone(result)

    def test_root_itself(self):
        """Requesting the root itself should be allowed."""
        result = sanitize_path(".", self.root)
        # "." resolves to root which is allowed
        self.assertIsNotNone(result)

    def test_symlink_escape(self):
        """Symlinks that escape the root should be blocked."""
        link = self.root / "evil_link"
        try:
            link.symlink_to("/etc")
            result = sanitize_path("evil_link/passwd", self.root)
            self.assertIsNone(result)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

    def test_backslash_traversal(self):
        result = sanitize_path("..\\..\\etc\\passwd", self.root)
        self.assertIsNone(result)

    def test_url_encoded_not_decoded(self):
        """Raw %2e%2e should not bypass (Path doesn't URL-decode)."""
        result = sanitize_path("%2e%2e/%2e%2e/etc/passwd", self.root)
        # This should either be None or resolve to a nonexistent file
        # inside root (which is fine — it just won't exist)
        if result is not None:
            self.assertTrue(str(result).startswith(str(self.root.resolve())))


class TestValidateModelId(unittest.TestCase):
    """Tests for model ID validation."""

    def test_valid_ids(self):
        valid = [
            "llama/Qwen3.5-35B-A3B-8bit",
            "nvidia/z-ai/glm-5",
            "nvidia/moonshotai/kimi-k2.5",
            "qwen3.5:9b",
            "nomic-embed-text",
        ]
        for model_id in valid:
            self.assertTrue(validate_model_id(model_id),
                           f"Should be valid: {model_id}")

    def test_invalid_ids(self):
        invalid = [
            "",                          # empty
            "foo; rm -rf /",             # shell injection
            "model$(whoami)",            # command substitution
            "a" * 200,                   # too long
            "model\nid",                 # newline
            "model`id`",                 # backticks
        ]
        for model_id in invalid:
            self.assertFalse(validate_model_id(model_id),
                            f"Should be invalid: {model_id!r}")


class TestValidateRegexPattern(unittest.TestCase):
    """Tests for antibody regex pattern validation."""

    def test_valid_pattern(self):
        self.assertIsNone(validate_regex_pattern(r"(?i)ignore\s+previous"))

    def test_empty_pattern(self):
        self.assertIsNotNone(validate_regex_pattern(""))

    def test_too_long(self):
        self.assertIsNotNone(validate_regex_pattern("a" * 300))

    def test_invalid_regex(self):
        self.assertIsNotNone(validate_regex_pattern("[invalid"))

    def test_redos_pattern(self):
        """Catastrophic backtracking pattern should be blocked."""
        result = validate_regex_pattern("(a+)+$")
        self.assertIsNotNone(result)
        self.assertIn("ReDoS", result)


class TestPlaceholderDetection(unittest.TestCase):
    """Tests for placeholder token detection."""

    def test_known_placeholders(self):
        self.assertTrue(_is_placeholder("change-me-to-a-long-random-string"))
        self.assertTrue(_is_placeholder("change-me-dashboard-key"))
        self.assertTrue(_is_placeholder(""))
        self.assertTrue(_is_placeholder(None))

    def test_real_tokens(self):
        self.assertFalse(_is_placeholder("a3f8b2c1d4e5f6789012345678901234"))
        self.assertFalse(_is_placeholder("my-actual-secret-key-2026"))


if __name__ == "__main__":
    unittest.main()

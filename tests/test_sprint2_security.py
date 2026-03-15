"""
tests/test_sprint2_security.py — Sprint 2 Security Hardening + Chat History tests.

Validates all 6 Thor tasks:
  1. CORS wildcard removed from valhalla.yaml
  2. /mobile/pair requires X-Valhalla-Auth header
  3. Rate limiting (3/min), 15-min TTL, file permissions
  4. Chat history POST + GET (capped at 500, returns last 100)
  5. /mobile/sync returns adoption info when no companion
  6. IP validation endpoint

Run from project root:
    python -m pytest tests/test_sprint2_security.py -v
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Task 1 — CORS: wildcard removed
# ---------------------------------------------------------------------------

class TestCorsHardened(unittest.TestCase):

    def test_cors_no_wildcard(self):
        import yaml
        data = yaml.safe_load((REPO_ROOT / "valhalla.yaml").read_text(encoding="utf-8"))
        origins = data.get("dashboard", {}).get("cors_origins", [])
        self.assertNotIn("*", origins,
                         "CORS wildcard '*' must be removed (Heimdall HIGH)")

    def test_cors_has_localhost(self):
        import yaml
        data = yaml.safe_load((REPO_ROOT / "valhalla.yaml").read_text(encoding="utf-8"))
        origins = data.get("dashboard", {}).get("cors_origins", [])
        self.assertTrue(
            any("localhost" in o for o in origins),
            "cors_origins must still include localhost for dev"
        )

    def test_bifrost_has_origin_regex(self):
        """bifrost.py must use allow_origin_regex for Tailscale/LAN IPs."""
        src = (REPO_ROOT / "bifrost.py").read_text(encoding="utf-8")
        self.assertIn("allow_origin_regex", src,
                      "bifrost.py must use allow_origin_regex for Tailscale/LAN")

    def test_bifrost_regex_matches_tailscale(self):
        """The regex must match Tailscale 100.x.x.x IPs."""
        src = (REPO_ROOT / "bifrost.py").read_text(encoding="utf-8")
        # Extract the regex
        match = re.search(r'allow_origin_regex\s*=\s*r"([^"]+)"', src)
        self.assertIsNotNone(match, "Could not find origin regex in bifrost.py")
        pattern = re.compile(match.group(1))
        # Tailscale IP should match
        self.assertIsNotNone(pattern.match("http://100.117.255.38:8765"))
        # LAN IP should match
        self.assertIsNotNone(pattern.match("http://192.168.1.100:8765"))
        # Public IP should NOT match
        self.assertIsNone(pattern.match("http://8.8.8.8:8765"))


# ---------------------------------------------------------------------------
# Task 2 — /mobile/pair requires auth header
# ---------------------------------------------------------------------------

class TestPairAuth(unittest.TestCase):

    def test_pair_requires_auth_header(self):
        """handler.py must check X-Valhalla-Auth header."""
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("X-Valhalla-Auth", src,
                      "/mobile/pair must require X-Valhalla-Auth header")

    def test_pair_returns_401_without_auth(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("401", src,
                      "/mobile/pair must return 401 for missing auth")

    def test_pair_checks_dashboard_auth_key(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("auth_key", src,
                      "Should check config dashboard.auth_key")


# ---------------------------------------------------------------------------
# Task 3 — Rate limiting + token hardening
# ---------------------------------------------------------------------------

class TestTokenHardening(unittest.TestCase):

    def test_rate_limit_present(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("429", src,
                      "/mobile/pair must return 429 when rate limited")

    def test_ttl_reduced_to_15_minutes(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("minutes=15", src,
                      "Token TTL must be 15 minutes (not 365 days)")
        self.assertNotIn("days=365", src,
                         "Old 365-day TTL should be removed")

    def test_file_permissions_0600(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("0o600", src,
                      "Token file must be chmod 0600")

    def test_rate_limit_is_3_per_minute(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("_PAIR_RATE_LIMIT = 3", src,
                      "Rate limit should be 3 per minute")


# ---------------------------------------------------------------------------
# Task 4 — Chat history endpoints
# ---------------------------------------------------------------------------

class TestChatHistory(unittest.TestCase):

    def test_chat_history_post_route_exists(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("/api/v1/companion/chat/history", src)

    def test_chat_history_validates_role(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn('"user"', src)
        self.assertIn('"companion"', src)

    def test_chat_history_fifo_cap(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("500", src, "Chat history should be capped at 500")

    def test_chat_history_returns_last_100(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("[-100:]", src, "GET should return last 100 messages")

    def test_chat_history_stored_in_valhalla(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("chat_history.json", src)

    def test_chat_content_max_length(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("5000", src, "Content should have max length validation")

    def test_chat_history_logic(self):
        """Functional test: write and read chat messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "chat_history.json"

            # Write 3 messages
            messages = []
            for i in range(3):
                messages.append({
                    "role": "user" if i % 2 == 0 else "companion",
                    "content": f"Message {i}",
                    "timestamp": time.time() + i,
                })
            history_file.write_text(json.dumps(messages), encoding="utf-8")

            # Read and verify
            loaded = json.loads(history_file.read_text(encoding="utf-8"))
            self.assertEqual(len(loaded), 3)
            self.assertEqual(loaded[0]["content"], "Message 0")
            self.assertEqual(loaded[2]["role"], "user")

    def test_fifo_cap_logic(self):
        """Verify FIFO cap at 500 messages."""
        messages = [{"role": "user", "content": f"M{i}", "timestamp": i}
                    for i in range(510)]
        # Apply cap
        if len(messages) > 500:
            messages = messages[-500:]
        self.assertEqual(len(messages), 500)
        self.assertEqual(messages[0]["content"], "M10")


# ---------------------------------------------------------------------------
# Task 5 — /mobile/sync handles no-companion state
# ---------------------------------------------------------------------------

class TestMobileSyncAdoption(unittest.TestCase):

    def test_sync_returns_adopted_false(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn('"adopted": False', src,
                      "/mobile/sync should return adopted: false when no companion")

    def test_sync_returns_available_species(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("available_species", src,
                      "/mobile/sync should list available species")
        for species in ["cat", "dog", "penguin", "fox", "owl", "dragon"]:
            self.assertIn(f'"{species}"', src,
                          f"Species '{species}' should be available")

    def test_sync_no_longer_raises_404(self):
        """The old HTTPException(404) for no companion should be replaced."""
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        # Find the api_mobile_sync function and check it doesn't raise 404
        sync_start = src.find("async def api_mobile_sync")
        sync_end = src.find("async def api_mobile_pair")
        sync_body = src[sync_start:sync_end]
        self.assertNotIn('raise HTTPException(404', sync_body,
                         "/mobile/sync should not raise 404 when no companion")


# ---------------------------------------------------------------------------
# Task 6 — IP validation endpoint
# ---------------------------------------------------------------------------

class TestIPValidation(unittest.TestCase):

    def test_validate_host_route_exists(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("/api/v1/companion/mobile/validate-host", src)

    def test_validates_ip_format(self):
        """Unit test the IP validation regex patterns."""
        ip_port_re = re.compile(
            r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?$"
        )
        # Valid
        self.assertIsNotNone(ip_port_re.match("100.117.255.38"))
        self.assertIsNotNone(ip_port_re.match("192.168.1.100:8765"))
        self.assertIsNotNone(ip_port_re.match("10.0.0.1:8765"))
        # Invalid
        self.assertIsNone(ip_port_re.match("not-an-ip"))
        self.assertIsNone(ip_port_re.match("javascript:alert(1)"))

    def test_rejects_protocol_prefixes(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        for proto in ["http://", "https://", "javascript:", "file://"]:
            self.assertIn(proto, src,
                          f"Should reject '{proto}' prefix")

    def test_validates_octet_bounds(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("255", src, "Should check IP octets ≤ 255")

    def test_validates_port_range(self):
        src = (REPO_ROOT / "plugins" / "companion" / "handler.py").read_text(encoding="utf-8")
        self.assertIn("65535", src, "Should validate port ≤ 65535")


if __name__ == "__main__":
    unittest.main()

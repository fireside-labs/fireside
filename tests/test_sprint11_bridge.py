"""
tests/test_sprint11_bridge.py — Sprint 11: Connection Choice / Tailscale Bridge

Validates Thor's 3 tasks:
  1. Setup bridge scripts (.sh + .ps1)
  2. GET /api/v1/network/status
  3. Bifrost 0.0.0.0 binding + Tailscale CORS

Run:  python -m pytest tests/test_sprint11_bridge.py -v
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
# Task 1 — Setup Bridge Scripts
# ---------------------------------------------------------------------------

class TestSetupBridgeScripts(unittest.TestCase):

    def test_sh_script_exists(self):
        self.assertTrue((REPO_ROOT / "scripts" / "setup_bridge.sh").exists())

    def test_ps1_script_exists(self):
        self.assertTrue((REPO_ROOT / "scripts" / "setup_bridge.ps1").exists())

    def test_sh_installs_tailscale(self):
        src = _read("scripts/setup_bridge.sh")
        self.assertIn("tailscale", src.lower())

    def test_sh_tailscale_up(self):
        src = _read("scripts/setup_bridge.sh")
        self.assertIn("tailscale up", src)

    def test_sh_authkey_support(self):
        src = _read("scripts/setup_bridge.sh")
        self.assertIn("TAILSCALE_AUTHKEY", src)

    def test_sh_displays_ips(self):
        src = _read("scripts/setup_bridge.sh")
        self.assertIn("tailscale ip", src)

    def test_ps1_installs_tailscale(self):
        src = _read("scripts/setup_bridge.ps1")
        self.assertIn("Tailscale", src)

    def test_ps1_tailscale_up(self):
        src = _read("scripts/setup_bridge.ps1")
        self.assertIn("tailscale up", src)

    def test_ps1_authkey_support(self):
        src = _read("scripts/setup_bridge.ps1")
        self.assertIn("TAILSCALE_AUTHKEY", src)

    def test_ps1_displays_ips(self):
        src = _read("scripts/setup_bridge.ps1")
        self.assertIn("tailscale ip", src)

    def test_sh_hostname_fireside(self):
        src = _read("scripts/setup_bridge.sh")
        self.assertIn("fireside-", src)

    def test_ps1_hostname_fireside(self):
        src = _read("scripts/setup_bridge.ps1")
        self.assertIn("fireside-", src)


# ---------------------------------------------------------------------------
# Task 2 — Network Status API
# ---------------------------------------------------------------------------

class TestNetworkStatusAPI(unittest.TestCase):

    def test_network_status_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/network/status", src)

    def test_get_method(self):
        src = _read("plugins/companion/handler.py")
        idx = src.find("/api/v1/network/status")
        before = src[max(0, idx - 200):idx]
        self.assertIn(".get(", before)

    def test_returns_local_ip(self):
        src = _read("plugins/companion/handler.py")
        status_start = src.find("def api_network_status")
        body = src[status_start:status_start + 2000]
        self.assertIn('"local_ip"', body)

    def test_returns_tailscale_ip(self):
        src = _read("plugins/companion/handler.py")
        status_start = src.find("def api_network_status")
        body = src[status_start:status_start + 2000]
        self.assertIn('"tailscale_ip"', body)

    def test_returns_bridge_active(self):
        src = _read("plugins/companion/handler.py")
        status_start = src.find("def api_network_status")
        body = src[status_start:status_start + 2000]
        self.assertIn('"bridge_active"', body)

    def test_runs_tailscale_ip_command(self):
        src = _read("plugins/companion/handler.py")
        status_start = src.find("def api_network_status")
        body = src[status_start:status_start + 2000]
        self.assertIn("tailscale", body)

    def test_handles_tailscale_not_installed(self):
        src = _read("plugins/companion/handler.py")
        status_start = src.find("def api_network_status")
        body = src[status_start:status_start + 2000]
        self.assertIn("FileNotFoundError", body)


# ---------------------------------------------------------------------------
# Task 3 — Bifrost Listener
# ---------------------------------------------------------------------------

class TestBifrostListener(unittest.TestCase):

    def test_binds_to_all_interfaces(self):
        src = _read("bifrost.py")
        self.assertIn('0.0.0.0', src)

    def test_tailscale_cors_regex(self):
        src = _read("bifrost.py")
        self.assertIn("100\\.", src)

    def test_local_network_cors(self):
        src = _read("bifrost.py")
        self.assertIn("192\\.168\\.", src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint11Regression(unittest.TestCase):

    def test_guildhall_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/guildhall/agents", src)

    def test_agent_profile_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/agent/profile", src)

    def test_query_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/query", src)

    def test_waitlist_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/waitlist", src)


if __name__ == "__main__":
    unittest.main()

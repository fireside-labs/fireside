"""
tests/test_sprint20_lessismore.py — Sprint 20: Less is More

Thor T1: No backend changes needed.
All existing API endpoints must remain intact — sidebar rearrangement
is frontend-only. This file confirms no regressions.

Run:  python -m pytest tests/test_sprint20_lessismore.py -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent

def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class TestAllEndpointsPreserved(unittest.TestCase):
    """All API endpoints must remain (pages are moving, not deleting)."""

    def test_chat_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/chat"', src)

    def test_nodes_endpoint(self):
        """Connected Devices moves to Settings > Advanced, but API stays."""
        src = _read("api/v1.py")
        self.assertIn('"/nodes"', src)

    def test_config_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/config"', src)

    def test_store_plugins_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/plugins"', src)

    def test_store_purchase_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/purchase"', src)

    def test_brains_active_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/active"', src)

    def test_brains_install_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/install"', src)

    def test_brains_download_status_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/download-status"', src)

    def test_status_agent_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/status/agent"', src)

    def test_config_onboarding_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/config/onboarding"', src)

    def test_guildhall_agents_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/guildhall/agents"', src)


class TestSidebarReduction(unittest.TestCase):
    """Verify the sidebar definition exists and is structured."""

    def test_sidebar_file_exists(self):
        sidebar = REPO_ROOT / "dashboard" / "components" / "Sidebar.tsx"
        self.assertTrue(sidebar.is_file())

    def test_sidebar_has_nav_sections(self):
        src = _read("dashboard/components/Sidebar.tsx")
        self.assertIn("NAV_SECTIONS", src)


class TestSettingsComponentExists(unittest.TestCase):

    def test_settings_form_exists(self):
        settings = REPO_ROOT / "dashboard" / "components" / "SettingsForm.tsx"
        self.assertTrue(settings.is_file())


if __name__ == "__main__":
    unittest.main()

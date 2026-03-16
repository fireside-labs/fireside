"""
tests/test_sprint24_makeitreal.py — Sprint 24: Make It Real

No Thor backend tasks this sprint (all bugs are frontend).
Regression tests confirm all backend endpoints remain intact.

Run:  python -m pytest tests/test_sprint24_makeitreal.py -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent

def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class TestAllEndpointsPreserved(unittest.TestCase):

    def test_chat(self):
        self.assertIn('"/chat"', _read("api/v1.py"))

    def test_brains_active(self):
        self.assertIn('"/brains/active"', _read("api/v1.py"))

    def test_brains_install(self):
        self.assertIn('"/brains/install"', _read("api/v1.py"))

    def test_brains_download_status(self):
        self.assertIn('"/brains/download-status"', _read("api/v1.py"))

    def test_status_agent(self):
        self.assertIn('"/status/agent"', _read("api/v1.py"))

    def test_store_plugins(self):
        self.assertIn('"/store/plugins"', _read("api/v1.py"))

    def test_store_purchase(self):
        self.assertIn('"/store/purchase"', _read("api/v1.py"))

    def test_config_onboarding(self):
        self.assertIn('"/config/onboarding"', _read("api/v1.py"))

    def test_guildhall_agents(self):
        self.assertIn('"/guildhall/agents"', _read("api/v1.py"))


class TestTauriCommandsPreserved(unittest.TestCase):

    def test_all_commands_registered(self):
        src = _read("tauri/src-tauri/src/main.rs")
        handler_idx = src.find("generate_handler!")
        handler_block = src[handler_idx:handler_idx + 600]
        for cmd in [
            "get_system_info", "write_config", "start_fireside",
            "get_backend_status", "download_brain", "test_connection",
        ]:
            self.assertIn(cmd, handler_block, f"{cmd} missing from handler")


class TestModelMapping(unittest.TestCase):
    """B3 regression: model mapping must be consistent across backend and Tauri."""

    def test_api_brain_models(self):
        src = _read("api/v1.py")
        self.assertIn("llama-3.1-8b-q6", src)
        self.assertIn("qwen-2.5-35b-q4", src)

    def test_tauri_brain_models(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("llama-3.1-8b-q6", src)
        self.assertIn("qwen-2.5-35b-q4", src)


if __name__ == "__main__":
    unittest.main()

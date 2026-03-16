"""
tests/test_sprint19_alive.py — Sprint 19: Alive

Validates Thor's 2 tasks:
  T1. Agent status API (verified — already done in Sprint 18)
  T2. Brain download endpoint + download status

Run:  python -m pytest tests/test_sprint19_alive.py -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent

def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T1 — Agent status API (Sprint 18 carry-forward)
# ---------------------------------------------------------------------------

class TestAgentStatusCarryForward(unittest.TestCase):

    def test_status_agent_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/status/agent"', src)

    def test_returns_status_field(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn('"status"', body)


# ---------------------------------------------------------------------------
# T2 — Brain download endpoint
# ---------------------------------------------------------------------------

class TestBrainInstallEndpoint(unittest.TestCase):

    def test_brains_install_route(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/install"', src)

    def test_brains_download_status_route(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/download-status"', src)

    def test_brain_models_defined(self):
        src = _read("api/v1.py")
        self.assertIn("_BRAIN_MODELS", src)
        self.assertIn('"fast"', src)
        self.assertIn('"deep"', src)

    def test_fast_brain_model_mapping(self):
        src = _read("api/v1.py")
        self.assertIn("llama-3.1-8b-q6", src)
        self.assertIn("Meta-Llama-3.1-8B-Instruct-Q6_K.gguf", src)

    def test_deep_brain_model_mapping(self):
        src = _read("api/v1.py")
        self.assertIn("qwen-2.5-35b-q4", src)
        self.assertIn("Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf", src)

    def test_unknown_brain_returns_400(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def install_brain")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("400", body)

    def test_already_installed_check(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def install_brain")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("already_installed", body)

    def test_download_state_tracking(self):
        src = _read("api/v1.py")
        self.assertIn("_download_state", src)
        self.assertIn('"downloading"', src)

    def test_direct_http_fallback(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def install_brain")
        body = src[fn_idx:fn_idx + 3000]
        self.assertIn("urllib.request", body)
        self.assertIn("huggingface.co", body)

    def test_huggingface_hub_integration(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def install_brain")
        body = src[fn_idx:fn_idx + 3000]
        self.assertIn("hf_hub_download", body)

    def test_background_thread_download(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def install_brain")
        body = src[fn_idx:fn_idx + 4000]
        self.assertIn("threading.Thread", body)
        self.assertIn("daemon=True", body)

    def test_frontend_calls_backend(self):
        """BrainInstaller.tsx should call POST /brains/install."""
        src = _read("dashboard/components/BrainInstaller.tsx")
        self.assertIn("/api/v1/brains/install", src)
        self.assertIn("model_id", src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint19Regression(unittest.TestCase):

    def test_store_endpoints_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/plugins"', src)
        self.assertIn('"/store/purchase"', src)

    def test_brains_active_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/active"', src)

    def test_chat_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/chat"', src)


if __name__ == "__main__":
    unittest.main()

"""
tests/test_sprint21_finishinstall.py — Sprint 21: Finish the Install

Validates Thor's 2 tasks:
  T1. download_brain Tauri command — downloads GGUF from HuggingFace
  T2. test_connection Tauri command — verifies backend responds

Run:  python -m pytest tests/test_sprint21_finishinstall.py -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent

def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T1 — download_brain Tauri command
# ---------------------------------------------------------------------------

class TestDownloadBrainCommand(unittest.TestCase):

    def test_download_brain_fn_exists(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("fn download_brain", src)

    def test_accepts_model_and_dest(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn download_brain")
        sig = src[fn_idx:fn_idx + 200]
        self.assertIn("model: String", sig)
        self.assertIn("dest: String", sig)

    def test_knows_fast_model(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn download_brain")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("llama-3.1-8b-q6", body)
        self.assertIn("Meta-Llama-3.1-8B-Instruct-Q6_K.gguf", body)

    def test_knows_deep_model(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn download_brain")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("qwen-2.5-35b-q4", body)

    def test_already_installed_check(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn download_brain")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("already_installed", body)

    def test_huggingface_url(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn download_brain")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("huggingface.co", body)

    def test_cross_platform_download(self):
        """Windows uses Invoke-WebRequest, Unix uses curl."""
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn download_brain")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("Invoke-WebRequest", body)
        self.assertIn("curl", body)

    def test_registered_in_handler(self):
        src = _read("tauri/src-tauri/src/main.rs")
        handler_idx = src.find("generate_handler!")
        handler_end = src.find("])", handler_idx)
        handler_block = src[handler_idx:handler_end]
        self.assertIn("download_brain", handler_block)


# ---------------------------------------------------------------------------
# T2 — test_connection Tauri command
# ---------------------------------------------------------------------------

class TestConnectionCommand(unittest.TestCase):

    def test_test_connection_fn_exists(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("fn test_connection", src)

    def test_connects_to_8765(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn test_connection")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("127.0.0.1:8765", body)

    def test_retries_on_failure(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn test_connection")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("max_attempts", body)

    def test_checks_http_health(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn test_connection")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("status/agent", body)

    def test_returns_connected_on_success(self):
        src = _read("tauri/src-tauri/src/main.rs")
        fn_idx = src.find("fn test_connection")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("connected:", body)

    def test_registered_in_handler(self):
        src = _read("tauri/src-tauri/src/main.rs")
        handler_idx = src.find("generate_handler!")
        handler_end = src.find("])", handler_idx)
        handler_block = src[handler_idx:handler_end]
        self.assertIn("test_connection", handler_block)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint21Regression(unittest.TestCase):

    def test_brains_install_api_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/install"', src)

    def test_status_agent_api_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/status/agent"', src)

    def test_existing_commands_preserved(self):
        src = _read("tauri/src-tauri/src/main.rs")
        handler_idx = src.find("generate_handler!")
        handler_block = src[handler_idx:handler_idx + 500]
        for cmd in ["get_system_info", "write_config", "start_fireside", "get_backend_status"]:
            self.assertIn(cmd, handler_block)


if __name__ == "__main__":
    unittest.main()

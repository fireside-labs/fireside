"""
tests/test_sprint14_lastmile.py — Sprint 14: Last Mile Wiring

Validates Thor's 6 tasks:
  T1. Mac unified memory detection in main.rs
  T2. POST /api/v1/chat endpoint in v1.py
  T3. POST /api/v1/brains/install endpoint in v1.py
  T4. GET /api/v1/guildhall/agents endpoint in v1.py
  T5. POST /api/v1/nodes endpoint in v1.py
  T6. API port unification (8765 everywhere)

Run:  python -m pytest tests/test_sprint14_lastmile.py -v
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
# T1 — Mac unified memory detection
# ---------------------------------------------------------------------------

class TestMacVRAM(unittest.TestCase):

    def test_macos_sysctl(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("hw.memsize", src)

    def test_macos_cfg_target(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn('cfg(target_os = "macos")', src)

    def test_linux_nvidia_smi(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("nvidia-smi", src)

    def test_linux_cfg_target(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn('cfg(target_os = "linux")', src)

    def test_no_bare_zero_fallback(self):
        src = _read("tauri/src-tauri/src/main.rs")
        # Verify the old "0.0 // macOS/Linux" comment is gone
        self.assertNotIn("unified memory or nvidia-smi needed", src)


# ---------------------------------------------------------------------------
# T2 — POST /api/v1/chat
# ---------------------------------------------------------------------------

class TestChatEndpoint(unittest.TestCase):

    def test_chat_route(self):
        src = _read("api/v1.py")
        self.assertIn('"/chat"', src)

    def test_post_method(self):
        src = _read("api/v1.py")
        self.assertIn("router.post", src)
        idx = src.find('"/chat"')
        before = src[max(0, idx - 100):idx]
        self.assertIn(".post(", before)

    def test_llama_cpp_proxy(self):
        src = _read("api/v1.py")
        self.assertIn("127.0.0.1:8080/completion", src)

    def test_sse_streaming(self):
        src = _read("api/v1.py")
        chat_idx = src.find("def post_chat")
        body = src[chat_idx:chat_idx + 3000]
        self.assertIn("StreamingResponse", body)

    def test_companion_personality(self):
        src = _read("api/v1.py")
        chat_idx = src.find("def post_chat")
        body = src[chat_idx:chat_idx + 2000]
        self.assertIn("companion_state.json", body)

    def test_chat_request_model(self):
        src = _read("api/v1.py")
        self.assertIn("class ChatRequest", src)


# ---------------------------------------------------------------------------
# T3 — POST /api/v1/brains/install
# ---------------------------------------------------------------------------

class TestBrainsInstall(unittest.TestCase):

    def test_brains_install_route(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/install"', src)

    def test_downloads_to_models_dir(self):
        src = _read("api/v1.py")
        install_idx = src.find("def post_brains_install")
        body = src[install_idx:install_idx + 3000]
        self.assertIn("models", body)

    def test_sse_progress(self):
        src = _read("api/v1.py")
        install_idx = src.find("def post_brains_install")
        body = src[install_idx:install_idx + 3000]
        self.assertIn("downloading", body)
        self.assertIn("percent", body)

    def test_gguf_extension(self):
        src = _read("api/v1.py")
        install_idx = src.find("def post_brains_install")
        body = src[install_idx:install_idx + 3000]
        self.assertIn(".gguf", body)

    def test_error_cleanup(self):
        src = _read("api/v1.py")
        install_idx = src.find("def post_brains_install")
        body = src[install_idx:install_idx + 3000]
        self.assertIn("unlink", body)

    def test_brain_install_request_model(self):
        src = _read("api/v1.py")
        self.assertIn("class BrainInstallRequest", src)


# ---------------------------------------------------------------------------
# T4 — GET /api/v1/guildhall/agents in v1.py
# ---------------------------------------------------------------------------

class TestGuildhallV1(unittest.TestCase):

    def test_guildhall_route_in_v1(self):
        src = _read("api/v1.py")
        self.assertIn('"/guildhall/agents"', src)

    def test_returns_agents_list(self):
        src = _read("api/v1.py")
        gh_idx = src.find("def get_guildhall_agents")
        body = src[gh_idx:gh_idx + 2000]
        self.assertIn('"agents"', body)

    def test_reads_from_config(self):
        src = _read("api/v1.py")
        gh_idx = src.find("def get_guildhall_agents")
        body = src[gh_idx:gh_idx + 2000]
        self.assertIn("_config", body)

    def test_has_ai_and_companion(self):
        src = _read("api/v1.py")
        gh_idx = src.find("def get_guildhall_agents")
        body = src[gh_idx:gh_idx + 2000]
        self.assertIn('"ai"', body)
        self.assertIn('"companion"', body)


# ---------------------------------------------------------------------------
# T5 — POST /api/v1/nodes
# ---------------------------------------------------------------------------

class TestNodeRegistration(unittest.TestCase):

    def test_nodes_post_route(self):
        src = _read("api/v1.py")
        self.assertIn("def register_node", src)

    def test_node_register_request(self):
        src = _read("api/v1.py")
        self.assertIn("class NodeRegisterRequest", src)

    def test_persists_to_config(self):
        src = _read("api/v1.py")
        reg_idx = src.find("def register_node")
        body = src[reg_idx:reg_idx + 2000]
        self.assertIn("valhalla.yaml", body)

    def test_returns_mesh_size(self):
        src = _read("api/v1.py")
        reg_idx = src.find("def register_node")
        body = src[reg_idx:reg_idx + 2000]
        self.assertIn("mesh_size", body)

    def test_conflict_detection(self):
        src = _read("api/v1.py")
        reg_idx = src.find("def register_node")
        body = src[reg_idx:reg_idx + 2000]
        self.assertIn("409", body)


# ---------------------------------------------------------------------------
# T6 — API port unification
# ---------------------------------------------------------------------------

class TestPortUnification(unittest.TestCase):

    def test_api_ts_port_8765(self):
        src = _read("dashboard/lib/api.ts")
        self.assertIn("8765", src)

    def test_no_8766_in_api_base(self):
        src = _read("dashboard/lib/api.ts")
        # Only check the const API_BASE declaration, not usage lines
        for line in src.splitlines():
            if line.strip().startswith("const API_BASE"):
                self.assertNotIn("8766", line)
                self.assertIn("8765", line)
                break

    def test_bifrost_default_8765(self):
        src = _read("bifrost.py")
        self.assertIn("8765", src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint14Regression(unittest.TestCase):

    def test_network_status_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/network/status", src)

    def test_agent_profile_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/agent/profile", src)

    def test_tauri_fireside_branding(self):
        src = _read("tauri/src-tauri/tauri.conf.json")
        self.assertIn("Fireside", src)
        self.assertNotIn('"Valhalla"', src)


if __name__ == "__main__":
    unittest.main()

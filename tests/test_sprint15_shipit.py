"""
tests/test_sprint15_shipit.py — Sprint 15: Ship It

Validates Thor's 4 tasks:
  T1. Backend auto-start from Tauri (setup hook, lifecycle, backend status cmd)
  T2. Verify nvidia-smi VRAM detection (code-level check)
  T3. Store backend endpoints (GET /store/plugins, POST /store/purchase, GET /store/purchases)
  T4. Config onboarding endpoint (GET /config/onboarding)

Run:  python -m pytest tests/test_sprint15_shipit.py -v
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
# T1 — Backend auto-start from Tauri
# ---------------------------------------------------------------------------

class TestBackendAutoStart(unittest.TestCase):

    def test_setup_hook(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn(".setup(", src)

    def test_spawn_backend_fn(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("fn spawn_backend", src)

    def test_backend_state_struct(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("struct BackendState", src)

    def test_restart_on_crash(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("restart_count", src)
        self.assertIn("max_restarts", src)

    def test_exit_cleanup(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("RunEvent::Exit", src)
        self.assertIn("kill", src)

    def test_get_backend_status_cmd(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("fn get_backend_status", src)
        self.assertIn("get_backend_status", src)

    def test_backend_status_registered(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("get_backend_status", src)
        # Must be in generate_handler
        handler_idx = src.find("generate_handler!")
        handler_end = src.find("])", handler_idx)
        handler_block = src[handler_idx:handler_end]
        self.assertIn("get_backend_status", handler_block)

    def test_uses_port_8765(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("8765", src)


# ---------------------------------------------------------------------------
# T2 — nvidia-smi VRAM detection verified
# ---------------------------------------------------------------------------

class TestVRAMDetection(unittest.TestCase):

    def test_nvidia_smi_present(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("nvidia-smi", src)

    def test_nvidia_smi_query_memory(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("--query-gpu=name,memory.total", src)

    def test_mb_to_gb_conversion(self):
        src = _read("tauri/src-tauri/src/main.rs")
        # Should divide MB by 1024 to get GB
        self.assertIn("1024.0", src)

    def test_macos_sysctl(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("hw.memsize", src)

    def test_windows_nvidia_first(self):
        """Windows should try nvidia-smi BEFORE WMI fallback."""
        src = _read("tauri/src-tauri/src/main.rs")
        # Find the "let (gpu, vram_gb) = {" block, then the Windows section within it
        vram_let_idx = src.find("let (gpu, vram_gb)")
        self.assertGreater(vram_let_idx, -1, "let (gpu, vram_gb) not found")
        # Within the vram block, nvidia-smi should come before Win32_VideoController
        vram_block = src[vram_let_idx:vram_let_idx + 3000]
        nvidia_pos = vram_block.find("nvidia-smi")
        wmi_pos = vram_block.find("Win32_VideoController")
        self.assertGreater(nvidia_pos, -1, "nvidia-smi not in vram block")
        self.assertGreater(wmi_pos, -1, "WMI not in vram block")
        self.assertLess(nvidia_pos, wmi_pos, "nvidia-smi should come before WMI")


# ---------------------------------------------------------------------------
# T3 — Store backend endpoints
# ---------------------------------------------------------------------------

class TestStoreBackend(unittest.TestCase):

    def test_store_plugins_route(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/plugins"', src)

    def test_store_purchase_route(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/purchase"', src)

    def test_store_purchases_route(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/purchases"', src)

    def test_purchase_request_model(self):
        src = _read("api/v1.py")
        self.assertIn("class PurchaseRequest", src)

    def test_local_json_registry(self):
        src = _read("api/v1.py")
        self.assertIn("store_registry.json", src)

    def test_seed_defaults(self):
        src = _read("api/v1.py")
        # Should seed with at least a few default plugins
        self.assertIn("daily-brief", src)
        self.assertIn("git-watcher", src)

    def test_duplicate_purchase_prevented(self):
        src = _read("api/v1.py")
        store_idx = src.find("def store_purchase")
        body = src[store_idx:store_idx + 1500]
        self.assertIn("409", body)

    def test_plugin_not_found_404(self):
        src = _read("api/v1.py")
        store_idx = src.find("def store_purchase")
        body = src[store_idx:store_idx + 1500]
        self.assertIn("404", body)

    def test_purchased_flag(self):
        src = _read("api/v1.py")
        self.assertIn("purchased", src)


# ---------------------------------------------------------------------------
# T4 — Config onboarding endpoint
# ---------------------------------------------------------------------------

class TestConfigOnboarding(unittest.TestCase):

    def test_config_onboarding_route(self):
        src = _read("api/v1.py")
        self.assertIn('"/config/onboarding"', src)

    def test_returns_agent_name(self):
        src = _read("api/v1.py")
        ob_idx = src.find("def get_config_onboarding")
        body = src[ob_idx:ob_idx + 2000]
        self.assertIn("agent_name", body)

    def test_returns_companion_name(self):
        src = _read("api/v1.py")
        ob_idx = src.find("def get_config_onboarding")
        body = src[ob_idx:ob_idx + 2000]
        self.assertIn("companion_name", body)

    def test_returns_brain(self):
        src = _read("api/v1.py")
        ob_idx = src.find("def get_config_onboarding")
        body = src[ob_idx:ob_idx + 2000]
        self.assertIn("brain", body)

    def test_reads_onboarding_json(self):
        src = _read("api/v1.py")
        ob_idx = src.find("def get_config_onboarding")
        body = src[ob_idx:ob_idx + 2000]
        self.assertIn("onboarding.json", body)

    def test_reads_from_config(self):
        src = _read("api/v1.py")
        ob_idx = src.find("def get_config_onboarding")
        body = src[ob_idx:ob_idx + 2000]
        self.assertIn("_config", body)

    def test_returns_onboarded_flag(self):
        src = _read("api/v1.py")
        ob_idx = src.find("def get_config_onboarding")
        body = src[ob_idx:ob_idx + 2000]
        self.assertIn("onboarded", body)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint15Regression(unittest.TestCase):

    def test_chat_endpoint_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/chat"', src)

    def test_brains_install_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/install"', src)

    def test_guildhall_agents_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/guildhall/agents"', src)

    def test_port_8765(self):
        src = _read("dashboard/lib/api.ts")
        for line in src.splitlines():
            if line.strip().startswith("const API_BASE"):
                self.assertIn("8765", line)
                break

    def test_fireside_branding(self):
        src = _read("tauri/src-tauri/tauri.conf.json")
        self.assertIn("Fireside", src)


if __name__ == "__main__":
    unittest.main()

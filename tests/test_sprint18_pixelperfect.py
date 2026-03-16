"""
tests/test_sprint18_pixelperfect.py — Sprint 18: Pixel Perfect

Validates Thor's 2 tasks:
  T1. Sprite asset serving (directory exists, CSP configured, README)
  T2. Status effect API (/api/v1/status/agent with state mapping)

Run:  python -m pytest tests/test_sprint18_pixelperfect.py -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent

def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T1 — Sprite asset serving
# ---------------------------------------------------------------------------

class TestSpriteAssetServing(unittest.TestCase):

    def test_sprites_directory_exists(self):
        sprites_dir = REPO_ROOT / "dashboard" / "public" / "sprites"
        self.assertTrue(sprites_dir.is_dir(), "dashboard/public/sprites/ must exist")

    def test_sprites_readme_exists(self):
        readme = REPO_ROOT / "dashboard" / "public" / "sprites" / "README.md"
        self.assertTrue(readme.is_file(), "sprites/README.md must exist")

    def test_readme_documents_structure(self):
        readme = _read("dashboard/public/sprites/README.md")
        self.assertIn("agents/", readme)
        self.assertIn("companions/", readme)
        self.assertIn("effects/", readme)
        self.assertIn("environment/", readme)

    def test_csp_allows_images(self):
        src = _read("tauri/src-tauri/tauri.conf.json")
        self.assertIn("img-src", src)
        self.assertIn("'self'", src)
        self.assertIn("data:", src)
        self.assertIn("blob:", src)

    def test_capabilities_csp_allows_images(self):
        src = _read("tauri/src-tauri/capabilities/main.json")
        self.assertIn("img-src", src)
        self.assertIn("'self'", src)

    def test_readme_mentions_pixelated(self):
        readme = _read("dashboard/public/sprites/README.md")
        self.assertIn("image-rendering: pixelated", readme)

    def test_readme_mentions_sprite_sizes(self):
        readme = _read("dashboard/public/sprites/README.md")
        self.assertIn("48×48", readme)  # agents
        self.assertIn("32×32", readme)  # companions


# ---------------------------------------------------------------------------
# T2 — Status effect API
# ---------------------------------------------------------------------------

class TestStatusEffectAPI(unittest.TestCase):

    def test_status_agent_endpoint_exists(self):
        src = _read("api/v1.py")
        self.assertIn('"/status/agent"', src)

    def test_returns_status_field(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn('"status"', body)

    def test_status_values_documented(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        for status in ["on_a_roll", "idle", "working", "error", "learning"]:
            self.assertIn(status, body)

    def test_returns_cpu_percent(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("cpu_percent", body)

    def test_returns_memory_percent(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("memory_percent", body)

    def test_returns_llm_running(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("llm_running", body)

    def test_returns_uptime(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("uptime_seconds", body)

    def test_uses_psutil(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        self.assertIn("psutil", body)

    def test_detects_llm_processes(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        # Should detect common LLM server processes
        for proc_name in ["llama", "ollama", "vllm", "mlx"]:
            self.assertIn(proc_name, body)

    def test_on_a_roll_threshold(self):
        src = _read("api/v1.py")
        fn_idx = src.find("def get_agent_status")
        body = src[fn_idx:fn_idx + 2000]
        # on_a_roll requires LLM running + high CPU
        self.assertIn("on_a_roll", body)
        self.assertIn("llm_running", body)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint18Regression(unittest.TestCase):

    def test_brains_active_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/active"', src)

    def test_store_plugins_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/plugins"', src)

    def test_chat_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/chat"', src)

    def test_fireside_branding(self):
        src = _read("tauri/src-tauri/tauri.conf.json")
        self.assertIn("Fireside", src)

    def test_mac_linux_gpu_tuple(self):
        """macOS and Linux GPU detection must return (String, f64) tuples."""
        src = _read("tauri/src-tauri/src/main.rs")
        # All 3 platforms should use the same (gpu, vram_gb) tuple
        self.assertIn("let (gpu, vram_gb)", src)
        # macOS branch should return a tuple
        mac_idx = src.find('target_os = "macos"', src.find("let (gpu, vram_gb)"))
        mac_block = src[mac_idx:mac_idx + 1500]
        self.assertIn("(gpu_name, vram)", mac_block)
        # Linux branch should return a tuple
        linux_idx = src.find('target_os = "linux"', mac_idx)
        linux_block = src[linux_idx:linux_idx + 2000]
        self.assertIn("(gpu_name, 0.0)", linux_block)


if __name__ == "__main__":
    unittest.main()

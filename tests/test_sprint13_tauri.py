"""
tests/test_sprint13_tauri.py — Sprint 13: Tauri Commands + Config + Icons

Validates Thor's 4 tasks:
  1. tauri.conf.json rebrand (Valhalla → Fireside)
  2. Rust Tauri commands in main.rs
  3. App icon source in icons/
  4. Cargo.toml with correct name and deps

Run:  python -m pytest tests/test_sprint13_tauri.py -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent
TAURI_DIR = REPO_ROOT / "tauri" / "src-tauri"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Task 1 — tauri.conf.json Rebrand
# ---------------------------------------------------------------------------

class TestTauriConfig(unittest.TestCase):

    def test_config_exists(self):
        self.assertTrue((TAURI_DIR / "tauri.conf.json").exists())

    def test_product_name_fireside(self):
        cfg = json.loads(_read("tauri/src-tauri/tauri.conf.json"))
        self.assertEqual(cfg["productName"], "Fireside")

    def test_identifier(self):
        cfg = json.loads(_read("tauri/src-tauri/tauri.conf.json"))
        self.assertEqual(cfg["identifier"], "ai.fireside.app")

    def test_version(self):
        cfg = json.loads(_read("tauri/src-tauri/tauri.conf.json"))
        self.assertEqual(cfg["version"], "1.0.0")

    def test_app_title(self):
        cfg = json.loads(_read("tauri/src-tauri/tauri.conf.json"))
        # app.title may or may not exist; window title is the key one
        app_title = cfg.get("app", {}).get("title", None)
        if app_title:
            self.assertEqual(app_title, "Fireside")
        # Window title must always have Fireside
        self.assertIn("Fireside", cfg["app"]["windows"][0]["title"])

    def test_window_title(self):
        cfg = json.loads(_read("tauri/src-tauri/tauri.conf.json"))
        self.assertIn("Fireside", cfg["app"]["windows"][0]["title"])

    def test_no_valhalla_references(self):
        src = _read("tauri/src-tauri/tauri.conf.json")
        self.assertNotIn("Valhalla", src)
        self.assertNotIn("valhalla.ai", src)

    def test_updater_endpoint_fireside(self):
        cfg = json.loads(_read("tauri/src-tauri/tauri.conf.json"))
        endpoint = cfg["plugins"]["updater"]["endpoints"][0]
        self.assertIn("getfireside.ai", endpoint)

    def test_csp_includes_8765(self):
        cfg = json.loads(_read("tauri/src-tauri/tauri.conf.json"))
        csp = cfg["app"]["security"]["csp"]
        self.assertIn("8765", csp)


# ---------------------------------------------------------------------------
# Task 2 — Rust Tauri Commands
# ---------------------------------------------------------------------------

class TestRustCommands(unittest.TestCase):

    def test_main_rs_exists(self):
        self.assertTrue((TAURI_DIR / "src" / "main.rs").exists())

    def test_get_system_info(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("get_system_info", src)

    def test_check_python(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("check_python", src)

    def test_check_node(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("check_node", src)

    def test_install_python(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("install_python", src)

    def test_install_node(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("install_node", src)

    def test_clone_repo(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("clone_repo", src)

    def test_install_deps(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("install_deps", src)

    def test_write_config(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("write_config", src)

    def test_start_fireside(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("start_fireside", src)

    def test_tauri_command_attr(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("#[tauri::command]", src)

    def test_generate_handler(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("generate_handler!", src)

    def test_system_info_struct(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("SystemInfo", src)

    def test_fireside_config_struct(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("FiresideConfig", src)

    def test_writes_valhalla_yaml(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("valhalla.yaml", src)

    def test_writes_companion_state(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("companion_state.json", src)

    def test_writes_onboarding(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("onboarding.json", src)

    def test_fireside_branding(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("Fireside", src)


# ---------------------------------------------------------------------------
# Task 3 — App Icons
# ---------------------------------------------------------------------------

class TestAppIcons(unittest.TestCase):

    def test_icons_directory_exists(self):
        self.assertTrue((TAURI_DIR / "icons").exists())

    def test_icon_source_exists(self):
        icons_dir = TAURI_DIR / "icons"
        # At least one icon file should exist
        icon_files = list(icons_dir.glob("*.png"))
        self.assertGreater(len(icon_files), 0)


# ---------------------------------------------------------------------------
# Task 4 — Cargo.toml
# ---------------------------------------------------------------------------

class TestCargoToml(unittest.TestCase):

    def test_cargo_toml_exists(self):
        self.assertTrue((TAURI_DIR / "Cargo.toml").exists())

    def test_name_fireside(self):
        src = _read("tauri/src-tauri/Cargo.toml")
        self.assertIn('name = "fireside"', src)

    def test_tauri_dep(self):
        src = _read("tauri/src-tauri/Cargo.toml")
        self.assertIn("tauri", src)

    def test_tauri_build_dep(self):
        src = _read("tauri/src-tauri/Cargo.toml")
        self.assertIn("tauri-build", src)

    def test_serde_dep(self):
        src = _read("tauri/src-tauri/Cargo.toml")
        self.assertIn("serde", src)

    def test_dirs_dep(self):
        src = _read("tauri/src-tauri/Cargo.toml")
        self.assertIn("dirs", src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint13Regression(unittest.TestCase):

    def test_network_status_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/network/status", src)

    def test_guildhall_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/guildhall/agents", src)

    def test_agent_profile_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/agent/profile", src)


if __name__ == "__main__":
    unittest.main()

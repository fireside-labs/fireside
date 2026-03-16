"""
tests/test_sprint16_polish.py — Sprint 16: Polish & Ship

Validates Thor's 3 tasks:
  T1. Store backend wired to frontend (6 default plugins, purchase flow, history)
  T2. Backend auto-start verification (setup hook, lifecycle, status cmd)
  T3. BrainPicker reads from localStorage + InstallerWizard writes fireside_brain

Run:  python -m pytest tests/test_sprint16_polish.py -v
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
# T1 — Store backend wired (6 default plugins)
# ---------------------------------------------------------------------------

class TestStoreWired(unittest.TestCase):

    def test_six_default_plugins(self):
        src = _read("api/v1.py")
        # Count plugin id definitions in the defaults list
        for pid in ["daily-brief", "git-watcher", "backup-sync",
                     "voice-interface", "prompt-optimizer", "cost-tracker"]:
            self.assertIn(f'"{pid}"', src)

    def test_store_plugins_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/plugins"', src)

    def test_store_purchase_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/purchase"', src)

    def test_store_purchases_endpoint(self):
        src = _read("api/v1.py")
        self.assertIn('"/store/purchases"', src)

    def test_purchase_persists_to_json(self):
        src = _read("api/v1.py")
        self.assertIn("purchases.json", src)

    def test_purchased_flag_returned(self):
        src = _read("api/v1.py")
        self.assertIn('"purchased"', src)

    def test_404_for_missing_plugin(self):
        src = _read("api/v1.py")
        store_idx = src.find("def store_purchase")
        body = src[store_idx:store_idx + 1500]
        self.assertIn("404", body)

    def test_409_for_duplicate(self):
        src = _read("api/v1.py")
        store_idx = src.find("def store_purchase")
        body = src[store_idx:store_idx + 1500]
        self.assertIn("409", body)


# ---------------------------------------------------------------------------
# T2 — Backend auto-start verification
# ---------------------------------------------------------------------------

class TestAutoStartVerification(unittest.TestCase):

    def test_setup_hook_exists(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn(".setup(", src)

    def test_spawn_backend(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("fn spawn_backend", src)

    def test_restart_on_crash(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("max_restarts", src)

    def test_exit_cleanup(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("RunEvent::Exit", src)

    def test_backend_status_command(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("fn get_backend_status", src)


# ---------------------------------------------------------------------------
# T3 — BrainPicker matches onboarding
# ---------------------------------------------------------------------------

class TestBrainPickerMatch(unittest.TestCase):

    def test_installer_writes_fireside_brain(self):
        src = _read("dashboard/components/InstallerWizard.tsx")
        self.assertIn("fireside_brain", src)

    def test_settings_reads_fireside_brain(self):
        src = _read("dashboard/components/SettingsForm.tsx")
        self.assertIn("fireside_brain", src)

    def test_brainpicker_has_smart_and_fast(self):
        src = _read("dashboard/components/BrainPicker.tsx")
        self.assertIn("Smart & Fast", src)

    def test_brainpicker_has_deep_thinker(self):
        src = _read("dashboard/components/BrainPicker.tsx")
        self.assertIn("Deep Thinker", src)

    def test_brainpicker_has_cloud_expert(self):
        src = _read("dashboard/components/BrainPicker.tsx")
        self.assertIn("Cloud Expert", src)

    def test_brainpicker_ids_match_installer(self):
        """BrainPicker IDs must match what InstallerWizard writes."""
        bp_src = _read("dashboard/components/BrainPicker.tsx")
        iw_src = _read("dashboard/components/InstallerWizard.tsx")
        # BrainPicker uses "fast" and "deep" IDs
        self.assertIn('"fast"', bp_src)
        self.assertIn('"deep"', bp_src)
        # InstallerWizard writes one of those IDs
        self.assertIn('"deep"', iw_src)
        self.assertIn('"fast"', iw_src)

    def test_settings_initializes_from_localstorage(self):
        src = _read("dashboard/components/SettingsForm.tsx")
        # Should use localStorage.getItem, not hardcoded "fast"
        self.assertIn('localStorage.getItem("fireside_brain")', src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint16Regression(unittest.TestCase):

    def test_chat_endpoint_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/chat"', src)

    def test_brains_install_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/install"', src)

    def test_config_onboarding_preserved(self):
        src = _read("api/v1.py")
        self.assertIn('"/config/onboarding"', src)

    def test_fireside_branding(self):
        src = _read("tauri/src-tauri/tauri.conf.json")
        self.assertIn("Fireside", src)

    def test_port_8765(self):
        src = _read("dashboard/lib/api.ts")
        for line in src.splitlines():
            if line.strip().startswith("const API_BASE"):
                self.assertIn("8765", line)
                break

    def test_installer_writes_companion_json(self):
        src = _read("dashboard/components/InstallerWizard.tsx")
        self.assertIn("fireside_companion", src)

    def test_no_odin_in_mock_data(self):
        src = _read("dashboard/lib/api.ts")
        # Check that mock node names and config don't contain "odin"
        # (type names like ValhallaEvent are fine — just no user-facing Odin references)
        for line in src.splitlines():
            lower = line.lower().strip()
            # Skip type definitions, imports, interface lines
            if any(kw in lower for kw in ["interface ", "type ", "export ", "import "]):
                continue
            # Check user-facing content: string literals containing "odin"
            if 'name: "odin"' in lower or 'node_name: "odin"' in lower:
                self.fail(f"Found 'odin' in mock data: {line.strip()}")


if __name__ == "__main__":
    unittest.main()

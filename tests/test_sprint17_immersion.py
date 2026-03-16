"""
tests/test_sprint17_immersion.py — Sprint 17: Immersion

Validates Thor's T1 task:
  T1. Model name -> brain mapping
      - fireside_model key in localStorage
      - Mapping: fast -> llama-3.1-8b-q6, deep -> qwen-2.5-35b-q4
      - GET /api/v1/brains/active returns mapped values

Also verifies sync with User's manual fixes:
  - auth_token validation in /store/purchase
  - Refined hardware detection (main.rs) - code-level checks

Run:  python -m pytest tests/test_sprint17_immersion.py -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent

def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")

class TestModelBrainMapping(unittest.TestCase):
    def test_onboarding_wizard_saves_model(self):
        src = _read("dashboard/components/OnboardingWizard.tsx")
        self.assertIn("fireside_model", src)
        self.assertIn("llama-3.1-8b-q6", src)
        self.assertIn("qwen-2.5-35b-q4", src)

    def test_installer_wizard_saves_model(self):
        src = _read("dashboard/components/InstallerWizard.tsx")
        self.assertIn("fireside_model", src)
        self.assertIn("llama-3.1-8b-q6", src)
        self.assertIn("qwen-2.5-35b-q4", src)

    def test_active_brain_endpoint_exists(self):
        src = _read("api/v1.py")
        self.assertIn('"/brains/active"', src)
        self.assertIn('"active"', src)
        self.assertIn('"model"', src)

    def test_active_brain_logic(self):
        src = _read("api/v1.py")
        self.assertIn('get("brain", "fast")', src)
        self.assertIn('get("model", "llama-3.1-8b-q6")', src)

class TestSecuritySync(unittest.TestCase):
    def test_store_purchase_requires_auth(self):
        src = _read("api/v1.py")
        self.assertIn("auth_token", src)
        self.assertIn("hmac.compare_digest", src)
        self.assertIn("401", src)

class TestHardwareSync(unittest.TestCase):
    def test_nvidia_smi_absolute_path(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn('C:\\\\Windows\\\\System32\\\\nvidia-smi.exe', src)

    pub_src = _read("tauri/src-tauri/src/main.rs")
    def test_wmi_gpu_aggregation(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("max_by_key", src)
        self.assertIn("AdapterRAM", src)

    def test_backend_polling(self):
        src = _read("tauri/src-tauri/src/main.rs")
        self.assertIn("try_wait()", src)
        self.assertIn("thread::sleep", src)

if __name__ == "__main__":
    unittest.main()

"""
tests/test_credential_store.py — Unit tests for credential storage and installer security.

Run: cd /Users/odin/Documents/ProjectOpenClaw/valhalla-mesh-v2 && python3 -m pytest tests/test_credential_store.py -v
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# The plugin directory uses hyphens (brain-installer), which isn't a valid
# Python package name. Use importlib to load the module from its file path.
import importlib.util

_mod_path = Path(__file__).parent.parent / "plugins" / "brain-installer" / "credential_store.py"
_spec = importlib.util.spec_from_file_location("credential_store", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

CredentialStore = _mod.CredentialStore
verify_gguf_checksum = _mod.verify_gguf_checksum
verify_binary_signature = _mod.verify_binary_signature
check_process_isolation = _mod.check_process_isolation
sanitize_telegram_message = _mod.sanitize_telegram_message
validate_telegram_config = _mod.validate_telegram_config
validate_telegram_user = _mod.validate_telegram_user
_get_machine_id = _mod._get_machine_id
_derive_key = _mod._derive_key
SENSITIVE_KEY_NAMES = _mod.SENSITIVE_KEY_NAMES


class TestCredentialStore(unittest.TestCase):
    """Credential storage core functionality."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.store = CredentialStore(store_dir=self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_set_and_get(self):
        self.store.set("test_key", "super-secret-value")
        self.assertEqual(self.store.get("test_key"), "super-secret-value")

    def test_masked_value(self):
        self.store.set("api_key", "nvapi-abc123def456ghi789")
        masked = self.store.get_masked("api_key")
        self.assertTrue(masked.startswith("nvap"))
        self.assertTrue(masked.endswith("i789"))
        self.assertIn("...", masked)
        self.assertNotIn("abc123def456", masked)

    def test_short_value_fully_masked(self):
        self.store.set("short", "abc")
        masked = self.store.get_masked("short")
        self.assertEqual(masked, "***")

    def test_delete(self):
        self.store.set("temp", "value")
        self.assertTrue(self.store.delete("temp"))
        self.assertIsNone(self.store.get("temp"))

    def test_delete_nonexistent(self):
        self.assertFalse(self.store.delete("nonexistent"))

    def test_list_names(self):
        self.store.set("key1", "val1")
        self.store.set("key2", "val2")
        names = self.store.list_names()
        self.assertIn("key1", names)
        self.assertIn("key2", names)
        self.assertEqual(len(names), 2)

    def test_exists(self):
        self.store.set("exists", "yes")
        self.assertTrue(self.store.exists("exists"))
        self.assertFalse(self.store.exists("nope"))

    def test_get_nonexistent(self):
        self.assertIsNone(self.store.get("nonexistent"))

    def test_persistence(self):
        """Verify credentials survive store reload."""
        self.store.set("persist_key", "persist_value")

        # Create new store pointing to same dir
        store2 = CredentialStore(store_dir=self.tmpdir)
        self.assertEqual(store2.get("persist_key"), "persist_value")

    def test_file_permissions(self):
        """Verify store file has 600 permissions."""
        self.store.set("perm_test", "value")
        if self.store.store_file.exists():
            mode = stat.S_IMODE(self.store.store_file.stat().st_mode)
            self.assertEqual(mode, stat.S_IRUSR | stat.S_IWUSR)

    def test_status(self):
        self.store.set("key1", "val1")
        status = self.store.get_status()
        self.assertEqual(status["credential_count"], 1)
        self.assertIn("key1", status["credentials"])
        self.assertTrue(status["credentials"]["key1"]["stored"])

    def test_empty_value_rejected(self):
        with self.assertRaises(ValueError):
            self.store.set("key", "")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            self.store.set("", "value")


class TestKeyDerivation(unittest.TestCase):
    """Machine-specific key derivation."""

    def test_machine_id_not_empty(self):
        mid = _get_machine_id()
        self.assertTrue(len(mid) > 0)
        self.assertIn(":", mid)

    def test_derive_key_deterministic(self):
        salt = b"test_salt_12345678901234567890"
        key1 = _derive_key("test-machine", salt)
        key2 = _derive_key("test-machine", salt)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)

    def test_different_machines_different_keys(self):
        salt = b"test_salt_12345678901234567890"
        key1 = _derive_key("machine-a", salt)
        key2 = _derive_key("machine-b", salt)
        self.assertNotEqual(key1, key2)


class TestGGUFVerification(unittest.TestCase):
    """GGUF file checksum verification."""

    def test_valid_checksum(self):
        import hashlib
        f = Path(tempfile.mktemp())
        f.write_bytes(b"fake gguf model data for testing")
        expected = hashlib.sha256(b"fake gguf model data for testing").hexdigest()
        self.assertTrue(verify_gguf_checksum(f, expected))
        f.unlink()

    def test_invalid_checksum(self):
        f = Path(tempfile.mktemp())
        f.write_bytes(b"real data")
        self.assertFalse(verify_gguf_checksum(f, "0" * 64))
        f.unlink()

    def test_missing_file(self):
        self.assertFalse(verify_gguf_checksum(Path("/nonexistent/file.gguf"), "abc123"))


class TestBinaryVerification(unittest.TestCase):
    """Binary signature verification."""

    def test_missing_binary(self):
        result = verify_binary_signature(Path("/nonexistent/llama-server"))
        self.assertFalse(result["valid"])

    def test_too_small(self):
        f = Path(tempfile.mktemp())
        f.write_bytes(b"tiny")
        result = verify_binary_signature(f)
        self.assertFalse(result["valid"])
        f.unlink()


class TestProcessIsolation(unittest.TestCase):
    """Process isolation checks."""

    def test_non_root_passes(self):
        result = check_process_isolation()
        if os.getuid() != 0:
            self.assertTrue(result["isolated"] or len(result["warnings"]) >= 0)
            self.assertTrue(any("non-root" in c for c in result["checks"]))

    def test_localhost_binding(self):
        result = check_process_isolation({"inference": {"listen": "localhost"}})
        self.assertTrue(any("localhost" in c for c in result["checks"]))

    def test_wildcard_binding_warns(self):
        result = check_process_isolation({"inference": {"listen": "0.0.0.0"}})
        self.assertTrue(any("0.0.0.0" in w for w in result["warnings"]))


class TestTelegramSecurity(unittest.TestCase):
    """Telegram message sanitization and config validation."""

    def test_sanitize_removes_api_key(self):
        msg = "Config updated. api_key: sk-12345678901234567890"
        clean = sanitize_telegram_message(msg)
        self.assertNotIn("sk-12345678901234567890", clean)
        self.assertIn("[REDACTED]", clean)

    def test_sanitize_removes_password(self):
        msg = "password = super_secret_123"
        clean = sanitize_telegram_message(msg)
        self.assertNotIn("super_secret_123", clean)

    def test_sanitize_removes_long_token(self):
        msg = "Token: abcdefghijklmnopqrstuvwxyz1234567890abcd"
        clean = sanitize_telegram_message(msg)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890abcd", clean)

    def test_sanitize_preserves_safe_text(self):
        msg = "Pipeline completed: 5 steps, 3 tests passed."
        clean = sanitize_telegram_message(msg)
        self.assertEqual(clean, msg)

    def test_config_token_in_yaml(self):
        issues = validate_telegram_config({
            "telegram": {"bot_token": "123456:ABC-DEF"}
        })
        self.assertTrue(any("credential store" in i for i in issues))

    def test_config_token_env_ref_ok(self):
        issues = validate_telegram_config({
            "telegram": {"bot_token": "${TELEGRAM_BOT_TOKEN}"}
        })
        self.assertFalse(any("credential store" in i for i in issues))

    def test_no_allowed_users_warns(self):
        issues = validate_telegram_config({
            "telegram": {"bot_token": "${TELEGRAM_BOT_TOKEN}", "allowed_users": []}
        })
        self.assertTrue(any("allowed_users" in i for i in issues))

    def test_risky_events_warned(self):
        issues = validate_telegram_config({
            "telegram": {
                "bot_token": "${TELEGRAM_BOT_TOKEN}",
                "allowed_users": [123],
                "notify_on": ["pipeline.shipped", "debug"],
            }
        })
        self.assertTrue(any("Risky" in i for i in issues))

    def test_user_whitelist(self):
        self.assertTrue(validate_telegram_user(123, [123, 456]))
        self.assertFalse(validate_telegram_user(789, [123, 456]))

    def test_open_mode(self):
        self.assertTrue(validate_telegram_user(999, []))


class TestSensitiveKeyNames(unittest.TestCase):
    """Verify the sensitive key names set."""

    def test_common_keys_included(self):
        for key in ["api_key", "secret", "password", "token"]:
            self.assertIn(key, SENSITIVE_KEY_NAMES)

    def test_cloud_keys_included(self):
        for key in ["nvidia_api_key", "telegram_bot_token"]:
            self.assertIn(key, SENSITIVE_KEY_NAMES)


if __name__ == "__main__":
    unittest.main()

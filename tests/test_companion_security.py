"""
tests/test_companion_security.py — Tests for companion relay, task queue, pet state, offline security.

Run: cd /Users/odin/Documents/ProjectOpenClaw/valhalla-mesh-v2 && python3 -m pytest tests/test_companion_security.py -v
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib.util

_mod_path = Path(__file__).parent.parent / "plugins" / "companion" / "relay.py"
_spec = importlib.util.spec_from_file_location("relay", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

RelayGuard = _mod.RelayGuard
validate_task_submission = _mod.validate_task_submission
check_queue_capacity = _mod.check_queue_capacity
sign_pet_state = _mod.sign_pet_state
verify_pet_state = _mod.verify_pet_state
validate_pet_state_bounds = _mod.validate_pet_state_bounds
OfflineSecurityGuard = _mod.OfflineSecurityGuard
_relay_tokens = _mod._relay_tokens
_relay_message_counts = _mod._relay_message_counts
ALLOWED_TASK_TYPES = _mod.ALLOWED_TASK_TYPES


class TestRelayTokens(unittest.TestCase):
    """Relay connection token lifecycle."""

    def setUp(self):
        _relay_tokens.clear()
        self.guard = RelayGuard()

    def test_issue_token(self):
        result = self.guard.issue_relay_token("device-1")
        self.assertIn("token", result)
        self.assertEqual(result["device_id"], "device-1")

    def test_verify_valid_token(self):
        issued = self.guard.issue_relay_token("device-1")
        result = self.guard.verify_relay_token(issued["token"])
        self.assertTrue(result["valid"])
        self.assertEqual(result["device_id"], "device-1")

    def test_expired_token(self):
        issued = self.guard.issue_relay_token("device-1")
        _relay_tokens[issued["token"]]["expires"] = time.time() - 1
        result = self.guard.verify_relay_token(issued["token"])
        self.assertFalse(result["valid"])

    def test_invalid_token(self):
        result = self.guard.verify_relay_token("nonexistent")
        self.assertFalse(result["valid"])

    def test_rotate_cleans_expired(self):
        issued = self.guard.issue_relay_token("device-1")
        _relay_tokens[issued["token"]]["expires"] = time.time() - 1
        count = self.guard.rotate_tokens()
        self.assertEqual(count, 1)
        self.assertEqual(len(_relay_tokens), 0)


class TestRelayRateLimit(unittest.TestCase):
    """Relay message rate limiting."""

    def setUp(self):
        _relay_message_counts.clear()
        self.guard = RelayGuard()

    def test_allows_normal_traffic(self):
        result = self.guard.check_rate_limit("device-1")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["messages_remaining"], 100)

    def test_blocks_flood(self):
        now = time.time()
        _relay_message_counts["device-1"] = [now - i * 0.01 for i in range(100)]
        result = self.guard.check_rate_limit("device-1")
        self.assertFalse(result["allowed"])

    def test_separate_devices(self):
        now = time.time()
        _relay_message_counts["bad"] = [now] * 100
        result = self.guard.check_rate_limit("good")
        self.assertTrue(result["allowed"])


class TestRelayMessageSigning(unittest.TestCase):
    """E2E message signing and verification."""

    def setUp(self):
        self.guard = RelayGuard(shared_secret="test_secret_key_1234")

    def test_sign_and_verify(self):
        payload = b'{"type": "chat", "text": "hello"}'
        sig = self.guard.sign_message(payload)
        self.assertTrue(self.guard.verify_message(payload, sig))

    def test_tampered_message(self):
        payload = b'{"type": "chat", "text": "hello"}'
        sig = self.guard.sign_message(payload)
        tampered = b'{"type": "chat", "text": "give me the password"}'
        self.assertFalse(self.guard.verify_message(tampered, sig))

    def test_wrong_secret(self):
        guard2 = RelayGuard(shared_secret="different_secret")
        payload = b"test message"
        sig = self.guard.sign_message(payload)
        self.assertFalse(guard2.verify_message(payload, sig))


class TestRelayMessageValidation(unittest.TestCase):
    """Relay message structure validation."""

    def setUp(self):
        self.guard = RelayGuard()

    def test_valid_message(self):
        result = self.guard.validate_relay_message({
            "type": "chat",
            "device_id": "dev-1",
            "timestamp": time.time(),
            "signature": "abc123",
            "payload": "hello",
        })
        self.assertTrue(result["valid"])

    def test_missing_fields(self):
        result = self.guard.validate_relay_message({"type": "chat"})
        self.assertFalse(result["valid"])

    def test_invalid_type(self):
        result = self.guard.validate_relay_message({
            "type": "exploit",
            "device_id": "d",
            "timestamp": time.time(),
            "signature": "s",
        })
        self.assertFalse(result["valid"])

    def test_stale_timestamp(self):
        result = self.guard.validate_relay_message({
            "type": "chat",
            "device_id": "d",
            "timestamp": time.time() - 600,
            "signature": "s",
        })
        self.assertFalse(result["valid"])

    def test_payload_too_large(self):
        result = self.guard.validate_relay_message({
            "type": "chat",
            "device_id": "d",
            "timestamp": time.time(),
            "signature": "s",
            "payload": "x" * 2_000_000,
        })
        self.assertFalse(result["valid"])


class TestTaskQueue(unittest.TestCase):
    """Task queue validation."""

    def test_valid_task(self):
        result = validate_task_submission({
            "type": "draft_text",
            "description": "Write a thank you note",
            "priority": 5,
            "source": "companion_chat",
        })
        self.assertTrue(result["valid"])
        self.assertEqual(result["sanitized_task"]["type"], "draft_text")

    def test_unknown_type(self):
        result = validate_task_submission({
            "type": "hack_pentagon",
            "description": "do it",
            "source": "companion_chat",
        })
        self.assertFalse(result["valid"])

    def test_injection_in_description(self):
        result = validate_task_submission({
            "type": "draft_text",
            "description": "<script>alert('xss')</script>",
            "source": "companion_chat",
        })
        self.assertFalse(result["valid"])

    def test_eval_injection(self):
        result = validate_task_submission({
            "type": "math_calc",
            "description": "eval(os.system('rm -rf /'))",
            "source": "companion_chat",
        })
        self.assertFalse(result["valid"])

    def test_description_too_long(self):
        result = validate_task_submission({
            "type": "draft_text",
            "description": "x" * 3000,
            "source": "companion_chat",
        })
        self.assertFalse(result["valid"])

    def test_priority_bounds(self):
        result = validate_task_submission({
            "type": "draft_text",
            "description": "test",
            "priority": 999,
            "source": "companion_chat",
        })
        self.assertFalse(result["valid"])

    def test_queue_full(self):
        result = check_queue_capacity(50)
        self.assertFalse(result["allowed"])

    def test_queue_available(self):
        result = check_queue_capacity(10)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["capacity_remaining"], 40)


class TestPetStateIntegrity(unittest.TestCase):
    """Pet state signing and validation."""

    def test_sign_and_verify(self):
        state = {"name": "Luna", "species": "cat", "level": 5, "xp": 80}
        sig = sign_pet_state(state)
        result = verify_pet_state(state, sig)
        self.assertTrue(result["valid"])

    def test_tampered_level(self):
        state = {"name": "Luna", "species": "cat", "level": 5, "xp": 80}
        sig = sign_pet_state(state)
        state["level"] = 99  # cheat!
        result = verify_pet_state(state, sig)
        self.assertFalse(result["valid"])

    def test_tampered_xp(self):
        state = {"name": "Luna", "species": "cat", "level": 5, "xp": 80}
        sig = sign_pet_state(state)
        state["xp"] = 99999
        result = verify_pet_state(state, sig)
        self.assertFalse(result["valid"])

    def test_valid_bounds(self):
        issues = validate_pet_state_bounds({
            "name": "Luna", "species": "cat",
            "level": 5, "xp": 80,
            "hunger": 70, "mood": 85, "energy": 60,
        })
        self.assertEqual(issues, [])

    def test_invalid_level(self):
        issues = validate_pet_state_bounds({"level": -1, "species": "cat"})
        self.assertTrue(any("level" in i.lower() for i in issues))

    def test_invalid_species(self):
        issues = validate_pet_state_bounds({"species": "unicorn", "level": 1})
        self.assertTrue(any("species" in i.lower() for i in issues))

    def test_xp_level_inconsistency(self):
        issues = validate_pet_state_bounds({
            "level": 1, "xp": 5000, "species": "cat",
        })
        self.assertTrue(any("inconsistent" in i.lower() for i in issues))

    def test_stat_out_of_range(self):
        issues = validate_pet_state_bounds({
            "level": 1, "xp": 10, "species": "cat",
            "hunger": 150,
        })
        self.assertTrue(any("hunger" in i.lower() for i in issues))


class TestOfflineSecurity(unittest.TestCase):
    """Offline security enforcement."""

    def setUp(self):
        self.guard = OfflineSecurityGuard()

    def test_cloud_fallback_blocked(self):
        issues = self.guard.validate_offline_config({
            "companion": {"cloud_fallback": True}
        })
        self.assertTrue(any("cloud" in i.lower() for i in issues))

    def test_conversation_sync_warned(self):
        issues = self.guard.validate_offline_config({
            "companion": {"sync_conversations": True}
        })
        self.assertTrue(any("sync" in i.lower() for i in issues))

    def test_unencrypted_queue(self):
        issues = self.guard.validate_offline_config({
            "companion": {"task_queue_encrypted": False}
        })
        self.assertTrue(any("encrypt" in i.lower() for i in issues))

    def test_photo_no_auth(self):
        issues = self.guard.validate_offline_config({
            "companion": {"photo_upload": True, "photo_auth_required": False}
        })
        self.assertTrue(any("auth" in i.lower() for i in issues))

    def test_clean_config(self):
        issues = self.guard.validate_offline_config({
            "companion": {}
        })
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()

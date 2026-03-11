"""
tests/test_payment_security.py — Tests for payment security, voice privacy, mobile auth, and store content.

Run: cd /Users/odin/Documents/ProjectOpenClaw/valhalla-mesh-v2 && python3 -m pytest tests/test_payment_security.py -v
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from hyphenated directory
import importlib.util

_mod_path = Path(__file__).parent.parent / "plugins" / "payments" / "security.py"
_spec = importlib.util.spec_from_file_location("payments_security", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

verify_stripe_webhook = _mod.verify_stripe_webhook
PurchaseLog = _mod.PurchaseLog
check_purchase_rate = _mod.check_purchase_rate
record_purchase_attempt = _mod.record_purchase_attempt
VoicePrivacyGuard = _mod.VoicePrivacyGuard
issue_qr_token = _mod.issue_qr_token
claim_qr_token = _mod.claim_qr_token
verify_mobile_token = _mod.verify_mobile_token
revoke_all_mobile_tokens = _mod.revoke_all_mobile_tokens
list_mobile_devices = _mod.list_mobile_devices
sanitize_svg = _mod.sanitize_svg
validate_voice_pack_file = _mod.validate_voice_pack_file
_purchase_attempts = _mod._purchase_attempts
_mobile_tokens = _mod._mobile_tokens


class TestStripeWebhook(unittest.TestCase):
    """Stripe webhook signature verification."""

    def _sign(self, payload: bytes, secret: str, timestamp: int = None):
        ts = timestamp or int(time.time())
        signed = f"{ts}.".encode() + payload
        sig = hmac_mod.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_valid_webhook(self):
        payload = b'{"type": "payment_intent.succeeded"}'
        secret = "whsec_test123"
        header = self._sign(payload, secret)
        result = verify_stripe_webhook(payload, header, secret)
        self.assertTrue(result["valid"])
        self.assertEqual(result["event_type"], "payment_intent.succeeded")

    def test_invalid_signature(self):
        payload = b'{"type": "payment_intent.succeeded"}'
        result = verify_stripe_webhook(payload, "t=123,v1=fakesig", "whsec_test")
        self.assertFalse(result["valid"])

    def test_expired_timestamp(self):
        payload = b'{"type": "test"}'
        secret = "whsec_test"
        old_ts = int(time.time()) - 600  # 10 minutes ago
        header = self._sign(payload, secret, old_ts)
        result = verify_stripe_webhook(payload, header, secret, tolerance_seconds=300)
        self.assertFalse(result["valid"])
        self.assertTrue(any("too old" in i for i in result["issues"]))

    def test_missing_payload(self):
        result = verify_stripe_webhook(b"", "t=1,v1=sig", "secret")
        self.assertFalse(result["valid"])

    def test_malformed_header(self):
        result = verify_stripe_webhook(b"data", "garbage", "secret")
        self.assertFalse(result["valid"])


class TestPurchaseLog(unittest.TestCase):
    """Immutable purchase receipt chain."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.log = PurchaseLog(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_receipt(self):
        receipt = self.log.add_receipt(
            item_id="theme-valhalla",
            item_type="theme",
            buyer="user123",
            seller="creator456",
            amount_cents=500,
            platform_fee_cents=150,
            stripe_payment_id="pi_test123",
        )
        self.assertIn("receipt_id", receipt)
        self.assertEqual(receipt["seller_payout_cents"], 350)

    def test_chain_integrity(self):
        for i in range(5):
            self.log.add_receipt(
                item_id=f"item-{i}",
                item_type="theme",
                buyer="buyer",
                seller="seller",
                amount_cents=100,
                platform_fee_cents=30,
                stripe_payment_id=f"pi_{i}",
            )
        result = self.log.verify_chain()
        self.assertTrue(result["valid"])
        self.assertEqual(result["count"], 5)

    def test_tamper_detection(self):
        self.log.add_receipt("a", "theme", "b", "s", 100, 30, "pi_1")
        self.log.add_receipt("b", "theme", "b", "s", 200, 60, "pi_2")
        # Tamper with first receipt
        self.log._receipts[0]["amount_cents"] = 999
        result = self.log.verify_chain()
        self.assertFalse(result["valid"])

    def test_persistence(self):
        self.log.add_receipt("x", "agent", "b", "s", 500, 150, "pi_x")
        log2 = PurchaseLog(self.tmpdir)
        self.assertEqual(len(log2.get_receipts()), 1)

    def test_filter_by_buyer(self):
        self.log.add_receipt("a", "t", "alice", "s", 100, 30, "p1")
        self.log.add_receipt("b", "t", "bob", "s", 200, 60, "p2")
        self.assertEqual(len(self.log.get_receipts(buyer="alice")), 1)


class TestCardTestingPrevention(unittest.TestCase):
    """Purchase rate limiting."""

    def setUp(self):
        _purchase_attempts.clear()

    def test_allows_normal_purchases(self):
        result = check_purchase_rate("1.2.3.4")
        self.assertTrue(result["allowed"])

    def test_blocks_excessive_attempts(self):
        now = time.time()
        _purchase_attempts["1.2.3.4"] = [now - i for i in range(10)]
        result = check_purchase_rate("1.2.3.4")
        self.assertFalse(result["allowed"])

    def test_separate_ips(self):
        now = time.time()
        _purchase_attempts["bad.ip"] = [now - i for i in range(10)]
        result = check_purchase_rate("good.ip")
        self.assertTrue(result["allowed"])


class TestVoicePrivacy(unittest.TestCase):
    """Voice privacy enforcement."""

    def setUp(self):
        self.guard = VoicePrivacyGuard()

    def test_local_config_valid(self):
        issues = self.guard.validate_voice_config({
            "voice": {"stt_provider": "faster-whisper", "tts_provider": "kokoro"}
        })
        self.assertEqual(issues, [])

    def test_cloud_stt_warned(self):
        issues = self.guard.validate_voice_config({
            "voice": {"stt_provider": "google-cloud"}
        })
        self.assertTrue(any("cloud" in i.lower() for i in issues))

    def test_cloud_tts_warned(self):
        issues = self.guard.validate_voice_config({
            "voice": {"tts_provider": "elevenlabs"}
        })
        self.assertTrue(any("cloud" in i.lower() for i in issues))

    def test_unencrypted_audio_warned(self):
        issues = self.guard.validate_voice_config({
            "voice": {"save_audio": True, "audio_encrypted": False}
        })
        self.assertTrue(any("encrypted" in i for i in issues))

    def test_non_localhost_ws(self):
        issues = self.guard.validate_voice_config({
            "voice": {"ws_host": "0.0.0.0"}
        })
        self.assertTrue(any("network" in i.lower() for i in issues))

    def test_cloud_fallback_alert(self):
        alert = self.guard.check_cloud_fallback("google")
        self.assertIsNotNone(alert)
        self.assertIn("cloud", alert.lower())

    def test_local_no_alert(self):
        alert = self.guard.check_cloud_fallback("faster-whisper")
        self.assertIsNone(alert)


class TestMobileAuth(unittest.TestCase):
    """Mobile QR auth token lifecycle."""

    def setUp(self):
        _mobile_tokens.clear()

    def test_issue_qr_token(self):
        result = issue_qr_token()
        self.assertIn("token", result)
        self.assertEqual(result["expires_in"], 300)
        self.assertTrue(result["qr_data"].startswith("valhalla://pair"))

    def test_claim_qr_token(self):
        qr = issue_qr_token()
        result = claim_qr_token(qr["token"], "iPhone 15")
        self.assertTrue(result["valid"])
        self.assertIsNotNone(result["mobile_token"])

    def test_verify_mobile_token(self):
        qr = issue_qr_token()
        claimed = claim_qr_token(qr["token"])
        result = verify_mobile_token(claimed["mobile_token"])
        self.assertTrue(result["valid"])

    def test_expired_qr(self):
        qr = issue_qr_token()
        # Manually expire it
        _mobile_tokens[qr["token"]]["expires"] = time.time() - 1
        result = claim_qr_token(qr["token"])
        self.assertFalse(result["valid"])
        self.assertTrue(any("expired" in i.lower() for i in result["issues"]))

    def test_double_claim(self):
        qr = issue_qr_token()
        claim_qr_token(qr["token"])
        result = claim_qr_token(qr["token"])
        self.assertFalse(result["valid"])

    def test_revoke_all(self):
        qr = issue_qr_token()
        claimed = claim_qr_token(qr["token"])
        count = revoke_all_mobile_tokens()
        self.assertEqual(count, 1)
        result = verify_mobile_token(claimed["mobile_token"])
        self.assertFalse(result["valid"])

    def test_invalid_token(self):
        result = verify_mobile_token("nonexistent")
        self.assertFalse(result["valid"])

    def test_list_devices(self):
        qr = issue_qr_token()
        claim_qr_token(qr["token"], "Pixel 8")
        devices = list_mobile_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["device"], "Pixel 8")


class TestSVGSanitization(unittest.TestCase):
    """SVG content security."""

    def test_clean_svg(self):
        result = sanitize_svg('<svg><rect width="100" height="100" fill="red"/></svg>')
        self.assertTrue(result["safe"])

    def test_script_blocked(self):
        result = sanitize_svg('<svg><script>alert("xss")</script></svg>')
        self.assertFalse(result["safe"])

    def test_onclick_blocked(self):
        result = sanitize_svg('<svg><rect onclick="alert(1)"/></svg>')
        self.assertFalse(result["safe"])

    def test_javascript_href_blocked(self):
        result = sanitize_svg('<svg><a href="javascript:alert(1)">click</a></svg>')
        self.assertFalse(result["safe"])

    def test_foreignobject_blocked(self):
        result = sanitize_svg('<svg><foreignObject><body>html!</body></foreignObject></svg>')
        self.assertFalse(result["safe"])

    def test_iframe_blocked(self):
        result = sanitize_svg('<svg><iframe src="https://evil.com"></iframe></svg>')
        self.assertFalse(result["safe"])


class TestVoiceFileValidation(unittest.TestCase):
    """Voice pack file magic byte validation."""

    def test_valid_wav(self):
        f = Path(tempfile.mktemp(suffix=".wav"))
        # WAV header
        f.write_bytes(b"RIFF" + b"\x00" * 100)
        result = validate_voice_pack_file(f)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "wav")
        f.unlink()

    def test_valid_ogg(self):
        f = Path(tempfile.mktemp(suffix=".ogg"))
        f.write_bytes(b"OggS" + b"\x00" * 100)
        result = validate_voice_pack_file(f)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "ogg")
        f.unlink()

    def test_executable_rejected(self):
        f = Path(tempfile.mktemp(suffix=".wav"))
        f.write_bytes(b"MZ" + b"\x00" * 100)  # PE executable header
        result = validate_voice_pack_file(f)
        self.assertFalse(result["valid"])
        f.unlink()

    def test_missing_file(self):
        result = validate_voice_pack_file(Path("/nonexistent/voice.wav"))
        self.assertFalse(result["valid"])

    def test_too_large(self):
        f = Path(tempfile.mktemp(suffix=".wav"))
        f.write_bytes(b"RIFF" + b"\x00" * 10_000_100)
        result = validate_voice_pack_file(f)
        self.assertFalse(result["valid"])
        f.unlink()


if __name__ == "__main__":
    unittest.main()

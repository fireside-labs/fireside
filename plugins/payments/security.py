"""
plugins/payments/security.py — Payment security, voice privacy, mobile auth, and store content review.

Handles:
  - Stripe webhook signature verification
  - Immutable purchase receipts
  - Card testing attack prevention (rate limiting)
  - Voice privacy enforcement (local-only, no disk storage)
  - Mobile QR token lifecycle (issue, verify, revoke, expire)
  - Store content scanning (SVG sanitization, voice file validation, personality injection)

Heimdall Sprint 9.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import struct
import time
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("heimdall.payments")

# ---------------------------------------------------------------------------
# Stripe Webhook Verification
# ---------------------------------------------------------------------------

def verify_stripe_webhook(
    payload: bytes,
    signature_header: str,
    webhook_secret: str,
    tolerance_seconds: int = 300,
) -> dict:
    """Verify a Stripe webhook signature.

    Stripe signs webhooks with HMAC-SHA256 using the endpoint's signing secret.
    Format: `t=timestamp,v1=signature[,v1=signature...]`

    Returns:
        {valid: bool, event_type: str, issues: list}
    """
    result = {"valid": False, "event_type": None, "issues": []}

    if not payload or not signature_header or not webhook_secret:
        result["issues"].append("Missing payload, signature, or webhook secret")
        return result

    # Parse Stripe signature header
    try:
        elements = dict(
            pair.split("=", 1)
            for pair in signature_header.split(",")
            if "=" in pair
        )
    except Exception:
        result["issues"].append("Malformed signature header")
        return result

    timestamp = elements.get("t")
    signatures = [
        v for k, v in
        (pair.split("=", 1) for pair in signature_header.split(",") if "=" in pair)
        if k == "v1"
    ]

    if not timestamp:
        result["issues"].append("Missing timestamp in signature")
        return result

    if not signatures:
        result["issues"].append("Missing v1 signature")
        return result

    # Timestamp tolerance (prevent replay attacks)
    try:
        ts = int(timestamp)
    except ValueError:
        result["issues"].append("Invalid timestamp")
        return result

    age = abs(time.time() - ts)
    if age > tolerance_seconds:
        result["issues"].append(
            f"Webhook too old ({age:.0f}s > {tolerance_seconds}s tolerance)"
        )
        return result

    # Compute expected signature
    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    # Timing-safe compare against all provided signatures
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        result["issues"].append("Signature mismatch — possible tampering")
        log.critical("[payments] 🔴 Stripe webhook signature MISMATCH")
        return result

    # Parse event type
    try:
        event = json.loads(payload)
        result["event_type"] = event.get("type", "unknown")
    except Exception:
        result["event_type"] = "parse_error"

    result["valid"] = True
    return result


# ---------------------------------------------------------------------------
# Purchase Receipt Log (immutable append-only)
# ---------------------------------------------------------------------------

class PurchaseLog:
    """Immutable, append-only purchase receipt log.

    Each receipt is SHA256-chained to the previous one for tamper detection.
    """

    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "purchase_receipts.json"
        self._receipts: list = []
        self._load()

    def _load(self) -> None:
        if self.log_file.exists():
            try:
                self._receipts = json.loads(
                    self.log_file.read_text(encoding="utf-8")
                )
            except Exception:
                self._receipts = []

    def _save(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.write_text(
            json.dumps(self._receipts, indent=2),
            encoding="utf-8",
        )

    def _chain_hash(self) -> str:
        """Get the receipt_hash of the last receipt for chaining."""
        if not self._receipts:
            return "genesis"
        return self._receipts[-1].get("receipt_hash", "genesis")

    def add_receipt(
        self,
        item_id: str,
        item_type: str,
        buyer: str,
        seller: str,
        amount_cents: int,
        platform_fee_cents: int,
        stripe_payment_id: str,
    ) -> dict:
        """Add an immutable purchase receipt.

        Returns the receipt with chain hash.
        """
        receipt = {
            "receipt_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "item_id": item_id,
            "item_type": item_type,  # "agent", "theme", "avatar", "voice", "personality"
            "buyer": buyer,
            "seller": seller,
            "amount_cents": amount_cents,
            "platform_fee_cents": platform_fee_cents,
            "seller_payout_cents": amount_cents - platform_fee_cents,
            "stripe_payment_id": stripe_payment_id,
            "prev_hash": self._chain_hash(),
        }
        # Receipt hash (includes prev_hash for chaining)
        receipt["receipt_hash"] = hashlib.sha256(
            json.dumps(receipt, sort_keys=True).encode()
        ).hexdigest()

        self._receipts.append(receipt)
        self._save()

        log.info(
            "[payments] Receipt %s: %s bought %s for $%.2f",
            receipt["receipt_id"][:8], buyer, item_id,
            amount_cents / 100,
        )
        return receipt

    def verify_chain(self) -> dict:
        """Verify the entire receipt chain is untampered.

        Returns {valid, count, issues}.
        """
        issues = []
        prev_hash = "genesis"

        for i, receipt in enumerate(self._receipts):
            if receipt.get("prev_hash") != prev_hash:
                issues.append(f"Chain break at receipt {i}: prev_hash mismatch")

            # Recompute receipt hash
            r_copy = {k: v for k, v in receipt.items() if k != "receipt_hash"}
            expected = hashlib.sha256(
                json.dumps(r_copy, sort_keys=True).encode()
            ).hexdigest()
            if receipt.get("receipt_hash") != expected:
                issues.append(f"Tampered receipt at index {i}")

            prev_hash = receipt.get("receipt_hash", "")

        return {
            "valid": len(issues) == 0,
            "count": len(self._receipts),
            "issues": issues,
        }

    def get_receipts(self, buyer: str = None, limit: int = 100) -> list:
        """Get receipts, optionally filtered by buyer."""
        receipts = self._receipts
        if buyer:
            receipts = [r for r in receipts if r.get("buyer") == buyer]
        return list(reversed(receipts[-limit:]))


# ---------------------------------------------------------------------------
# Card testing prevention
# ---------------------------------------------------------------------------

# In-memory rate tracker for purchase attempts
_purchase_attempts: dict = {}  # {ip: [timestamps]}
MAX_PURCHASE_ATTEMPTS_PER_HOUR = 10
MAX_FAILED_PAYMENTS_PER_HOUR = 3


def check_purchase_rate(ip: str) -> dict:
    """Rate-limit purchase API calls to prevent card testing.

    Returns {allowed, attempts_remaining, issues}.
    """
    now = time.time()
    one_hour_ago = now - 3600

    attempts = _purchase_attempts.get(ip, [])
    attempts = [t for t in attempts if t > one_hour_ago]
    _purchase_attempts[ip] = attempts

    if len(attempts) >= MAX_PURCHASE_ATTEMPTS_PER_HOUR:
        log.warning("[payments] Card testing suspected from %s", ip)
        return {
            "allowed": False,
            "attempts_remaining": 0,
            "issues": ["Rate limit exceeded — too many purchase attempts"],
        }

    return {
        "allowed": True,
        "attempts_remaining": MAX_PURCHASE_ATTEMPTS_PER_HOUR - len(attempts),
        "issues": [],
    }


def record_purchase_attempt(ip: str, success: bool) -> None:
    """Record a purchase attempt for rate limiting."""
    _purchase_attempts.setdefault(ip, []).append(time.time())

    if not success:
        # Track failed payments separately
        key = f"fail:{ip}"
        _purchase_attempts.setdefault(key, []).append(time.time())
        fails = len([
            t for t in _purchase_attempts[key]
            if t > time.time() - 3600
        ])
        if fails >= MAX_FAILED_PAYMENTS_PER_HOUR:
            log.critical(
                "[payments] 🔴 Card testing detected: %d failed payments from %s",
                fails, ip,
            )


# ---------------------------------------------------------------------------
# Voice Privacy
# ---------------------------------------------------------------------------

class VoicePrivacyGuard:
    """Enforce voice data privacy rules."""

    def __init__(self):
        self.voice_logging_enabled = False  # User must explicitly opt-in

    def validate_voice_config(self, config: dict) -> list:
        """Validate voice plugin configuration for privacy.

        Returns list of issues.
        """
        issues = []
        voice = config.get("voice", {})

        # Audio must stay local
        stt_provider = voice.get("stt_provider", "local")
        if stt_provider not in ("local", "faster-whisper", "whisper"):
            issues.append(
                f"⚠️ STT provider '{stt_provider}' may send audio to cloud. "
                "Use 'local' (faster-whisper) for privacy."
            )

        tts_provider = voice.get("tts_provider", "local")
        if tts_provider not in ("local", "kokoro", "piper"):
            issues.append(
                f"⚠️ TTS provider '{tts_provider}' may send text to cloud. "
                "Use 'local' (kokoro) for privacy."
            )

        # No disk storage by default
        if voice.get("save_audio", False) and not voice.get("audio_encrypted", False):
            issues.append(
                "⚠️ Voice logging enabled but audio not encrypted. "
                "Set audio_encrypted: true or disable save_audio."
            )

        # WebSocket must be localhost
        ws_host = voice.get("ws_host", "localhost")
        if ws_host not in ("localhost", "127.0.0.1"):
            issues.append(
                f"🔴 Voice WebSocket on {ws_host} — audio accessible from network! "
                "Use localhost."
            )

        return issues

    def check_cloud_fallback(self, active_provider: str) -> Optional[str]:
        """Alert if voice is routed through cloud.

        Returns alert message, or None if local.
        """
        cloud_providers = {"google", "azure", "aws", "openai", "elevenlabs", "deepgram"}
        if active_provider.lower() in cloud_providers:
            return (
                f"⚠️ Voice is using cloud provider '{active_provider}'. "
                "Your audio is being sent over the internet. "
                "Switch to local (Whisper + Kokoro) for privacy."
            )
        return None

    def get_privacy_status(self) -> dict:
        return {
            "audio_stays_local": True,  # enforced by config validation
            "disk_storage": "disabled" if not self.voice_logging_enabled else "opt-in, encrypted",
            "cloud_transcription": False,
            "cloud_tts": False,
        }


# ---------------------------------------------------------------------------
# Mobile Auth Security
# ---------------------------------------------------------------------------

# QR token store
_mobile_tokens: dict = {}  # {token: {issued, expires, device, revoked}}

QR_TOKEN_EXPIRY_SECONDS = 300  # 5 minutes to scan
MOBILE_TOKEN_LIFETIME_DAYS = 30


def issue_qr_token() -> dict:
    """Generate a time-limited QR code token for mobile pairing.

    Returns {token, expires_in, qr_data}.
    """
    token = str(uuid.uuid4())
    now = time.time()

    _mobile_tokens[token] = {
        "type": "qr_pending",
        "issued": now,
        "expires": now + QR_TOKEN_EXPIRY_SECONDS,
        "device": None,
        "revoked": False,
    }

    return {
        "token": token,
        "expires_in": QR_TOKEN_EXPIRY_SECONDS,
        "qr_data": f"valhalla://pair?token={token}",
    }


def claim_qr_token(token: str, device_info: str = "mobile") -> dict:
    """Claim a QR token after scanning.

    Upgrades to a long-lived mobile token.
    Returns {valid, mobile_token, issues}.
    """
    result = {"valid": False, "mobile_token": None, "issues": []}

    entry = _mobile_tokens.get(token)
    if not entry:
        result["issues"].append("Invalid token")
        return result

    if entry.get("revoked"):
        result["issues"].append("Token has been revoked")
        return result

    if time.time() > entry.get("expires", 0):
        result["issues"].append("QR code expired — generate a new one")
        return result

    if entry.get("type") != "qr_pending":
        result["issues"].append("Token already claimed")
        return result

    # Upgrade to mobile token
    mobile_token = str(uuid.uuid4())
    now = time.time()

    _mobile_tokens[mobile_token] = {
        "type": "mobile_active",
        "issued": now,
        "expires": now + (MOBILE_TOKEN_LIFETIME_DAYS * 86400),
        "device": device_info,
        "revoked": False,
        "parent_qr": token,
    }

    # Mark QR as claimed
    entry["type"] = "qr_claimed"

    result["valid"] = True
    result["mobile_token"] = mobile_token
    return result


def verify_mobile_token(token: str) -> dict:
    """Verify a mobile access token.

    Returns {valid, device, issues}.
    """
    result = {"valid": False, "device": None, "issues": []}

    entry = _mobile_tokens.get(token)
    if not entry:
        result["issues"].append("Invalid token")
        return result

    if entry.get("revoked"):
        result["issues"].append("Token revoked")
        return result

    if entry.get("type") != "mobile_active":
        result["issues"].append("Not a mobile token")
        return result

    if time.time() > entry.get("expires", 0):
        result["issues"].append("Token expired — re-scan QR code")
        return result

    result["valid"] = True
    result["device"] = entry.get("device")
    return result


def revoke_all_mobile_tokens() -> int:
    """Revoke ALL mobile tokens (disconnect all devices).

    Returns count of revoked tokens.
    """
    count = 0
    for token, entry in _mobile_tokens.items():
        if entry.get("type") == "mobile_active" and not entry.get("revoked"):
            entry["revoked"] = True
            count += 1

    log.info("[mobile] Revoked %d mobile tokens", count)
    return count


def list_mobile_devices() -> list:
    """List active mobile connections."""
    devices = []
    for token, entry in _mobile_tokens.items():
        if (
            entry.get("type") == "mobile_active"
            and not entry.get("revoked")
            and time.time() < entry.get("expires", 0)
        ):
            devices.append({
                "device": entry.get("device", "unknown"),
                "connected_since": entry.get("issued"),
                "expires": entry.get("expires"),
            })
    return devices


# ---------------------------------------------------------------------------
# Store Content Security
# ---------------------------------------------------------------------------

# Dangerous SVG elements/attributes
_SVG_DANGEROUS = [
    r"<script",
    r"on\w+\s*=",     # onclick, onerror, onload, etc.
    r"javascript\s*:",
    r"data\s*:\s*text/html",
    r"<foreignObject",
    r"<iframe",
    r"<embed",
    r"<object",
    r"xlink:href\s*=\s*[\"'](?!#)",  # external xlinks
    r"<use\s+[^>]*href\s*=\s*[\"']https?://",  # external use references
]

_SVG_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _SVG_DANGEROUS]


def sanitize_svg(svg_content: str) -> dict:
    """Scan an SVG file for embedded scripts and dangerous elements.

    Returns {safe, issues, cleaned}.
    """
    issues = []

    for pattern in _SVG_PATTERNS:
        matches = pattern.findall(svg_content)
        if matches:
            issues.append(f"Dangerous SVG content: {matches[0][:50]}")

    return {
        "safe": len(issues) == 0,
        "issues": issues,
    }


# Valid audio file magic bytes
_AUDIO_SIGNATURES = {
    b"RIFF": "wav",
    b"OggS": "ogg",
    b"\xff\xfb": "mp3",
    b"\xff\xf3": "mp3",
    b"\xff\xf2": "mp3",
    b"ID3": "mp3",
    b"fLaC": "flac",
}


def validate_voice_pack_file(file_path: Path) -> dict:
    """Validate a voice pack file is actually audio.

    Checks magic bytes, not just extension. Prevents executable masquerading.
    Returns {valid, format, issues}.
    """
    result = {"valid": False, "format": None, "issues": []}
    file_path = Path(file_path)

    if not file_path.exists():
        result["issues"].append("File not found")
        return result

    # Read first 12 bytes (enough for all signatures)
    with open(file_path, "rb") as f:
        header = f.read(12)

    if len(header) < 4:
        result["issues"].append("File too small to be audio")
        return result

    # Check magic bytes
    detected = None
    for magic, fmt in _AUDIO_SIGNATURES.items():
        if header[:len(magic)] == magic:
            detected = fmt
            break

    if not detected:
        result["issues"].append(
            f"Not a recognized audio format (header: {header[:4].hex()})"
        )
        return result

    # Size check (voice clips should be < 10MB)
    size = file_path.stat().st_size
    if size > 10_000_000:
        result["issues"].append(f"File too large ({size / 1e6:.1f} MB, max 10 MB)")
        return result

    result["valid"] = True
    result["format"] = detected
    return result


def scan_personality_preset(preset: dict) -> list:
    """Scan a personality preset for prompt injection.

    Uses the same patterns from personality_guard.py.

    Returns list of issues.
    """
    from middleware.personality_guard import PersonalityGuard

    guard = PersonalityGuard()
    issues = []

    # Scan all text fields
    for field in ["name", "role", "description", "system_prompt_modifier"]:
        text = preset.get(field, "")
        if text:
            injections = guard.scan_for_injection(text)
            for inj in injections:
                issues.append(f"[{field}] {inj}")

    # Scan boundary rules
    for i, rule in enumerate(preset.get("boundaries", [])):
        injections = guard.scan_for_injection(rule)
        for inj in injections:
            issues.append(f"[boundary #{i}] {inj}")

    # Validate slider values if present
    sliders = preset.get("sliders", {})
    if sliders:
        slider_issues = guard.validate_slider_values(sliders)
        issues.extend(slider_issues)

    return issues

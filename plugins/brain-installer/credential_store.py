"""
plugins/brain-installer/credential_store.py — Secure credential storage.

Stores API keys and tokens in ~/.valhalla/credentials (NOT in valhalla.yaml).
Encrypted at rest with AES-256-GCM using a machine-specific key.
File permissions set to 600 (owner read/write only).

Heimdall Sprint 7.

Usage:
    from plugins.brain_installer.credential_store import CredentialStore

    store = CredentialStore()
    store.set("nvidia_api_key", "nvapi-abc123...")
    key = store.get("nvidia_api_key")        # returns full key
    masked = store.get_masked("nvidia_api_key")  # returns "nvapi-...c123"
    store.delete("nvidia_api_key")
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import platform
import stat
import subprocess
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("heimdall.credentials")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_STORE_DIR = Path.home() / ".valhalla"
DEFAULT_STORE_FILE = "credentials"
MASK_VISIBLE_CHARS = 4  # show first N and last N characters

# ---------------------------------------------------------------------------
# Machine-specific key derivation
# ---------------------------------------------------------------------------

def _get_machine_id() -> str:
    """Get a stable machine-specific identifier for key derivation.

    Uses (in priority order):
    1. macOS: IOPlatformSerialNumber via ioreg
    2. Linux: /etc/machine-id
    3. Fallback: hostname + platform + username hash
    """
    # macOS
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "IOPlatformSerialNumber" in line:
                    serial = line.split('"')[-2]
                    if serial and len(serial) > 4:
                        return f"darwin:{serial}"
        except Exception:
            pass

    # Linux
    machine_id_path = Path("/etc/machine-id")
    if machine_id_path.exists():
        try:
            mid = machine_id_path.read_text().strip()
            if mid:
                return f"linux:{mid}"
        except Exception:
            pass

    # Fallback
    fallback = f"{platform.node()}:{platform.system()}:{os.getlogin()}"
    return f"fallback:{fallback}"


def _derive_key(machine_id: str, salt: bytes) -> bytes:
    """Derive a 32-byte AES key from machine ID + salt using PBKDF2."""
    try:
        import hashlib
        key = hashlib.pbkdf2_hmac(
            "sha256",
            machine_id.encode("utf-8"),
            salt,
            iterations=100_000,
            dklen=32,
        )
        return key
    except Exception as e:
        log.error("[credentials] Key derivation failed: %s", e)
        raise


# ---------------------------------------------------------------------------
# AES-256-GCM encryption (using cryptography library if available,
# fallback to base64 obfuscation if not)
# ---------------------------------------------------------------------------

def _encrypt(plaintext: str, key: bytes) -> dict:
    """Encrypt plaintext with AES-256-GCM. Returns {nonce, ciphertext, tag}."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return {
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ct).decode(),
            "method": "aes-256-gcm",
        }
    except ImportError:
        # Fallback: XOR with key hash (not real encryption, but better than plaintext)
        log.warning(
            "[credentials] 'cryptography' package not installed. "
            "Using obfuscation fallback. Install with: pip install cryptography"
        )
        key_stream = hashlib.sha256(key).digest()
        obfuscated = bytes(
            b ^ key_stream[i % len(key_stream)]
            for i, b in enumerate(plaintext.encode("utf-8"))
        )
        return {
            "ciphertext": base64.b64encode(obfuscated).decode(),
            "method": "xor-obfuscation",
        }


def _decrypt(encrypted: dict, key: bytes) -> str:
    """Decrypt ciphertext back to plaintext."""
    method = encrypted.get("method", "aes-256-gcm")

    if method == "aes-256-gcm":
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(key)
            nonce = base64.b64decode(encrypted["nonce"])
            ct = base64.b64decode(encrypted["ciphertext"])
            return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
        except ImportError:
            raise RuntimeError(
                "Credentials encrypted with AES-256-GCM but 'cryptography' "
                "package not installed. Install with: pip install cryptography"
            )

    elif method == "xor-obfuscation":
        key_stream = hashlib.sha256(key).digest()
        ct = base64.b64decode(encrypted["ciphertext"])
        plaintext = bytes(
            b ^ key_stream[i % len(key_stream)]
            for i, b in enumerate(ct)
        )
        return plaintext.decode("utf-8")

    else:
        raise ValueError(f"Unknown encryption method: {method}")


# ---------------------------------------------------------------------------
# Credential Store
# ---------------------------------------------------------------------------

# Keys that should NEVER be stored in valhalla.yaml
SENSITIVE_KEY_NAMES = frozenset({
    "nvidia_api_key", "openai_api_key", "anthropic_api_key",
    "huggingface_token", "github_token", "telegram_bot_token",
    "mesh_auth_token", "dashboard_auth_key",
    "api_key", "secret", "password", "token",
})


class CredentialStore:
    """Encrypted credential storage.

    Stores credentials in ~/.valhalla/credentials with:
    - AES-256-GCM encryption (machine-specific key)
    - File permissions 600 (owner only)
    - Never exposes full keys to dashboard API
    """

    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = Path(store_dir) if store_dir else DEFAULT_STORE_DIR
        self.store_file = self.store_dir / DEFAULT_STORE_FILE
        self._salt_file = self.store_dir / ".salt"
        self._key: Optional[bytes] = None
        self._data: dict = {}

        self._ensure_dir()
        self._load()

    def _ensure_dir(self) -> None:
        """Create store directory with secure permissions."""
        self.store_dir.mkdir(parents=True, exist_ok=True)

        # Set directory permissions to 700 (owner only)
        try:
            os.chmod(self.store_dir, stat.S_IRWXU)
        except OSError as e:
            log.warning("[credentials] Cannot set dir permissions: %s", e)

    def _get_salt(self) -> bytes:
        """Get or create the encryption salt."""
        if self._salt_file.exists():
            return self._salt_file.read_bytes()

        salt = os.urandom(32)
        self._salt_file.write_bytes(salt)
        try:
            os.chmod(self._salt_file, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return salt

    def _get_key(self) -> bytes:
        """Get the derived encryption key."""
        if self._key is None:
            machine_id = _get_machine_id()
            salt = self._get_salt()
            self._key = _derive_key(machine_id, salt)
        return self._key

    def _load(self) -> None:
        """Load credentials from disk."""
        if not self.store_file.exists():
            self._data = {}
            return

        try:
            raw = self.store_file.read_text(encoding="utf-8")
            self._data = json.loads(raw)
        except Exception as e:
            log.error("[credentials] Failed to load store: %s", e)
            self._data = {}

    def _save(self) -> None:
        """Save credentials to disk with secure permissions."""
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self.store_file.write_text(
            json.dumps(self._data, indent=2),
            encoding="utf-8",
        )

        # Set file permissions to 600 (owner read/write only)
        try:
            os.chmod(self.store_file, stat.S_IRUSR | stat.S_IWUSR)
        except OSError as e:
            log.warning("[credentials] Cannot set file permissions: %s", e)

        log.info("[credentials] Store saved (%d credentials)", len(self._data))

    # --- Public API ---

    def set(self, name: str, value: str) -> None:
        """Store a credential (encrypted)."""
        if not name or not value:
            raise ValueError("Credential name and value required")

        key = self._get_key()
        encrypted = _encrypt(value, key)
        self._data[name] = encrypted
        self._save()
        log.info("[credentials] Stored: %s", name)

    def get(self, name: str) -> Optional[str]:
        """Retrieve a credential (decrypted). Returns None if not found."""
        encrypted = self._data.get(name)
        if encrypted is None:
            return None

        try:
            key = self._get_key()
            return _decrypt(encrypted, key)
        except Exception as e:
            log.error("[credentials] Decrypt failed for '%s': %s", name, e)
            return None

    def get_masked(self, name: str) -> Optional[str]:
        """Get a masked version for dashboard display.

        Example: "nvapi-abc123def456" → "nvap...f456"
        """
        value = self.get(name)
        if value is None:
            return None

        if len(value) <= MASK_VISIBLE_CHARS * 2:
            return "***"

        prefix = value[:MASK_VISIBLE_CHARS]
        suffix = value[-MASK_VISIBLE_CHARS:]
        return f"{prefix}...{suffix}"

    def delete(self, name: str) -> bool:
        """Delete a credential. Returns True if existed."""
        if name in self._data:
            del self._data[name]
            self._save()
            log.info("[credentials] Deleted: %s", name)
            return True
        return False

    def list_names(self) -> list:
        """List stored credential names (never values)."""
        return list(self._data.keys())

    def exists(self, name: str) -> bool:
        """Check if a credential exists."""
        return name in self._data

    def get_status(self) -> dict:
        """Status for dashboard display (no values exposed)."""
        return {
            "store_path": str(self.store_file),
            "credential_count": len(self._data),
            "credentials": {
                name: {
                    "stored": True,
                    "method": entry.get("method", "unknown"),
                    "masked": self.get_masked(name),
                }
                for name, entry in self._data.items()
            },
            "encryption": "aes-256-gcm" if self._has_cryptography() else "xor-obfuscation",
            "permissions_ok": self._check_permissions(),
        }

    def _has_cryptography(self) -> bool:
        try:
            import cryptography
            return True
        except ImportError:
            return False

    def _check_permissions(self) -> bool:
        """Verify file permissions are 600 (owner only)."""
        if not self.store_file.exists():
            return True
        try:
            st = self.store_file.stat()
            mode = stat.S_IMODE(st.st_mode)
            return mode == (stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            return False


# ---------------------------------------------------------------------------
# Installer security helpers
# ---------------------------------------------------------------------------

def verify_gguf_checksum(file_path: Path, expected_sha256: str) -> bool:
    """Verify a downloaded GGUF file against its SHA256 checksum.

    Returns True if valid, False if tampered or missing.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        log.error("[installer] File not found: %s", file_path)
        return False

    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)

    actual = hasher.hexdigest()
    if actual != expected_sha256:
        log.critical(
            "[installer] 🔴 CHECKSUM MISMATCH for %s\n"
            "  Expected: %s\n  Got:      %s",
            file_path.name, expected_sha256, actual,
        )
        return False

    log.info("[installer] ✅ Checksum verified: %s", file_path.name)
    return True


def verify_binary_signature(binary_path: Path, expected_source: str = "llama.cpp") -> dict:
    """Verify a downloaded binary (llama-server, etc).

    Checks:
    - File exists and is executable
    - On macOS: codesign verification
    - File size reasonable (not truncated or suspiciously large)

    Returns dict with {valid, checks, warnings}.
    """
    result = {"valid": True, "checks": [], "warnings": []}
    binary_path = Path(binary_path)

    if not binary_path.exists():
        result["valid"] = False
        result["checks"].append("❌ File not found")
        return result

    # Size check (llama-server should be 5-200 MB)
    size = binary_path.stat().st_size
    if size < 1_000_000:  # < 1 MB
        result["valid"] = False
        result["checks"].append(f"❌ File too small ({size} bytes) — likely truncated")
        return result
    if size > 500_000_000:  # > 500 MB
        result["warnings"].append(f"⚠️ File unusually large ({size / 1e6:.0f} MB)")

    result["checks"].append(f"✅ Size OK ({size / 1e6:.1f} MB)")

    # Executable check
    if not os.access(binary_path, os.X_OK):
        result["warnings"].append("⚠️ Not executable — will need chmod +x")

    # macOS codesign
    if platform.system() == "Darwin":
        try:
            proc = subprocess.run(
                ["codesign", "-v", str(binary_path)],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                result["checks"].append("✅ macOS code signature valid")
            else:
                result["warnings"].append(
                    "⚠️ No valid code signature (common for community binaries)"
                )
        except Exception:
            result["warnings"].append("⚠️ Could not verify code signature")

    return result


def validate_pypi_package(package_name: str) -> dict:
    """Validate a Python package is from official PyPI.

    Checks the package exists on pypi.org and isn't a typosquat.
    Returns {valid, name, version, warnings}.
    """
    import urllib.request
    import urllib.error

    result = {"valid": False, "name": package_name, "warnings": []}

    # Known safe packages for brain installer
    TRUSTED_PACKAGES = frozenset({
        "mlx-lm", "mlx", "transformers", "huggingface-hub",
        "torch", "tokenizers", "safetensors",
    })

    if package_name not in TRUSTED_PACKAGES:
        result["warnings"].append(
            f"⚠️ '{package_name}' not in trusted package list"
        )

    # Check PyPI
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "valhalla-mesh/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result["valid"] = True
            result["version"] = data.get("info", {}).get("version", "unknown")
            result["author"] = data.get("info", {}).get("author", "unknown")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["warnings"].append(f"❌ Package '{package_name}' not found on PyPI")
        else:
            result["warnings"].append(f"⚠️ PyPI check failed: HTTP {e.code}")
    except Exception as e:
        result["warnings"].append(f"⚠️ PyPI check failed: {e}")

    return result


# ---------------------------------------------------------------------------
# Process isolation checks
# ---------------------------------------------------------------------------

def check_process_isolation(config: dict = None) -> dict:
    """Check inference server process isolation.

    Returns dict with isolation status and recommendations.
    """
    checks = []
    warnings = []

    # 1. Check if running as root
    if os.getuid() == 0:
        warnings.append("🔴 CRITICAL: Running as root — inference should use unprivileged user")
    else:
        checks.append(f"✅ Running as non-root user (uid={os.getuid()})")

    # 2. Check listen address
    listen_addr = "localhost"
    if config:
        listen_addr = config.get("inference", {}).get("listen", "localhost")

    if listen_addr in ("0.0.0.0", "::"):
        warnings.append(
            f"⚠️ Inference listening on {listen_addr} — accessible from network. "
            "Use localhost unless mesh discovery requires it."
        )
    else:
        checks.append(f"✅ Inference bound to {listen_addr}")

    # 3. Check model directory access
    model_dirs = [
        Path.home() / ".cache" / "huggingface",
        Path.home() / ".cache" / "mlx",
        Path.home() / ".ollama",
    ]
    for md in model_dirs:
        if md.exists():
            try:
                # Check it's not world-readable
                mode = stat.S_IMODE(md.stat().st_mode)
                if mode & stat.S_IROTH:
                    warnings.append(f"⚠️ {md} is world-readable")
                else:
                    checks.append(f"✅ {md} permissions OK")
            except Exception:
                pass

    return {
        "isolated": len(warnings) == 0,
        "checks": checks,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Telegram security helpers
# ---------------------------------------------------------------------------

# Patterns that should NEVER be sent via Telegram
_SENSITIVE_PATTERNS = [
    "api_key", "api-key", "secret", "password", "token",
    "private_key", "-----BEGIN", "nvapi-", "sk-", "ghp_",
    "auth_token", "credential",
]


def sanitize_telegram_message(message: str) -> str:
    """Remove sensitive information before sending via Telegram.

    Replaces any detected patterns with [REDACTED].
    """
    import re

    sanitized = message
    for pattern in _SENSITIVE_PATTERNS:
        # Replace the pattern and anything after it until whitespace/newline
        regex = re.compile(
            rf'({re.escape(pattern)})\s*[:=]\s*\S+',
            re.IGNORECASE,
        )
        sanitized = regex.sub(r'\1: [REDACTED]', sanitized)

    # Also redact anything that looks like a long API key
    sanitized = re.sub(
        r'[a-zA-Z0-9_\-]{32,}',
        '[REDACTED]',
        sanitized,
    )

    return sanitized


def validate_telegram_config(config: dict) -> list:
    """Validate Telegram plugin configuration for security.

    Returns list of issues. Empty = valid.
    """
    issues = []
    tg = config.get("telegram", {})

    # Bot token must be in credential store, not config
    bot_token = tg.get("bot_token", "")
    if bot_token and not bot_token.startswith("${"):
        issues.append(
            "🔴 CRITICAL: bot_token should be in credential store, "
            "not in valhalla.yaml. Use ${TELEGRAM_BOT_TOKEN} reference."
        )

    # Allowed users
    allowed = tg.get("allowed_users", [])
    if not allowed:
        issues.append(
            "⚠️ No allowed_users set — anyone with the bot link can interact. "
            "Consider adding Telegram user IDs."
        )

    # Notification events — check nothing leaks sensitive data
    notify_events = tg.get("notify_on", [])
    risky_events = {"config.changed", "credential.stored", "debug"}
    risky_found = set(notify_events) & risky_events
    if risky_found:
        issues.append(
            f"⚠️ Risky notification events: {risky_found}. "
            "These may leak sensitive configuration data."
        )

    return issues


def validate_telegram_user(user_id: int, allowed_users: list) -> bool:
    """Check if a Telegram user is allowed to interact.

    If allowed_users is empty, all users permitted (open mode).
    """
    if not allowed_users:
        return True  # Open mode
    return user_id in allowed_users

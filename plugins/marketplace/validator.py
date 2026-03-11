"""
plugins/marketplace/validator.py — Security validation for .valhalla agent packages.

Ensures agent packages can't contain executable code, leaked credentials,
or malicious content. Used by the marketplace import/export endpoints.

Heimdall Sprint 5.

Usage:
    from plugins.marketplace.validator import (
        validate_package,
        validate_manifest,
        scan_for_credentials,
        sign_package,
        verify_package_signature,
    )

    # On export:
    issues = validate_package(package_dir)
    if issues:
        reject(issues)
    manifest_hash = sign_package(package_dir)

    # On import:
    if not verify_package_signature(package_dir):
        reject("Package integrity check failed")
    issues = validate_package(package_dir)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Optional

log = logging.getLogger("heimdall.marketplace")

# ---------------------------------------------------------------------------
# Allowed file types in .valhalla packages
# ---------------------------------------------------------------------------

# ONLY data files. No executable code allowed.
ALLOWED_EXTENSIONS = frozenset({
    ".md",           # Soul, identity, philosopher prompt
    ".yaml", ".yml", # Manifest, config fragment
    ".json",         # Procedures, personality, metadata
    ".txt",          # Notes, descriptions
    ".png", ".jpg", ".jpeg", ".webp",  # Agent avatar
})

# Explicitly blocked — even if extension isn't in allowed list, we
# double-check for these dangerous patterns
BLOCKED_EXTENSIONS = frozenset({
    ".py", ".pyc", ".pyo", ".pyw",   # Python
    ".js", ".mjs", ".cjs", ".ts",    # JavaScript/TypeScript
    ".sh", ".bash", ".zsh",          # Shell
    ".rb", ".pl", ".php",            # Other scripting
    ".exe", ".dll", ".so", ".dylib", # Binaries
    ".bat", ".cmd", ".ps1",          # Windows scripts
    ".jar", ".class",                # Java
    ".wasm",                         # WebAssembly
})

# Max package size (50 MB)
MAX_PACKAGE_SIZE_BYTES = 50 * 1024 * 1024

# Max individual file size (5 MB)
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

# Max files in package
MAX_FILE_COUNT = 50

# ---------------------------------------------------------------------------
# Manifest validation
# ---------------------------------------------------------------------------

REQUIRED_MANIFEST_KEYS = {"name", "version", "description"}

ALLOWED_MANIFEST_KEYS = {
    "name", "version", "description", "author", "license",
    "model_requirements", "price", "category", "tags",
    "min_confidence", "procedures_count", "created_at",
    "sha256",  # Integrity hash (set by sign_package)
}

_SEMVER_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')
_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$')


def validate_manifest(manifest: dict) -> list:
    """Validate a .valhalla manifest.yaml for security issues.

    Returns list of issue strings. Empty = valid.
    """
    issues = []

    # Required keys
    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            issues.append(f"Missing required key: {key}")

    # No arbitrary keys
    extra_keys = set(manifest.keys()) - ALLOWED_MANIFEST_KEYS
    if extra_keys:
        issues.append(f"Unknown manifest keys (rejected): {extra_keys}")

    # Name validation
    name = manifest.get("name", "")
    if name and not _NAME_PATTERN.match(name):
        issues.append(
            f"Invalid name '{name}': must be alphanumeric with ._- (max 64 chars)"
        )

    # Version validation
    version = manifest.get("version", "")
    if version and not _SEMVER_PATTERN.match(version):
        issues.append(f"Invalid version '{version}': must be semver (X.Y.Z)")

    # Description length
    desc = manifest.get("description", "")
    if len(desc) > 2000:
        issues.append(f"Description too long ({len(desc)} > 2000 chars)")

    # Price validation
    price = manifest.get("price")
    if price is not None:
        if not isinstance(price, (int, float)) or price < 0:
            issues.append(f"Invalid price: {price} (must be non-negative number)")
        if isinstance(price, float) and price > 999.99:
            issues.append(f"Price too high: {price} (max $999.99)")

    # XSS in description (basic check for HTML tags)
    if desc:
        xss_issues = _check_xss(desc)
        issues.extend(xss_issues)

    # Author field XSS
    author = manifest.get("author", "")
    if author:
        xss_issues = _check_xss(author)
        issues.extend(xss_issues)

    return issues


# ---------------------------------------------------------------------------
# Credential scanning
# ---------------------------------------------------------------------------

# Patterns that suggest leaked credentials or PII
_CREDENTIAL_PATTERNS = [
    (r'["\']?(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}', "API key"),
    (r'["\']?(?:secret|password|passwd|pwd)["\']?\s*[:=]\s*["\']?[^\s"\']{8,}', "password/secret"),
    (r'(?:sk-|pk-|rk-)[a-zA-Z0-9]{20,}', "Stripe/OpenAI-style key"),
    (r'nvapi-[a-zA-Z0-9_\-]{20,}', "NVIDIA API key"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub personal access token"),
    (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth token"),
    (r'xox[bpsa]-[a-zA-Z0-9\-]{20,}', "Slack token"),
    (r'(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}', "AWS access key"),
    (r'-----BEGIN (?:RSA )?PRIVATE KEY-----', "Private key"),
    (r'-----BEGIN CERTIFICATE-----', "Certificate"),
    (r'\b(?:100\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', "Tailscale IP address"),
    (r'\b(?:\d{1,3}\.){3}\d{1,3}\b(?!.*(?:0\.0\.0\.0|127\.0\.0\.1|localhost))',
     "IP address (potential internal)"),
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "Email address (PII)"),
]

_CREDENTIAL_REGEXES = [
    (re.compile(pattern, re.IGNORECASE), desc)
    for pattern, desc in _CREDENTIAL_PATTERNS
]


def scan_for_credentials(text: str, filename: str = "") -> list:
    """Scan text for leaked credentials, API keys, PII.

    Returns list of (description, matched_text_preview) tuples.
    """
    findings = []
    for regex, desc in _CREDENTIAL_REGEXES:
        for match in regex.finditer(text):
            # Truncate match for logging (don't log full secrets)
            preview = match.group()[:20] + "..." if len(match.group()) > 20 else match.group()
            findings.append({
                "type": desc,
                "file": filename,
                "preview": preview,
                "position": match.start(),
            })
    return findings


# ---------------------------------------------------------------------------
# XSS checking
# ---------------------------------------------------------------------------

_XSS_PATTERNS = [
    re.compile(r'<script', re.IGNORECASE),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),  # onclick=, onerror=, etc.
    re.compile(r'<iframe', re.IGNORECASE),
    re.compile(r'<object', re.IGNORECASE),
    re.compile(r'<embed', re.IGNORECASE),
    re.compile(r'<form', re.IGNORECASE),
    re.compile(r'data:text/html', re.IGNORECASE),
    re.compile(r'vbscript:', re.IGNORECASE),
]


def _check_xss(text: str) -> list:
    """Check text for XSS patterns. Returns list of issue strings."""
    issues = []
    for pattern in _XSS_PATTERNS:
        if pattern.search(text):
            issues.append(f"XSS pattern detected: {pattern.pattern}")
    return issues


# ---------------------------------------------------------------------------
# Full package validation
# ---------------------------------------------------------------------------

def validate_package(package_dir: Path) -> list:
    """Validate an entire .valhalla package directory.

    Returns list of issue strings. Empty = safe.
    """
    issues = []
    package_dir = Path(package_dir)

    if not package_dir.is_dir():
        return [f"Package directory not found: {package_dir}"]

    # Count and size checks
    all_files = list(package_dir.rglob("*"))
    files_only = [f for f in all_files if f.is_file()]

    if len(files_only) > MAX_FILE_COUNT:
        issues.append(f"Too many files ({len(files_only)} > {MAX_FILE_COUNT})")

    total_size = sum(f.stat().st_size for f in files_only)
    if total_size > MAX_PACKAGE_SIZE_BYTES:
        issues.append(
            f"Package too large ({total_size / 1024 / 1024:.1f} MB > "
            f"{MAX_PACKAGE_SIZE_BYTES / 1024 / 1024:.0f} MB)"
        )

    # Validate each file
    for f in files_only:
        rel = f.relative_to(package_dir)

        # Extension check
        ext = f.suffix.lower()
        if ext in BLOCKED_EXTENSIONS:
            issues.append(f"BLOCKED: executable file '{rel}' ({ext})")
            continue

        if ext not in ALLOWED_EXTENSIONS:
            issues.append(f"BLOCKED: unknown file type '{rel}' ({ext})")
            continue

        # Size check
        size = f.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            issues.append(
                f"File too large: '{rel}' ({size / 1024 / 1024:.1f} MB > "
                f"{MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB)"
            )

        # Content scan (text files only)
        if ext in (".md", ".yaml", ".yml", ".json", ".txt"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")

                # Credential scan
                cred_findings = scan_for_credentials(content, str(rel))
                for finding in cred_findings:
                    issues.append(
                        f"CREDENTIAL: {finding['type']} in '{rel}' "
                        f"(near pos {finding['position']})"
                    )

                # XSS scan (for user-facing content)
                xss_issues = _check_xss(content)
                for xss in xss_issues:
                    issues.append(f"XSS in '{rel}': {xss}")

                # Embedded code check — look for code fences with executable languages
                if _has_executable_code_blocks(content):
                    # This is a WARNING, not a block — markdown docs may contain
                    # code examples
                    log.warning(
                        "[marketplace] Code block in '%s' — review manually", rel
                    )

            except Exception as e:
                issues.append(f"Cannot read '{rel}': {e}")

    # Manifest check
    manifest_path = package_dir / "manifest.yaml"
    if not manifest_path.exists():
        manifest_path = package_dir / "manifest.yml"
    if not manifest_path.exists():
        issues.append("Missing manifest.yaml")
    else:
        try:
            import yaml
            with open(manifest_path) as mf:
                manifest = yaml.safe_load(mf)
            if isinstance(manifest, dict):
                issues.extend(validate_manifest(manifest))
            else:
                issues.append("manifest.yaml is not a valid YAML dict")
        except Exception as e:
            issues.append(f"Cannot parse manifest.yaml: {e}")

    # Symlink check — no symlinks allowed (could escape sandbox)
    for f in all_files:
        if f.is_symlink():
            issues.append(f"BLOCKED: symlink '{f.relative_to(package_dir)}'")

    # Path traversal in filenames
    for f in files_only:
        rel_str = str(f.relative_to(package_dir))
        if ".." in rel_str:
            issues.append(f"BLOCKED: path traversal in '{rel_str}'")

    return issues


def _has_executable_code_blocks(content: str) -> bool:
    """Check if markdown contains code fences with executable languages."""
    exec_langs = {"python", "javascript", "js", "bash", "sh", "ruby", "php", "perl"}
    for match in re.finditer(r'```(\w+)', content):
        if match.group(1).lower() in exec_langs:
            return True
    return False


# ---------------------------------------------------------------------------
# Package signing (SHA256)
# ---------------------------------------------------------------------------

def sign_package(package_dir: Path) -> str:
    """Compute SHA256 hash of all package contents (excluding manifest hash field).

    Returns the hex digest. Also updates manifest.yaml with the hash.
    """
    package_dir = Path(package_dir)
    files = sorted(
        f for f in package_dir.rglob("*")
        if f.is_file() and f.name != "manifest.yaml" and f.name != "manifest.yml"
    )

    hasher = hashlib.sha256()
    for f in files:
        # Hash relative path + content
        rel = str(f.relative_to(package_dir))
        hasher.update(rel.encode("utf-8"))
        hasher.update(f.read_bytes())

    digest = hasher.hexdigest()

    # Update manifest with hash
    manifest_path = package_dir / "manifest.yaml"
    if not manifest_path.exists():
        manifest_path = package_dir / "manifest.yml"

    if manifest_path.exists():
        try:
            import yaml
            with open(manifest_path) as mf:
                manifest = yaml.safe_load(mf) or {}
            manifest["sha256"] = digest
            with open(manifest_path, "w") as mf:
                yaml.dump(manifest, mf, default_flow_style=False, sort_keys=False)
        except Exception as e:
            log.error("[marketplace] Failed to update manifest with hash: %s", e)

    log.info("[marketplace] Package signed: %s...%s", digest[:8], digest[-8:])
    return digest


def verify_package_signature(package_dir: Path) -> bool:
    """Verify the SHA256 hash in manifest matches the actual content.

    Returns True if valid, False if tampered or missing.
    """
    package_dir = Path(package_dir)

    manifest_path = package_dir / "manifest.yaml"
    if not manifest_path.exists():
        manifest_path = package_dir / "manifest.yml"
    if not manifest_path.exists():
        log.warning("[marketplace] No manifest found for signature check")
        return False

    try:
        import yaml
        with open(manifest_path) as mf:
            manifest = yaml.safe_load(mf) or {}
    except Exception:
        return False

    expected_hash = manifest.get("sha256")
    if not expected_hash:
        log.warning("[marketplace] No sha256 in manifest — unsigned package")
        return False

    # Recompute hash (same algorithm as sign_package)
    files = sorted(
        f for f in package_dir.rglob("*")
        if f.is_file() and f.name != "manifest.yaml" and f.name != "manifest.yml"
    )

    hasher = hashlib.sha256()
    for f in files:
        rel = str(f.relative_to(package_dir))
        hasher.update(rel.encode("utf-8"))
        hasher.update(f.read_bytes())

    actual_hash = hasher.hexdigest()

    if actual_hash != expected_hash:
        log.critical(
            "[marketplace] 🔴 INTEGRITY CHECK FAILED for %s "
            "(expected: %s, got: %s)",
            package_dir.name, expected_hash[:16], actual_hash[:16],
        )
        return False

    log.info("[marketplace] ✅ Package integrity verified: %s", package_dir.name)
    return True


# ---------------------------------------------------------------------------
# Marketplace trust helpers
# ---------------------------------------------------------------------------

_REVIEW_MIN_LENGTH = 10
_REVIEW_MAX_LENGTH = 2000


def validate_review(review: dict) -> list:
    """Validate a marketplace review for security.

    Returns list of issues. Empty = valid.
    """
    issues = []

    # Rating
    rating = review.get("rating")
    if not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
        issues.append("Rating must be 1-5")

    # Text
    text = review.get("text", "")
    if len(text) < _REVIEW_MIN_LENGTH:
        issues.append(f"Review too short ({len(text)} < {_REVIEW_MIN_LENGTH})")
    if len(text) > _REVIEW_MAX_LENGTH:
        issues.append(f"Review too long ({len(text)} > {_REVIEW_MAX_LENGTH})")

    # XSS in review text
    if text:
        xss_issues = _check_xss(text)
        issues.extend(xss_issues)

    # Auth check (this is enforced at endpoint level, but validate presence)
    if not review.get("author"):
        issues.append("Review must have an author")

    return issues


def validate_price_change(
    current_price: Optional[float],
    new_price: Optional[float],
    is_admin: bool = False,
) -> list:
    """Validate a price change request.

    Price changes after publish require admin approval.
    Returns list of issues.
    """
    issues = []

    if new_price is not None and new_price < 0:
        issues.append("Price cannot be negative")

    if current_price is not None and new_price is not None:
        if current_price != new_price and not is_admin:
            issues.append(
                "Price change requires admin approval. "
                f"Current: ${current_price:.2f}, Requested: ${new_price:.2f}"
            )

    return issues

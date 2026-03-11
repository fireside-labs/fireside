"""
middleware/task_integrity.py — Task persistence security + context compaction guardrails +
                               cloud deploy hardening + Discord bot security + rebrand audit.

Covers Sprint 11 (rebrand to Fireside) and Sprint 12 (task persistence, context compaction,
Discord, cloud deploy) security requirements.

Heimdall Sprint 11+12.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import stat
import time
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("heimdall.task_integrity")

# ---------------------------------------------------------------------------
# Task Persistence Security
# ---------------------------------------------------------------------------

class TaskCheckpoint:
    """Secure task persistence with integrity verification.

    Tasks write checkpoints to `data/tasks/{task_id}.json`. Each checkpoint
    is integrity-checked to prevent tampering and validated before resume.
    """

    VALID_STATUSES = frozenset({
        "pending", "in_progress", "paused", "completed", "failed", "resuming",
    })

    def __init__(self, tasks_dir: Path):
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(
        self,
        task_id: str,
        agent: str,
        step: int,
        total_steps: int,
        status: str = "in_progress",
        data: Optional[dict] = None,
    ) -> dict:
        """Create or update a task checkpoint.

        Returns the checkpoint with integrity hash.
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")

        if step < 0 or step > total_steps:
            raise ValueError(f"Step {step} out of range (0-{total_steps})")

        checkpoint = {
            "task_id": task_id,
            "agent": agent,
            "step": step,
            "total_steps": total_steps,
            "status": status,
            "checkpoint_data": data or {},
            "created_at": time.time(),
            "updated_at": time.time(),
            "version": 1,
        }

        # Compute integrity hash
        checkpoint["integrity_hash"] = self._compute_hash(checkpoint)

        # Save
        path = self.tasks_dir / f"{task_id}.json"
        path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")

        # Set file permissions to 600
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

        log.info(
            "[task] Checkpoint: %s step %d/%d (%s)",
            task_id[:8], step, total_steps, status,
        )
        return checkpoint

    def validate_checkpoint(self, task_id: str) -> dict:
        """Validate a checkpoint file hasn't been tampered with.

        Returns {valid, checkpoint, issues}.
        """
        result = {"valid": False, "checkpoint": None, "issues": []}
        path = self.tasks_dir / f"{task_id}.json"

        if not path.exists():
            result["issues"].append(f"Task {task_id} not found")
            return result

        try:
            checkpoint = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            result["issues"].append(f"Corrupt checkpoint: {e}")
            return result

        # Verify integrity hash
        stored_hash = checkpoint.pop("integrity_hash", None)
        expected_hash = self._compute_hash(checkpoint)
        checkpoint["integrity_hash"] = stored_hash  # restore

        if stored_hash != expected_hash:
            result["issues"].append(
                "Integrity check FAILED — checkpoint has been tampered with"
            )
            log.critical("[task] 🔴 Checkpoint tampering detected: %s", task_id)
            return result

        # Validate status
        if checkpoint.get("status") not in self.VALID_STATUSES:
            result["issues"].append(f"Invalid status: {checkpoint.get('status')}")

        # Validate step bounds
        step = checkpoint.get("step", -1)
        total = checkpoint.get("total_steps", 0)
        if step < 0 or step > total:
            result["issues"].append(f"Step {step} out of range (0-{total})")

        result["valid"] = len(result["issues"]) == 0
        result["checkpoint"] = checkpoint
        return result

    def get_resumable_tasks(self) -> list:
        """Find all tasks that need resuming (status=in_progress).

        Returns list of validated checkpoints.
        """
        resumable = []
        for task_file in self.tasks_dir.glob("*.json"):
            task_id = task_file.stem
            validation = self.validate_checkpoint(task_id)
            if (
                validation["valid"]
                and validation["checkpoint"].get("status") == "in_progress"
            ):
                resumable.append(validation["checkpoint"])

        # Sort by updated_at (oldest first — resume in order)
        resumable.sort(key=lambda t: t.get("updated_at", 0))
        return resumable

    def validate_resume(self, task_id: str) -> dict:
        """Full validation before resuming a task.

        Returns {can_resume, checkpoint, gap_minutes, issues}.
        """
        validation = self.validate_checkpoint(task_id)
        result = {
            "can_resume": False,
            "checkpoint": validation.get("checkpoint"),
            "gap_minutes": 0,
            "issues": validation.get("issues", []),
        }

        if not validation["valid"]:
            return result

        cp = validation["checkpoint"]

        # Calculate offline gap
        gap = time.time() - cp.get("updated_at", time.time())
        result["gap_minutes"] = round(gap / 60, 1)

        # Reject stale tasks (> 24 hours)
        if gap > 86400:
            result["issues"].append(
                f"Task stale ({result['gap_minutes']:.0f} min offline). "
                "Consider restarting instead of resuming."
            )
            return result

        # Must be in_progress to resume
        if cp.get("status") != "in_progress":
            result["issues"].append(
                f"Cannot resume — status is '{cp.get('status')}', not 'in_progress'"
            )
            return result

        result["can_resume"] = True
        return result

    def _compute_hash(self, checkpoint: dict) -> str:
        """Compute SHA256 integrity hash of checkpoint data."""
        # Hash everything except the hash itself
        data = {k: v for k, v in checkpoint.items() if k != "integrity_hash"}
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()


# ---------------------------------------------------------------------------
# Context Compaction Security
# ---------------------------------------------------------------------------

class ContextCompactionGuard:
    """Validate context compaction to prevent injection via compressed history.

    When long conversations are compressed, an attacker could inject
    instructions into early messages that survive compression.
    """

    # Patterns that should trigger review during compaction
    INJECTION_IN_HISTORY = [
        r"SYSTEM:\s",
        r"\[INST\]",
        r"\[/INST\]",
        r"<<SYS>>",
        r"<\|im_start\|>system",
        r"Human:\s.*\nAssistant:\s",  # prompt format injection
        r"ignore\s+(all\s+)?previous",
        r"new\s+instructions?\s*:",
        r"you\s+are\s+now",
    ]

    _PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_IN_HISTORY]

    def validate_compacted_context(self, compressed_block: str) -> dict:
        """Scan compressed context for injection attempts.

        Returns {safe, issues, suspicious_patterns}.
        """
        issues = []
        suspicious = []

        for pattern in self._PATTERNS:
            matches = pattern.findall(compressed_block)
            if matches:
                suspicious.append(matches[0][:50])
                issues.append(f"Suspicious pattern in compressed context: {matches[0][:50]}")

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "suspicious_patterns": suspicious,
        }

    def validate_compaction_ratio(
        self,
        original_tokens: int,
        compressed_tokens: int,
    ) -> dict:
        """Validate compression ratio is reasonable.

        Too little compression = waste. Too much = information loss.
        """
        if original_tokens == 0:
            return {"valid": True, "ratio": 0, "issues": []}

        ratio = compressed_tokens / original_tokens
        issues = []

        if ratio > 0.8:
            issues.append(
                f"Low compression ({ratio:.0%}). Consider more aggressive summarization."
            )
        elif ratio < 0.05:
            issues.append(
                f"Extreme compression ({ratio:.0%}). May lose critical context."
            )

        return {
            "valid": len(issues) == 0,
            "ratio": ratio,
            "issues": issues,
        }


# ---------------------------------------------------------------------------
# Discord Bot Security
# ---------------------------------------------------------------------------

def validate_discord_config(config: dict) -> list:
    """Validate Discord bot configuration for security.

    Returns list of issues.
    """
    issues = []
    discord = config.get("discord", {})

    # Bot token must be in credential store
    bot_token = discord.get("bot_token", "")
    if bot_token and not bot_token.startswith("${"):
        issues.append(
            "🔴 CRITICAL: Discord bot_token should be in credential store, "
            "not in config file. Use ${DISCORD_BOT_TOKEN}."
        )

    # Permission integer — check it's minimal
    permissions = discord.get("permissions", 0)
    # Dangerous permissions (bit flags)
    DANGEROUS_PERMS = {
        0x00000008: "ADMINISTRATOR",
        0x00000004: "BAN_MEMBERS",
        0x00000002: "KICK_MEMBERS",
        0x00000010: "MANAGE_CHANNELS",
        0x00000020: "MANAGE_GUILD",
        0x20000000: "MANAGE_WEBHOOKS",
        0x10000000: "MANAGE_ROLES",
    }
    for bit, name in DANGEROUS_PERMS.items():
        if permissions & bit:
            issues.append(f"⚠️ Discord bot has {name} permission — minimize scope")

    # Allowed guilds (servers)
    allowed_guilds = discord.get("allowed_guilds", [])
    if not allowed_guilds:
        issues.append(
            "⚠️ No allowed_guilds set — bot can be added to any server"
        )

    # Slash command rate limiting
    if not discord.get("rate_limit_enabled", True):
        issues.append("⚠️ Discord rate limiting disabled")

    return issues


def validate_discord_interaction(
    interaction_type: str,
    user_id: str,
    guild_id: str,
    allowed_guilds: list,
) -> dict:
    """Validate a Discord interaction request.

    Returns {allowed, issues}.
    """
    issues = []

    if allowed_guilds and guild_id not in allowed_guilds:
        issues.append(f"Guild {guild_id} not in allowed list")

    # Reject DM interactions (no guild context)
    if not guild_id:
        issues.append("DM interactions not allowed — use guild channels only")

    return {
        "allowed": len(issues) == 0,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Cloud Deploy Security
# ---------------------------------------------------------------------------

def validate_cloud_deploy_template(template: dict) -> list:
    """Validate a cloud deployment template for security.

    Checks Lightsail/DigitalOcean/Hetzner templates.

    Returns list of issues.
    """
    issues = []

    # Firewall rules
    firewall = template.get("firewall", {})
    allowed_ports = firewall.get("allow_inbound", [])

    # Only SSH (22) and HTTPS (443) should be open
    SAFE_PORTS = {22, 443}
    for rule in allowed_ports:
        port = rule.get("port", 0)
        if port not in SAFE_PORTS:
            issues.append(
                f"⚠️ Port {port} open to internet. "
                f"Only ports {SAFE_PORTS} should be public."
            )

    # API port (8337) should NOT be public — use reverse proxy
    if any(r.get("port") == 8337 for r in allowed_ports):
        issues.append(
            "🔴 Port 8337 (API) directly exposed! "
            "Use nginx/caddy reverse proxy with TLS."
        )

    # SSH key auth (no password)
    ssh = template.get("ssh", {})
    if ssh.get("password_auth", True):
        issues.append(
            "🔴 Password SSH auth enabled. Use key-based auth only."
        )

    # Root login
    if ssh.get("root_login", True):
        issues.append(
            "⚠️ Root SSH login enabled. Disable and use non-root user."
        )

    # Secrets management
    secrets = template.get("secrets", {})
    for key, value in secrets.items():
        if not value.startswith("${") and len(value) > 10:
            issues.append(
                f"🔴 Secret '{key}' appears hardcoded. Use environment variable."
            )

    # Auto-updates
    if not template.get("auto_updates", False):
        issues.append("⚠️ Auto security updates not enabled")

    # Backup
    if not template.get("backups", False):
        issues.append("⚠️ Automated backups not configured")

    return issues


def generate_cloud_firewall_rules() -> dict:
    """Generate secure firewall rules for cloud deployment.

    Returns rules dict suitable for DigitalOcean/Lightsail/Hetzner.
    """
    return {
        "inbound": [
            {"port": 22, "protocol": "tcp", "source": "0.0.0.0/0", "note": "SSH (key-auth only)"},
            {"port": 443, "protocol": "tcp", "source": "0.0.0.0/0", "note": "HTTPS (reverse proxy)"},
        ],
        "outbound": [
            {"port": 443, "protocol": "tcp", "destination": "0.0.0.0/0", "note": "HTTPS (updates, PyPI, HuggingFace)"},
            {"port": 53, "protocol": "udp", "destination": "0.0.0.0/0", "note": "DNS"},
        ],
        "blocked": [
            {"port": 8337, "note": "API — only via reverse proxy, not direct"},
            {"port": 11434, "note": "Ollama — localhost only"},
            {"port": 8080, "note": "llama-server — localhost only"},
        ],
        "notes": [
            "API (8337) proxied through nginx/caddy on 443 with TLS",
            "Inference servers (Ollama, llama-server) NEVER exposed to internet",
            "SSH: key-auth only, fail2ban enabled, root login disabled",
        ],
    }


# ---------------------------------------------------------------------------
# Rebrand Security Audit
# ---------------------------------------------------------------------------

# Patterns that should NOT appear in public-facing code after rebrand
_REBRAND_LEAKS = [
    r"valhalla\.ai",              # Old domain
    r"valhalla-mesh",             # Old repo name
    r"api\.valhalla",             # Old API URL
    r"releases\.valhalla",        # Old update URL
    r"valhalla_auth_key",         # Old env var names
    r"valhalla_mesh_token",       # Old token names
]

_REBRAND_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _REBRAND_LEAKS]

# Internal references that are OK (Norse theme stays)
_REBRAND_SAFE = frozenset({
    "valhalla.yaml",              # Config file name (internal)
    "valhalla",                   # Guild hall theme name
    "themes/valhalla",            # Theme directory
    "color-void",                # CSS theme var (Norse aesthetic)
})


def audit_rebrand(file_content: str, filename: str = "") -> dict:
    """Audit a file for leftover Valhalla references after rebrand.

    Returns {clean, issues}.
    """
    issues = []

    for pattern in _REBRAND_PATTERNS:
        matches = pattern.findall(file_content)
        for match in matches:
            # Check if it's a safe internal reference (exact match only)
            if match.lower() in _REBRAND_SAFE:
                continue
            issues.append(f"Leftover reference: '{match}' in {filename or 'file'}")

    return {
        "clean": len(issues) == 0,
        "issues": issues,
    }


def audit_install_script(script_content: str) -> list:
    """Audit install.sh for security best practices.

    Returns list of issues.
    """
    issues = []

    # Downloads should use HTTPS
    http_downloads = re.findall(r"http://[^\s\"']+", script_content)
    for url in http_downloads:
        issues.append(f"🔴 Insecure download (HTTP): {url} — use HTTPS")

    # curl | bash pattern (dangerous)
    if re.search(r"curl\s+.*\|\s*(bash|sh)", script_content):
        issues.append(
            "⚠️ curl | bash pattern detected. Consider downloading then executing "
            "with checksum verification."
        )

    # Running as root
    if "sudo" in script_content and "EUID" not in script_content:
        issues.append(
            "⚠️ Uses sudo without checking if already root (EUID check)"
        )

    # Checksum verification for downloads
    if "sha256" not in script_content.lower() and "checksum" not in script_content.lower():
        if "curl" in script_content or "wget" in script_content:
            issues.append(
                "⚠️ Downloads without checksum verification. Add SHA256 check."
            )

    # Temp file cleanup
    if "mktemp" in script_content and "trap" not in script_content:
        issues.append(
            "⚠️ Creates temp files without cleanup trap. Add: trap 'rm -rf $tmpdir' EXIT"
        )

    return issues

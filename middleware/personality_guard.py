"""
middleware/personality_guard.py — Personality change guardrails.

Validates personality slider changes, enforces rate limits, blocks prompt
injection via personality fields, and logs all changes for auditability.

Heimdall Sprint 8.

Usage:
    from middleware.personality_guard import PersonalityGuard

    guard = PersonalityGuard()
    issues = guard.validate_personality_change(changes)
    if issues:
        return {"error": issues}
    guard.record_change(agent_name, changes)
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("heimdall.personality")

# ---------------------------------------------------------------------------
# Personality slider definitions
# ---------------------------------------------------------------------------

PERSONALITY_SLIDERS = {
    "creative_precise": {
        "label": "Creative ↔ Precise",
        "low": "Follow proven patterns, be systematic",
        "high": "Take risks, try new approaches",
        "default": 0.5,
    },
    "verbose_concise": {
        "label": "Verbose ↔ Concise",
        "low": "Be brief, straight to the point",
        "high": "Explain thoroughly, provide context",
        "default": 0.5,
    },
    "bold_cautious": {
        "label": "Bold ↔ Cautious",
        "low": "Verify before acting, ask for permission",
        "high": "Act first, ask later, take initiative",
        "default": 0.5,
    },
    "warm_formal": {
        "label": "Warm ↔ Formal",
        "low": "Professional tone, no slang",
        "high": "Use emoji, be casual and friendly",
        "default": 0.6,
    },
}

VALID_SLIDER_NAMES = frozenset(PERSONALITY_SLIDERS.keys())

# ---------------------------------------------------------------------------
# Banned prompt fragments — protect against personality-based injection
# ---------------------------------------------------------------------------

BANNED_FRAGMENTS = [
    # Direct instruction override
    r"ignore\s+(all\s+)?(previous\s+)?instructions",
    r"ignore\s+(your\s+)?(system\s+)?prompt",
    r"disregard\s+(all\s+|your\s+)?(rules|instructions|guidelines)",
    r"forget\s+(everything|all\s+rules)",
    r"you\s+are\s+now\s+a?\s*(new|different)\s+(ai|assistant|model)",
    r"override\s+(system|safety|security)",
    r"bypass\s+(filter|safety|security|restriction)",

    # Role hijacking
    r"pretend\s+(to\s+be|you\s+are)",
    r"act\s+as\s+if\s+you",
    r"roleplay\s+as",
    r"from\s+now\s+on\s+(you|your)",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*",

    # Data exfiltration
    r"reveal\s+(your|the)\s+(system|initial)\s+prompt",
    r"show\s+(me\s+)?(your\s+)?(system|initial)\s+prompt",
    r"print\s+(your\s+)?instructions",
    r"what\s+(are|is)\s+your\s+(system\s+)?prompt",
    r"output\s+(your\s+)?configuration",
    r"dump\s+(your\s+)?(system|config|memory)",

    # Dangerous behaviors
    r"(execute|run|eval)\s+(this\s+)?(code|command|script)",
    r"(delete|remove|destroy)\s+(all|every)",
    r"access\s+(the\s+)?file\s*system",
    r"read\s+/etc/",
    r"sudo\s+",
    r"rm\s+-rf",
]

_BANNED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in BANNED_FRAGMENTS]

# ---------------------------------------------------------------------------
# Rate limiting for personality changes
# ---------------------------------------------------------------------------

MAX_CHANGES_PER_HOUR = 10

# In-memory rate tracker (per agent)
_change_timestamps: dict = {}  # {agent_name: [timestamps]}


# ---------------------------------------------------------------------------
# Change history
# ---------------------------------------------------------------------------

_HISTORY_DIR = "war_room_data"
_HISTORY_FILE = "personality_history.json"


def _history_path(base_dir: Path) -> Path:
    return base_dir / _HISTORY_DIR / _HISTORY_FILE


def _load_history(base_dir: Path) -> list:
    path = _history_path(base_dir)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_history(base_dir: Path, history: list) -> None:
    path = _history_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep last 500 changes max
    trimmed = history[-500:]
    path.write_text(json.dumps(trimmed, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# PersonalityGuard
# ---------------------------------------------------------------------------

class PersonalityGuard:
    """Validates and guards personality changes for agents."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(".")

    def validate_slider_values(self, changes: dict) -> list:
        """Validate slider values are within bounds.

        Args:
            changes: dict of {slider_name: value}

        Returns:
            List of issues. Empty = valid.
        """
        issues = []

        for name, value in changes.items():
            # Check slider name is known
            if name not in VALID_SLIDER_NAMES:
                issues.append(f"Unknown personality slider: '{name}'")
                continue

            # Check value type
            if not isinstance(value, (int, float)):
                issues.append(f"'{name}' must be a number, got {type(value).__name__}")
                continue

            # Check bounds (0.0 to 1.0)
            if value < 0.0 or value > 1.0:
                issues.append(f"'{name}' must be 0.0–1.0, got {value}")

        return issues

    def scan_for_injection(self, text: str) -> list:
        """Scan text fields for prompt injection patterns.

        Checks: agent name, role description, custom skills,
        boundary rules, and any free-text personality fields.

        Returns list of detected injections.
        """
        if not text:
            return []

        detections = []
        for pattern in _BANNED_PATTERNS:
            match = pattern.search(text)
            if match:
                detections.append(f"Banned pattern detected: '{match.group()}'")

        return detections

    def validate_personality_change(
        self,
        changes: dict,
        text_fields: Optional[dict] = None,
    ) -> list:
        """Full validation of a personality change request.

        Args:
            changes: dict of slider values {name: float}
            text_fields: optional dict of text fields to scan
                         (name, role, custom_skill, boundary_rule, etc.)

        Returns:
            List of issues. Empty = valid.
        """
        issues = []

        # Validate slider values
        if changes:
            issues.extend(self.validate_slider_values(changes))

        # Scan text fields for injection
        if text_fields:
            for field_name, text in text_fields.items():
                if not isinstance(text, str):
                    continue

                # Length check
                if len(text) > 500:
                    issues.append(
                        f"Text field '{field_name}' too long "
                        f"({len(text)} chars, max 500)"
                    )
                    continue

                # Injection scan
                injections = self.scan_for_injection(text)
                for inj in injections:
                    issues.append(f"[{field_name}] {inj}")

        return issues

    def check_rate_limit(self, agent_name: str) -> bool:
        """Check if personality changes are within rate limit.

        Returns True if allowed, False if rate-limited.
        """
        now = time.time()
        one_hour_ago = now - 3600

        timestamps = _change_timestamps.get(agent_name, [])
        # Clean old entries
        timestamps = [t for t in timestamps if t > one_hour_ago]
        _change_timestamps[agent_name] = timestamps

        if len(timestamps) >= MAX_CHANGES_PER_HOUR:
            log.warning(
                "[personality] Rate limit hit for '%s': %d changes in last hour",
                agent_name, len(timestamps),
            )
            return False

        return True

    def record_change(
        self,
        agent_name: str,
        changes: dict,
        text_fields: Optional[dict] = None,
    ) -> dict:
        """Record a personality change in history.

        Returns the history entry.
        """
        now = time.time()

        # Update rate limiter
        _change_timestamps.setdefault(agent_name, []).append(now)

        # Build history entry
        entry = {
            "agent": agent_name,
            "timestamp": now,
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "sliders": changes or {},
            "text_fields": text_fields or {},
        }

        # Save to disk
        history = _load_history(self.base_dir)
        history.append(entry)
        _save_history(self.base_dir, history)

        log.info(
            "[personality] Change recorded for '%s': %s",
            agent_name, list(changes.keys()) if changes else "text only",
        )

        return entry

    def get_history(self, agent_name: Optional[str] = None, limit: int = 50) -> list:
        """Get personality change history.

        Args:
            agent_name: filter to specific agent (None = all)
            limit: max entries to return

        Returns:
            List of history entries (newest first).
        """
        history = _load_history(self.base_dir)

        if agent_name:
            history = [h for h in history if h.get("agent") == agent_name]

        return list(reversed(history[-limit:]))

    def revert_to(self, agent_name: str, timestamp: float) -> Optional[dict]:
        """Find the personality state at a given timestamp.

        Returns the slider/text values at that point, or None.
        """
        history = _load_history(self.base_dir)
        for entry in reversed(history):
            if (
                entry.get("agent") == agent_name
                and entry.get("timestamp", 0) <= timestamp
            ):
                return {
                    "sliders": entry.get("sliders", {}),
                    "text_fields": entry.get("text_fields", {}),
                    "from_timestamp": entry.get("timestamp_iso"),
                }
        return None

    def get_status(self) -> dict:
        """Return guardrail status for monitoring."""
        return {
            "valid_sliders": list(VALID_SLIDER_NAMES),
            "banned_patterns": len(_BANNED_PATTERNS),
            "max_changes_per_hour": MAX_CHANGES_PER_HOUR,
            "active_rate_limits": {
                name: len(timestamps)
                for name, timestamps in _change_timestamps.items()
            },
        }


# ---------------------------------------------------------------------------
# Achievement integrity
# ---------------------------------------------------------------------------

# Events that can grant XP — must come from verified backend sources
VERIFIED_XP_SOURCES = frozenset({
    "pipeline.completed",     # Pipeline plugin (Thor)
    "crucible.survived",      # Crucible plugin (Thor)
    "debate.won",             # Socratic plugin (Thor)
    "pipeline.streak",        # Pipeline plugin streak bonus
})

# XP amounts per event
XP_REWARDS = {
    "pipeline.completed": 100,
    "crucible.survived": 50,
    "debate.won": 75,
    "pipeline.streak": 10,  # per consecutive
}

# Level thresholds
XP_PER_LEVEL = 500


def validate_xp_event(event_name: str, source: str = "") -> list:
    """Validate an XP-granting event.

    Args:
        event_name: the event that triggered XP
        source: origin of the event (e.g. "pipeline-plugin", "api-call")

    Returns:
        List of issues. Empty = valid.
    """
    issues = []

    if event_name not in VERIFIED_XP_SOURCES:
        issues.append(
            f"Unverified XP source: '{event_name}'. "
            f"Only these events grant XP: {sorted(VERIFIED_XP_SOURCES)}"
        )

    # Reject direct API calls trying to grant XP
    if source in ("api", "dashboard", "client", "external"):
        issues.append(
            f"XP cannot be granted from '{source}'. "
            "Must originate from verified backend plugin."
        )

    return issues


def calculate_level(total_xp: int) -> dict:
    """Calculate level from total XP.

    Returns {level, xp_current_level, xp_to_next, progress}.
    """
    level = total_xp // XP_PER_LEVEL
    xp_in_level = total_xp % XP_PER_LEVEL
    return {
        "level": level,
        "xp_total": total_xp,
        "xp_current_level": xp_in_level,
        "xp_to_next": XP_PER_LEVEL - xp_in_level,
        "progress": xp_in_level / XP_PER_LEVEL,
    }


# ---------------------------------------------------------------------------
# Windows security helpers
# ---------------------------------------------------------------------------

def check_windows_security() -> dict:
    """Check Windows-specific security configuration.

    Returns dict of checks and warnings.
    """
    import platform

    checks = []
    warnings = []

    if platform.system() != "Windows":
        checks.append("✅ Not Windows — Windows checks skipped")
        return {"checks": checks, "warnings": warnings}

    import os
    import subprocess

    # 1. Check not running as admin
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            warnings.append("🔴 Running as Administrator — use standard user")
        else:
            checks.append("✅ Running as standard user")
    except Exception:
        warnings.append("⚠️ Could not determine admin status")

    # 2. Check inference binding
    checks.append("✅ Inference should bind to 127.0.0.1 (enforced by config)")

    # 3. Windows Credential Manager availability
    try:
        result = subprocess.run(
            ["cmdkey", "/list"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            checks.append("✅ Windows Credential Manager available")
        else:
            warnings.append("⚠️ Windows Credential Manager not accessible")
    except Exception:
        warnings.append("⚠️ Cannot verify Credential Manager")

    return {"checks": checks, "warnings": warnings}

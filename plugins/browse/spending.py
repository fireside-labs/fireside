"""
browse/spending.py — Local spending controls for browser automation.

All data stays on the user's machine. No money flows through Valhalla.
The AI uses the user's existing saved payment methods on websites.
This module just enforces spending limits and logs transactions.

Config: ~/.fireside/spending.json
Ledger: ~/.fireside/spending_ledger.json
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.browse.spending")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIRESIDE_DIR = Path.home() / ".fireside"
CONFIG_PATH = FIRESIDE_DIR / "spending.json"
LEDGER_PATH = FIRESIDE_DIR / "spending_ledger.json"

# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "enabled": True,
    "weekly_limit": 50.00,       # max spend per week
    "per_action_limit": 25.00,   # max per single purchase
    "require_approval_above": 10.00,  # ask user above this amount
    "unusual_price_multiplier": 2.0,  # flag if price >2x the usual
    "blocked_sites": [],         # domains to never purchase from
    "allowed_sites": [],         # if non-empty, ONLY these sites allowed
}


# ---------------------------------------------------------------------------
# Config management
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load spending config, creating defaults if needed."""
    FIRESIDE_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # Merge with defaults for any missing keys
            merged = {**DEFAULT_CONFIG, **cfg}
            return merged
        except Exception as e:
            log.warning("[spending] Config parse error: %s — using defaults", e)

    # Create default config
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    log.info("[spending] Created default config: %s", CONFIG_PATH)
    return DEFAULT_CONFIG.copy()


def _load_ledger() -> list:
    """Load the spending ledger."""
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_ledger(ledger: list):
    """Save the spending ledger."""
    FIRESIDE_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Core: check_purchase
# ---------------------------------------------------------------------------

def check_purchase(description: str, estimated_cost: float,
                   site: str = "") -> dict:
    """
    Check whether a purchase should be allowed.

    Returns:
        {
            "allowed": bool,
            "requires_approval": bool,
            "reason": str,
            "weekly_spent": float,
            "weekly_remaining": float,
        }
    """
    config = _load_config()

    # Spending disabled entirely
    if not config.get("enabled", True):
        return {
            "allowed": False,
            "requires_approval": False,
            "reason": "Spending is disabled. Enable in ~/.fireside/spending.json",
        }

    # Site blocklist
    blocked = config.get("blocked_sites", [])
    if site and any(b.lower() in site.lower() for b in blocked):
        return {
            "allowed": False,
            "requires_approval": False,
            "reason": f"Site '{site}' is on the blocked list",
        }

    # Site allowlist (if set, only these sites are allowed)
    allowed_sites = config.get("allowed_sites", [])
    if allowed_sites and site:
        if not any(a.lower() in site.lower() for a in allowed_sites):
            return {
                "allowed": False,
                "requires_approval": False,
                "reason": f"Site '{site}' is not on the allowed list",
            }

    # Per-action limit
    per_action = config.get("per_action_limit", 25.0)
    if estimated_cost > per_action:
        return {
            "allowed": False,
            "requires_approval": False,
            "reason": f"${estimated_cost:.2f} exceeds per-action limit of ${per_action:.2f}",
        }

    # Weekly limit
    weekly_limit = config.get("weekly_limit", 50.0)
    weekly_spent = _get_weekly_spent()
    weekly_remaining = weekly_limit - weekly_spent

    if estimated_cost > weekly_remaining:
        return {
            "allowed": False,
            "requires_approval": False,
            "reason": (
                f"${estimated_cost:.2f} would exceed weekly limit. "
                f"Spent: ${weekly_spent:.2f} / ${weekly_limit:.2f}. "
                f"Remaining: ${weekly_remaining:.2f}"
            ),
            "weekly_spent": weekly_spent,
            "weekly_remaining": weekly_remaining,
        }

    # Unusual price check (somatic gut-check)
    usual_price = _get_usual_price(description)
    multiplier = config.get("unusual_price_multiplier", 2.0)
    if usual_price and estimated_cost > usual_price * multiplier:
        return {
            "allowed": True,
            "requires_approval": True,
            "reason": (
                f"⚠️ Unusual price! ${estimated_cost:.2f} is "
                f"{estimated_cost / usual_price:.1f}x the usual ${usual_price:.2f} "
                f"for '{description}'. Approval required."
            ),
            "usual_price": usual_price,
            "weekly_spent": weekly_spent,
            "weekly_remaining": weekly_remaining,
        }

    # Approval threshold
    approval_above = config.get("require_approval_above", 10.0)
    if estimated_cost > approval_above:
        return {
            "allowed": True,
            "requires_approval": True,
            "reason": (
                f"${estimated_cost:.2f} is above the auto-approve threshold "
                f"of ${approval_above:.2f}. User approval needed."
            ),
            "weekly_spent": weekly_spent,
            "weekly_remaining": weekly_remaining,
        }

    # All checks passed — auto-approve
    return {
        "allowed": True,
        "requires_approval": False,
        "reason": f"Auto-approved. ${estimated_cost:.2f} within limits.",
        "weekly_spent": weekly_spent,
        "weekly_remaining": weekly_remaining,
    }


# ---------------------------------------------------------------------------
# Ledger operations
# ---------------------------------------------------------------------------

def record_purchase(description: str, amount: float, site: str = "",
                    approved_by: str = "auto") -> dict:
    """Record a completed purchase in the ledger."""
    ledger = _load_ledger()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "description": description,
        "amount": amount,
        "site": site,
        "approved_by": approved_by,  # "auto" or "user"
    }
    ledger.append(entry)
    _save_ledger(ledger)

    log.info("[spending] Recorded: $%.2f for '%s' (%s)", amount, description, approved_by)
    return entry


def _get_weekly_spent() -> float:
    """Calculate total spent in the current week (Mon-Sun)."""
    ledger = _load_ledger()
    now = datetime.now()
    # Start of current week (Monday)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    total = 0.0
    for entry in ledger:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= week_start:
                total += entry.get("amount", 0.0)
        except (KeyError, ValueError):
            continue

    return total


def _get_usual_price(description: str) -> Optional[float]:
    """Get the average price for similar past purchases (somatic memory)."""
    ledger = _load_ledger()
    desc_lower = description.lower()

    # Find past purchases with similar descriptions
    similar_amounts = []
    for entry in ledger:
        past_desc = entry.get("description", "").lower()
        # Simple similarity: check if key words overlap
        desc_words = set(desc_lower.split())
        past_words = set(past_desc.split())
        overlap = desc_words & past_words
        if len(overlap) >= 2 or (len(desc_words) == 1 and overlap):
            similar_amounts.append(entry.get("amount", 0.0))

    if similar_amounts:
        return sum(similar_amounts) / len(similar_amounts)

    return None


def get_spending_summary() -> dict:
    """Get a summary of spending for the dashboard."""
    config = _load_config()
    ledger = _load_ledger()
    weekly_spent = _get_weekly_spent()
    weekly_limit = config.get("weekly_limit", 50.0)

    # Last 5 purchases
    recent = ledger[-5:] if ledger else []

    return {
        "enabled": config.get("enabled", True),
        "weekly_limit": weekly_limit,
        "weekly_spent": round(weekly_spent, 2),
        "weekly_remaining": round(weekly_limit - weekly_spent, 2),
        "per_action_limit": config.get("per_action_limit", 25.0),
        "require_approval_above": config.get("require_approval_above", 10.0),
        "total_purchases": len(ledger),
        "recent_purchases": recent,
    }

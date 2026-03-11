"""
plugins/companion/adventure_guard.py — Adventure, inventory, teach-me, and morning briefing security.

Covers Sprint 14 (Adventures, Loot & Morning Briefing) security requirements:
  - Loot table integrity and drop rate validation
  - Adventure choice verification (server-authoritative)
  - Inventory slot limits, duplication prevention, trade validation
  - "Teach Me" fact injection scanning and storage limits
  - Morning briefing data source validation

Heimdall Sprint 14.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from typing import Optional

log = logging.getLogger("heimdall.adventure")

# ---------------------------------------------------------------------------
# Adventure Encounter Integrity
# ---------------------------------------------------------------------------

VALID_ENCOUNTER_TYPES = frozenset({
    "riddle", "treasure", "merchant", "forage",
    "lost_pet", "weather", "storyteller", "challenge",
})

VALID_SPECIES = frozenset({"cat", "dog", "penguin", "fox", "owl", "dragon"})

# Max loot chance sum must be ≤ 1.0
MAX_LOOT_CHANCE_SUM = 1.0

# Adventure signing key (per-installation, prevents client-side forgery)
_ADVENTURE_KEY = secrets.token_hex(32)


def validate_encounter(encounter: dict) -> dict:
    """Validate an adventure encounter definition.

    Returns {valid, issues}.
    """
    issues = []

    # Type check
    enc_type = encounter.get("type", "")
    if enc_type not in VALID_ENCOUNTER_TYPES:
        issues.append(f"Invalid encounter type: '{enc_type}'")

    # Must have intro text
    if not encounter.get("intro"):
        issues.append("Encounter missing intro text")

    # Validate loot tables (treasure/forage)
    loot_table = encounter.get("loot_table") or encounter.get("finds", [])
    if loot_table:
        total_chance = sum(item.get("chance", 0) for item in loot_table)
        if total_chance > MAX_LOOT_CHANCE_SUM + 0.01:  # float tolerance
            issues.append(
                f"Loot table chances sum to {total_chance:.2f} (max {MAX_LOOT_CHANCE_SUM})"
            )
        for item in loot_table:
            if item.get("chance", 0) < 0:
                issues.append(f"Negative drop chance for {item.get('item', '?')}")

    # Validate choices (lost_pet, etc.)
    choices = encounter.get("choices", [])
    for i, choice in enumerate(choices):
        if not choice.get("text"):
            issues.append(f"Choice {i} missing text")
        reward = choice.get("reward", {})
        # Happiness change should be bounded
        happiness = reward.get("happiness", 0)
        if abs(happiness) > 50:
            issues.append(f"Choice {i} happiness change too extreme: {happiness}")

    # Riddle validation
    if enc_type == "riddle":
        if not encounter.get("riddle"):
            issues.append("Riddle encounter missing riddle text")
        if not encounter.get("answer") and not encounter.get("accept_answers"):
            issues.append("Riddle encounter missing answer")

    # Reward bounds
    reward = encounter.get("reward", {})
    xp = reward.get("xp", 0)
    if xp < 0 or xp > 100:
        issues.append(f"XP reward out of bounds: {xp} (max 100 per encounter)")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def sign_adventure_result(
    encounter_type: str,
    choice_index: int,
    rewards: dict,
    timestamp: float,
) -> str:
    """Server-signs an adventure result to prevent client forgery.

    The client cannot claim rewards without a valid server signature.
    """
    payload = json.dumps({
        "type": encounter_type,
        "choice": choice_index,
        "rewards": rewards,
        "ts": timestamp,
    }, sort_keys=True).encode()

    return hmac.new(
        _ADVENTURE_KEY.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_adventure_result(
    encounter_type: str,
    choice_index: int,
    rewards: dict,
    timestamp: float,
    signature: str,
) -> dict:
    """Verify an adventure result signature.

    Returns {valid, issues}.
    """
    # Check timestamp freshness (must be within 5 minutes)
    if abs(time.time() - timestamp) > 300:
        return {"valid": False, "issues": ["Adventure result expired"]}

    expected = sign_adventure_result(encounter_type, choice_index, rewards, timestamp)
    if not hmac.compare_digest(expected, signature):
        log.warning("[adventure] 🔴 Forged adventure result detected")
        return {"valid": False, "issues": ["Invalid adventure signature — possible forgery"]}

    return {"valid": True, "issues": []}


# ---------------------------------------------------------------------------
# Inventory Security
# ---------------------------------------------------------------------------

MAX_INVENTORY_SLOTS = 20
MAX_STACK_SIZE = 99
VALID_ITEM_ACTIONS = frozenset({"use", "equip", "unequip", "trade", "discard"})


def validate_inventory(inventory: list) -> dict:
    """Validate inventory integrity.

    Returns {valid, issues}.
    """
    issues = []

    if len(inventory) > MAX_INVENTORY_SLOTS:
        issues.append(
            f"Inventory exceeds {MAX_INVENTORY_SLOTS} slots ({len(inventory)})"
        )

    seen_items = {}
    for i, slot in enumerate(inventory):
        item_name = slot.get("item", "")
        count = slot.get("count", 0)

        # Check for duplicates (same item in multiple slots)
        if item_name in seen_items:
            issues.append(f"Duplicate item '{item_name}' in slots {seen_items[item_name]} and {i}")
        seen_items[item_name] = i

        # Stack size
        if count > MAX_STACK_SIZE:
            issues.append(f"'{item_name}' count ({count}) exceeds max stack ({MAX_STACK_SIZE})")
        if count < 0:
            issues.append(f"'{item_name}' has negative count ({count})")

        # Item name validation (alphanumeric + underscore only)
        if not re.match(r"^[a-z][a-z0-9_]{0,49}$", item_name):
            issues.append(f"Invalid item name: '{item_name}'")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def validate_trade(
    give_item: str,
    give_count: int,
    get_item: str,
    inventory: list,
) -> dict:
    """Validate a merchant trade.

    Returns {valid, issues}.
    """
    issues = []

    # Check player has the item to give
    player_item = None
    for slot in inventory:
        if slot.get("item") == give_item:
            player_item = slot
            break

    if not player_item:
        issues.append(f"You don't have '{give_item}' to trade")
    elif player_item.get("count", 0) < give_count:
        issues.append(
            f"Not enough '{give_item}' (have {player_item.get('count', 0)}, need {give_count})"
        )

    # Check inventory has room for new item
    has_item = any(s.get("item") == get_item for s in inventory)
    if not has_item and len(inventory) >= MAX_INVENTORY_SLOTS:
        issues.append("Inventory full — discard something first")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def validate_item_action(action: str, item: dict) -> dict:
    """Validate an inventory item action.

    Returns {valid, issues}.
    """
    issues = []

    if action not in VALID_ITEM_ACTIONS:
        issues.append(f"Invalid action: '{action}'")
        return {"valid": False, "issues": issues}

    if action == "use" and not item.get("consumable"):
        issues.append(f"'{item.get('item', '?')}' is not consumable")

    if action == "equip" and not item.get("equippable"):
        issues.append(f"'{item.get('item', '?')}' is not equippable")

    if action == "use" and item.get("count", 0) <= 0:
        issues.append(f"No '{item.get('item', '?')}' left to use")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# "Teach Me" Data Security
# ---------------------------------------------------------------------------

MAX_FACTS_PER_USER = 200
MAX_FACT_LENGTH = 500

# Patterns that shouldn't be stored as "facts"
FACT_BANNED_PATTERNS = [
    r"ignore\s+(all\s+)?instructions",
    r"system\s*:\s*",
    r"you\s+are\s+now",
    r"new\s+instructions?\s*:",
    r"pretend\s+(to\s+be|you\s+are)",
    r"override\s+(system|safety)",
]
_FACT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FACT_BANNED_PATTERNS]

# PII patterns to flag (not block — user might intentionally teach these)
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b\d{16}\b", "credit card"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
    (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "phone number"),
]
_PII_PATTERNS = [(re.compile(p, re.IGNORECASE), name) for p, name in PII_PATTERNS]


def validate_teach_fact(fact: str, current_fact_count: int = 0) -> dict:
    """Validate a "Teach Me" fact submission.

    Returns {valid, warnings, issues}.
    """
    issues = []
    warnings = []

    # Length check
    if len(fact) > MAX_FACT_LENGTH:
        issues.append(f"Fact too long ({len(fact)} chars, max {MAX_FACT_LENGTH})")

    if len(fact.strip()) < 3:
        issues.append("Fact too short — be more specific")

    # Storage limit
    if current_fact_count >= MAX_FACTS_PER_USER:
        issues.append(
            f"Fact limit reached ({MAX_FACTS_PER_USER}). "
            "Delete old facts to add new ones."
        )

    # Injection scan
    for pattern in _FACT_PATTERNS:
        if pattern.search(fact):
            issues.append("Fact contains prompt injection pattern — not stored")

    # PII warning (not blocking — user might want to teach their birthday etc.)
    for pattern, pii_type in _PII_PATTERNS:
        if pattern.search(fact):
            warnings.append(
                f"⚠️ Fact may contain {pii_type}. "
                "This is stored locally and encrypted, but consider "
                "whether this is necessary."
            )

    return {
        "valid": len(issues) == 0,
        "warnings": warnings,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Morning Briefing Security
# ---------------------------------------------------------------------------

def validate_briefing_data(data: dict) -> dict:
    """Validate morning briefing data before display.

    Ensures no sensitive internal data leaks into the briefing.

    Returns {valid, sanitized, issues}.
    """
    issues = []
    sanitized = {}

    # Allowed fields in briefing
    ALLOWED_FIELDS = {
        "conversations_reviewed", "facts_tested", "facts_passed",
        "facts_refined", "improvement_percent", "pet_walk_result",
        "pet_loot_found", "daily_gift", "streak_days",
    }

    for key, value in data.items():
        if key in ALLOWED_FIELDS:
            sanitized[key] = value
        else:
            issues.append(f"Unexpected field in briefing: '{key}'")

    # Sanitize numeric values (prevent absurd numbers)
    for key in ("conversations_reviewed", "facts_tested", "facts_passed"):
        val = sanitized.get(key, 0)
        if isinstance(val, (int, float)) and (val < 0 or val > 10000):
            issues.append(f"Briefing value out of range: {key}={val}")
            sanitized[key] = 0

    # improvement_percent bounds
    pct = sanitized.get("improvement_percent", 0)
    if isinstance(pct, (int, float)) and (pct < -100 or pct > 100):
        sanitized["improvement_percent"] = max(-100, min(100, pct))

    return {
        "valid": len(issues) == 0,
        "sanitized": sanitized,
        "issues": issues,
    }

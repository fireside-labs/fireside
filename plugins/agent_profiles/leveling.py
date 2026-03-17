"""
agent-profiles/leveling.py — XP and leveling system.

XP Sources:
  task completed  → +100 XP
  crucible survived → +50 XP
  debate won → +75 XP
  streak bonus → +10 per consecutive task
  file read → +5 XP

Levels:
  Every 500 XP = 1 level up
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

log = logging.getLogger("valhalla.agent-profiles.leveling")

XP_PER_LEVEL = 500
CHAT_XP_DAILY_CAP = 20  # Max chat XP per day (anti-farming)

XP_REWARDS = {
    "pipeline.shipped": 100,
    "crucible.survived": 50,
    "socratic.won": 75,
    "file.read": 5,
    "chat.response": 10,
    "hypothesis.accepted": 25,
}

STREAK_BONUS = 10  # per consecutive task


def _today_key() -> str:
    """UTC date string for daily tracking."""
    import datetime
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")


def _get_chat_xp_today(profile: dict) -> int:
    """Get total chat XP awarded today."""
    today = _today_key()
    return profile.get("_daily_chat_xp", {}).get(today, 0)


def _record_chat_xp(profile: dict, amount: int) -> None:
    """Record chat XP for daily cap tracking."""
    today = _today_key()
    if "_daily_chat_xp" not in profile:
        profile["_daily_chat_xp"] = {}
    # Clean old entries (keep only today)
    profile["_daily_chat_xp"] = {
        today: profile["_daily_chat_xp"].get(today, 0) + amount,
    }


def _profiles_dir() -> Path:
    p = Path.home() / ".valhalla" / "profiles"
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_profile(agent_name: str) -> dict:
    """Load agent profile from disk."""
    f = _profiles_dir() / f"{agent_name}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _default_profile(agent_name)


def save_profile(agent_name: str, profile: dict) -> None:
    """Save agent profile to disk."""
    f = _profiles_dir() / f"{agent_name}.json"
    f.write_text(json.dumps(profile, indent=2, default=str), encoding="utf-8")


def _default_profile(agent_name: str) -> dict:
    return {
        "name": agent_name,
        "level": 1,
        "xp": 0,
        "xp_to_next": XP_PER_LEVEL,
        "avatar": {"style": "pixel", "hair": "#8B4513", "outfit": "warrior"},
        "stats": {
            "tasks_completed": 0,
            "knowledge_count": 0,
            "accuracy": 0.0,
            "crucible_survival": 0.0,
            "streak": 0,
            "best_streak": 0,
            "debates_won": 0,
            "debates_total": 0,
            "skills": {},
        },
        "personality": {
            "creative_precise": 0.5,
            "verbose_concise": 0.5,
            "bold_cautious": 0.5,
            "warm_formal": 0.5,
        },
        "achievements": [],
        "xp_history": [],
        "created_at": time.time(),
    }


def add_xp(agent_name: str, amount: int, reason: str = "") -> dict:
    """Add XP to an agent. Returns level-up info if applicable."""
    profile = load_profile(agent_name)
    old_level = profile["level"]

    profile["xp"] += amount
    profile["xp_history"].append({
        "amount": amount,
        "reason": reason,
        "timestamp": time.time(),
    })
    # Keep only last 100 entries
    profile["xp_history"] = profile["xp_history"][-100:]

    # Calculate new level
    new_level = (profile["xp"] // XP_PER_LEVEL) + 1
    profile["level"] = new_level
    profile["xp_to_next"] = (new_level * XP_PER_LEVEL) - profile["xp"]

    leveled_up = new_level > old_level
    save_profile(agent_name, profile)

    result = {
        "agent": agent_name,
        "xp_added": amount,
        "total_xp": profile["xp"],
        "level": new_level,
        "leveled_up": leveled_up,
    }
    if leveled_up:
        result["old_level"] = old_level
        result["new_level"] = new_level
        log.info("[leveling] %s leveled up! %d → %d", agent_name, old_level, new_level)

    return result


def award_event_xp(agent_name: str, event_name: str) -> dict | None:
    """Award XP for an event if it has a reward defined."""
    xp = XP_REWARDS.get(event_name)
    if not xp:
        return None

    profile = load_profile(agent_name)

    # Chat XP daily cap (anti-farming)
    if event_name == "chat.response":
        today_used = _get_chat_xp_today(profile)
        remaining = CHAT_XP_DAILY_CAP - today_used
        if remaining <= 0:
            return {"agent": agent_name, "xp_added": 0, "capped": True,
                    "reason": f"Chat XP capped at {CHAT_XP_DAILY_CAP}/day"}
        xp = min(xp, remaining)
        _record_chat_xp(profile, xp)
        save_profile(agent_name, profile)

    # Streak tracking
    elif event_name == "pipeline.shipped":
        profile["stats"]["tasks_completed"] += 1
        profile["stats"]["streak"] += 1
        if profile["stats"]["streak"] > profile["stats"]["best_streak"]:
            profile["stats"]["best_streak"] = profile["stats"]["streak"]
        # Streak bonus
        xp += profile["stats"]["streak"] * STREAK_BONUS
        save_profile(agent_name, profile)
    elif event_name == "crucible.survived":
        save_profile(agent_name, profile)
    elif event_name == "socratic.won":
        profile["stats"]["debates_won"] += 1
        profile["stats"]["debates_total"] += 1
        save_profile(agent_name, profile)

    return add_xp(agent_name, xp, reason=event_name)


def update_stats(agent_name: str, stat_key: str, value) -> None:
    """Update a specific stat."""
    profile = load_profile(agent_name)
    profile["stats"][stat_key] = value
    save_profile(agent_name, profile)


def update_skill(agent_name: str, skill: str, level: int) -> None:
    """Update a skill level (1-5 stars)."""
    profile = load_profile(agent_name)
    profile["stats"]["skills"][skill] = min(max(level, 0), 5)
    save_profile(agent_name, profile)


def get_level_info(xp: int) -> dict:
    """Get level info from XP amount."""
    level = (xp // XP_PER_LEVEL) + 1
    xp_in_level = xp % XP_PER_LEVEL
    return {
        "level": level,
        "xp_in_level": xp_in_level,
        "xp_to_next": XP_PER_LEVEL - xp_in_level,
        "progress_pct": round((xp_in_level / XP_PER_LEVEL) * 100),
    }

"""
agent-profiles/achievements.py — Badge definitions and unlock logic.

Achievements are unlocked by meeting specific criteria.
Checked after each XP event.
"""
from __future__ import annotations

import time

ACHIEVEMENTS = {
    # Streak achievements
    "streak_3": {
        "name": "On a Roll",
        "desc": "3 tasks completed without failure",
        "emoji": "🔥",
        "check": lambda p: p["stats"]["streak"] >= 3,
    },
    "streak_5": {
        "name": "Dedicated",
        "desc": "5 tasks in a row",
        "emoji": "⚡",
        "check": lambda p: p["stats"]["streak"] >= 5,
    },
    "streak_10": {
        "name": "Unstoppable",
        "desc": "10 tasks without failure",
        "emoji": "🏆",
        "check": lambda p: p["stats"]["streak"] >= 10,
    },
    "streak_25": {
        "name": "Legendary",
        "desc": "25 tasks without failure",
        "emoji": "👑",
        "check": lambda p: p["stats"]["streak"] >= 25,
    },

    # Task milestones
    "tasks_10": {
        "name": "Getting Started",
        "desc": "10 tasks completed",
        "emoji": "📋",
        "check": lambda p: p["stats"]["tasks_completed"] >= 10,
    },
    "tasks_50": {
        "name": "Workhorse",
        "desc": "50 tasks completed",
        "emoji": "🐴",
        "check": lambda p: p["stats"]["tasks_completed"] >= 50,
    },
    "tasks_100": {
        "name": "Centurion",
        "desc": "100 tasks completed",
        "emoji": "💯",
        "check": lambda p: p["stats"]["tasks_completed"] >= 100,
    },

    # Knowledge milestones
    "knowledge_50": {
        "name": "Scholar",
        "desc": "Learned 50 things",
        "emoji": "📚",
        "check": lambda p: p["stats"]["knowledge_count"] >= 50,
    },
    "knowledge_200": {
        "name": "Walking Encyclopedia",
        "desc": "Learned 200 things",
        "emoji": "🧠",
        "check": lambda p: p["stats"]["knowledge_count"] >= 200,
    },

    # Crucible achievements
    "crucible_100": {
        "name": "Forged in Fire",
        "desc": "100% crucible survival rate (min 10 tests)",
        "emoji": "🔨",
        "check": lambda p: p["stats"]["crucible_survival"] >= 1.0 and p["stats"].get("crucible_tests", 0) >= 10,
    },

    # Debate achievements
    "debate_win_1": {
        "name": "First Argument",
        "desc": "Won first Socratic debate",
        "emoji": "💬",
        "check": lambda p: p["stats"]["debates_won"] >= 1,
    },
    "debate_win_3": {
        "name": "Silver Tongue",
        "desc": "Won 3 Socratic debates",
        "emoji": "🗣️",
        "check": lambda p: p["stats"]["debates_won"] >= 3,
    },
    "debate_win_10": {
        "name": "Philosopher",
        "desc": "Won 10 Socratic debates",
        "emoji": "🎭",
        "check": lambda p: p["stats"]["debates_won"] >= 10,
    },

    # Level milestones
    "level_5": {
        "name": "Apprentice",
        "desc": "Reached level 5",
        "emoji": "⭐",
        "check": lambda p: p["level"] >= 5,
    },
    "level_10": {
        "name": "Journeyman",
        "desc": "Reached level 10",
        "emoji": "🌟",
        "check": lambda p: p["level"] >= 10,
    },
    "level_20": {
        "name": "Master",
        "desc": "Reached level 20",
        "emoji": "✨",
        "check": lambda p: p["level"] >= 20,
    },
    "level_50": {
        "name": "Grand Master",
        "desc": "Reached level 50",
        "emoji": "🏅",
        "check": lambda p: p["level"] >= 50,
    },

    # Skill achievements
    "skill_max": {
        "name": "Specialist",
        "desc": "Maxed out a skill (5 stars)",
        "emoji": "⭐",
        "check": lambda p: any(v >= 5 for v in p["stats"]["skills"].values()) if p["stats"]["skills"] else False,
    },
    "skill_3_types": {
        "name": "Well Rounded",
        "desc": "3 or more skills at level 3+",
        "emoji": "🎯",
        "check": lambda p: sum(1 for v in p["stats"]["skills"].values() if v >= 3) >= 3 if p["stats"]["skills"] else False,
    },
}


def check_achievements(profile: dict) -> list:
    """Check which new achievements have been unlocked.

    Returns list of newly unlocked achievement dicts.
    """
    existing_ids = {a["id"] for a in profile.get("achievements", [])}
    newly_unlocked = []

    for ach_id, ach_def in ACHIEVEMENTS.items():
        if ach_id in existing_ids:
            continue
        try:
            if ach_def["check"](profile):
                achievement = {
                    "id": ach_id,
                    "name": ach_def["name"],
                    "desc": ach_def["desc"],
                    "emoji": ach_def["emoji"],
                    "unlocked_at": time.time(),
                }
                newly_unlocked.append(achievement)
        except Exception:
            pass

    return newly_unlocked


def get_all_achievements() -> list:
    """Return all possible achievements (for display in UI)."""
    return [
        {
            "id": ach_id,
            "name": ach_def["name"],
            "desc": ach_def["desc"],
            "emoji": ach_def["emoji"],
        }
        for ach_id, ach_def in ACHIEVEMENTS.items()
    ]


def get_next_achievements(profile: dict, limit: int = 3) -> list:
    """Return the closest achievements to being unlocked."""
    existing_ids = {a["id"] for a in profile.get("achievements", [])}
    candidates = []

    for ach_id, ach_def in ACHIEVEMENTS.items():
        if ach_id in existing_ids:
            continue
        candidates.append({
            "id": ach_id,
            "name": ach_def["name"],
            "desc": ach_def["desc"],
            "emoji": ach_def["emoji"],
        })

    return candidates[:limit]

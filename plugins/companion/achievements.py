"""
plugins/companion/achievements.py — Achievement tracking for companion app.

16 achievements stored in ~/.valhalla/achievements.json with timestamps.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

log = logging.getLogger("valhalla.achievements")

ACHIEVEMENTS = {
    "first_feed": {"name": "First Meal", "desc": "Feed your companion for the first time", "icon": "\ud83c\udf7d\ufe0f"},
    "feed_10": {"name": "Chef", "desc": "Feed your companion 10 times", "icon": "\ud83d\udc68\u200d\ud83c\udf73"},
    "feed_100": {"name": "Master Chef", "desc": "Feed 100 times", "icon": "\u2b50"},
    "first_walk": {"name": "First Steps", "desc": "Take your first walk", "icon": "\ud83d\udeb6"},
    "walk_50": {"name": "Explorer", "desc": "Complete 50 walks", "icon": "\ud83d\uddfa\ufe0f"},
    "first_quest": {"name": "Adventurer", "desc": "Complete your first quest", "icon": "\u2694\ufe0f"},
    "quest_25": {"name": "Hero", "desc": "Complete 25 quests", "icon": "\ud83e\uddb8"},
    "first_teach": {"name": "Teacher", "desc": "Teach your companion a fact", "icon": "\ud83d\udcda"},
    "teach_20": {"name": "Professor", "desc": "Teach 20 facts", "icon": "\ud83c\udf93"},
    "daily_7": {"name": "Streak!", "desc": "7-day login streak", "icon": "\ud83d\udd25"},
    "daily_30": {"name": "Devoted", "desc": "30-day login streak", "icon": "\ud83d\udc8e"},
    "level_5": {"name": "Growing Up", "desc": "Reach level 5", "icon": "\ud83c\udf31"},
    "level_10": {"name": "Seasoned", "desc": "Reach level 10", "icon": "\ud83c\udf33"},
    "guardian_save": {"name": "Saved by Guardian", "desc": "Guardian stopped a risky message", "icon": "\ud83d\udee1\ufe0f"},
    "voice_first": {"name": "First Words", "desc": "Use voice mode for the first time", "icon": "\ud83c\udfa4"},
    "translate_first": {"name": "Polyglot", "desc": "Translate something", "icon": "\ud83c\udf0d"},
}


def _achievements_file() -> Path:
    return Path.home() / ".valhalla" / "achievements.json"


def load_earned() -> dict:
    """Load earned achievements with timestamps."""
    f = _achievements_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_earned(earned: dict) -> None:
    """Save earned achievements."""
    f = _achievements_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(earned, indent=2), encoding="utf-8")


def get_all_achievements() -> list:
    """Get all achievements with earned status."""
    earned = load_earned()
    result = []
    for aid, info in ACHIEVEMENTS.items():
        result.append({
            "id": aid,
            "name": info["name"],
            "desc": info["desc"],
            "icon": info["icon"],
            "earned": aid in earned,
            "earned_at": earned.get(aid, {}).get("earned_at") if aid in earned else None,
        })
    return result


def check_and_award(state: dict) -> list:
    """Check companion state and award any newly earned achievements.

    Returns list of newly earned achievements (for toast notifications).
    """
    earned = load_earned()
    newly_earned = []

    counters = state.get("counters", {})

    # Feed achievements
    feeds = counters.get("feeds", 0)
    if feeds >= 1 and "first_feed" not in earned:
        newly_earned.append("first_feed")
    if feeds >= 10 and "feed_10" not in earned:
        newly_earned.append("feed_10")
    if feeds >= 100 and "feed_100" not in earned:
        newly_earned.append("feed_100")

    # Walk achievements
    walks = counters.get("walks", 0)
    if walks >= 1 and "first_walk" not in earned:
        newly_earned.append("first_walk")
    if walks >= 50 and "walk_50" not in earned:
        newly_earned.append("walk_50")

    # Quest achievements
    quests = counters.get("quests", 0)
    if quests >= 1 and "first_quest" not in earned:
        newly_earned.append("first_quest")
    if quests >= 25 and "quest_25" not in earned:
        newly_earned.append("quest_25")

    # Teach achievements
    teaches = counters.get("teaches", 0)
    if teaches >= 1 and "first_teach" not in earned:
        newly_earned.append("first_teach")
    if teaches >= 20 and "teach_20" not in earned:
        newly_earned.append("teach_20")

    # Streak achievements
    streak = state.get("streak_days", 0)
    if streak >= 7 and "daily_7" not in earned:
        newly_earned.append("daily_7")
    if streak >= 30 and "daily_30" not in earned:
        newly_earned.append("daily_30")

    # Level achievements
    level = state.get("level", 1)
    if level >= 5 and "level_5" not in earned:
        newly_earned.append("level_5")
    if level >= 10 and "level_10" not in earned:
        newly_earned.append("level_10")

    # Guardian save
    guardian_saves = counters.get("guardian_saves", 0)
    if guardian_saves >= 1 and "guardian_save" not in earned:
        newly_earned.append("guardian_save")

    # Voice usage
    voice_uses = counters.get("voice_uses", 0)
    if voice_uses >= 1 and "voice_first" not in earned:
        newly_earned.append("voice_first")

    # Translation usage
    translations = counters.get("translations", 0)
    if translations >= 1 and "translate_first" not in earned:
        newly_earned.append("translate_first")

    # Award new achievements
    if newly_earned:
        ts = time.time()
        for aid in newly_earned:
            earned[aid] = {"earned_at": ts}
        save_earned(earned)
        log.info("[achievements] Awarded: %s", newly_earned)

    return [
        {"id": aid, **ACHIEVEMENTS[aid], "earned_at": time.time()}
        for aid in newly_earned
    ]

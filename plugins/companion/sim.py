"""
companion/sim.py — CompanionSim Engine (Tamagotchi mechanics).

SIMPLIFIED (per Valkyrie UX audit):
  Single stat: HAPPINESS (0-100)
  - Goes up: chat, feeding, walks, tasks
  - Goes down: ~1% every 12 minutes (passive drift)
  - Below 30%: "Your companion misses you"
  - At 0%: Pet wanders off, comes back when you interact

Feeding: fish (+15), treat (+10/bonus), salad (+8), cake (+20)
Walks: 30 events (5 per species), unique outcomes.
XP: walks + feeding grant XP. Level up at level × 20 XP.
Daily streak: consecutive check-in days → rewards.
"""
from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path

log = logging.getLogger("valhalla.companion.sim")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPECIES = ["cat", "dog", "penguin", "fox", "owl", "dragon"]

FOOD_ITEMS = {
    "fish":  {"happiness": 15, "emoji": "🐟"},
    "treat": {"happiness": 10, "emoji": "🍬"},
    "salad": {"happiness": 8,  "emoji": "🥗"},
    "cake":  {"happiness": 20, "emoji": "🎂"},
}

WALK_EVENTS = {
    "cat": [
        {"text": "Found a sunny spot and refused to move for 20 minutes.", "xp": 5, "happiness": 10},
        {"text": "Chased a butterfly. Missed. Pretended it was on purpose.", "xp": 8, "happiness": 15},
        {"text": "Discovered a cardboard box. This is home now.", "xp": 3, "happiness": 20},
        {"text": "Made eye contact with a bird. Dominance established.", "xp": 10, "happiness": 5},
        {"text": "Knocked a pinecone off the path. Felt powerful.", "xp": 6, "happiness": 12},
    ],
    "dog": [
        {"text": "MET A NEW FRIEND! Sniffed butts. Best day ever!!", "xp": 10, "happiness": 25},
        {"text": "Found a stick. THE stick. Life complete.", "xp": 8, "happiness": 20},
        {"text": "Rolled in something mysterious. Owner not pleased.", "xp": 5, "happiness": 15},
        {"text": "Chased tail for 3 full minutes. Personal best!", "xp": 6, "happiness": 18},
        {"text": "Barked at a mailbox. It didn't bark back. Victory.", "xp": 7, "happiness": 10},
    ],
    "penguin": [
        {"text": "Waddled with purpose. Destination: unknown. Confidence: absolute.", "xp": 8, "happiness": 15},
        {"text": "Attempted to slide on grass. Physics disagreed.", "xp": 5, "happiness": 10},
        {"text": "Found a puddle. Closest thing to the ocean. Wept a little.", "xp": 3, "happiness": 5},
        {"text": "Adjusted bowtie 7 times. Looking impeccable.", "xp": 4, "happiness": 20},
        {"text": "Organized the rocks by size. Someone had to.", "xp": 10, "happiness": 12},
    ],
    "fox": [
        {"text": "Investigated a suspicious bush. Filed mental report.", "xp": 10, "happiness": 15},
        {"text": "Pounced on a leaf pile. Evidence scattered.", "xp": 8, "happiness": 20},
        {"text": "Located 3 escape routes from the park. Just in case.", "xp": 7, "happiness": 10},
        {"text": "Cached a snack under a tree. Investment portfolio growing.", "xp": 6, "happiness": 12},
        {"text": "Watched the sunset. Contemplated the universe.", "xp": 5, "happiness": 18},
    ],
    "owl": [
        {"text": "Counted every tree in the park. 47. You're welcome.", "xp": 8, "happiness": 10},
        {"text": "Spotted a mouse from 200 meters. Didn't tell anyone.", "xp": 10, "happiness": 5},
        {"text": "Rotated head 270°. Tourists were alarmed.", "xp": 6, "happiness": 15},
        {"text": "Blinked slowly at a squirrel. The squirrel understood.", "xp": 5, "happiness": 12},
        {"text": "Found a quiet branch. Read for 2 hours. Perfect.", "xp": 4, "happiness": 25},
    ],
    "dragon": [
        {"text": "Breathed fire at a dandelion. 10/10 aesthetic.", "xp": 10, "happiness": 20},
        {"text": "Tried to fly. Wings too small. Ran instead. Still majestic.", "xp": 8, "happiness": 15},
        {"text": "Found a shiny rock. Added to hoard (rock count: 847).", "xp": 6, "happiness": 25},
        {"text": "Intimidated a duck. The duck was not intimidated.", "xp": 5, "happiness": 10},
        {"text": "Napped on warm asphalt. Basically a natural heat stone.", "xp": 7, "happiness": 18},
    ],
}

# ~1% per 12 minutes → full to empty in ~20 hours
# Check in 3x/day = happy pet (Wordle cadence)
DECAY_PER_MINUTE = 1.0 / 12.0  # ~0.083% per minute

WANDER_THRESHOLD = 0  # Pet wanders off at 0 happiness
MISS_THRESHOLD = 30   # "Your companion misses you" below 30

# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _state_file() -> Path:
    f = Path.home() / ".valhalla" / "companion_state.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def load_state() -> dict:
    """Load companion state from disk."""
    f = _state_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    """Save companion state to disk."""
    _state_file().write_text(
        json.dumps(state, indent=2, default=str), encoding="utf-8",
    )


def default_companion(name: str, species: str, owner: str = "") -> dict:
    """Create a new companion."""
    return {
        "name": name,
        "species": species if species in SPECIES else "cat",
        "owner": owner,  # User's name — pet says it
        "happiness": 80,
        "xp": 0,
        "level": 1,
        "xp_to_next": 20,
        "walk_count": 0,
        "feed_count": 0,
        "streak_days": 0,
        "last_check_in": None,
        "wandered_off": False,
        "last_decay": time.time(),
        "created_at": time.time(),
    }


# ---------------------------------------------------------------------------
# Sim mechanics
# ---------------------------------------------------------------------------

def apply_decay(state: dict) -> dict:
    """Apply passive happiness decay based on time elapsed."""
    now = time.time()
    elapsed_mins = (now - state.get("last_decay", now)) / 60.0

    if elapsed_mins >= 1:
        decay = DECAY_PER_MINUTE * elapsed_mins
        state["happiness"] = max(0, round(state["happiness"] - decay, 1))
        state["last_decay"] = now

        # Wander off at 0
        if state["happiness"] <= WANDER_THRESHOLD and not state.get("wandered_off"):
            state["wandered_off"] = True
            log.info("[companion] %s wandered off looking for food!", state["name"])

    return state


def _check_streak(state: dict) -> dict:
    """Update daily check-in streak."""
    import datetime
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    last = state.get("last_check_in")

    if last == today:
        return state  # Already checked in today

    if last:
        # Check if yesterday
        yesterday = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        if last == yesterday:
            state["streak_days"] += 1
        else:
            state["streak_days"] = 1  # Streak broken
    else:
        state["streak_days"] = 1

    state["last_check_in"] = today
    return state


def feed(state: dict, food: str) -> dict:
    """Feed the companion."""
    if food not in FOOD_ITEMS:
        return {"ok": False, "error": f"Unknown food: {food}. Options: {list(FOOD_ITEMS.keys())}"}

    item = FOOD_ITEMS[food]
    state = apply_decay(state)

    # Feeding brings pet back from wandering
    if state.get("wandered_off"):
        state["wandered_off"] = False
        state["happiness"] = max(state["happiness"], 10)  # Min 10 on return

    state["happiness"] = min(100, state["happiness"] + item["happiness"])
    state["feed_count"] += 1
    state = _check_streak(state)

    # XP for feeding
    xp_gained = 3
    level_up = _add_xp(state, xp_gained)

    save_state(state)

    owner = state.get("owner", "")
    greeting = f"Thanks, {owner}! " if owner else ""

    return {
        "ok": True,
        "food": food,
        "emoji": item["emoji"],
        "happiness": state["happiness"],
        "xp_gained": xp_gained,
        "level_up": level_up,
        "message": f"{greeting}{state['name']} loved the {food}!",
        "streak_days": state["streak_days"],
    }


def walk(state: dict) -> dict:
    """Take the companion for a walk."""
    state = apply_decay(state)

    if state.get("wandered_off"):
        return {"ok": False, "error": f"{state['name']} has wandered off! Feed them to bring them back."}

    species = state.get("species", "cat")
    events = WALK_EVENTS.get(species, WALK_EVENTS["cat"])
    event = random.choice(events)

    state["happiness"] = min(100, state["happiness"] + event["happiness"])
    state["walk_count"] += 1
    state = _check_streak(state)

    level_up = _add_xp(state, event["xp"])

    save_state(state)
    return {
        "ok": True,
        "event": event["text"],
        "xp_gained": event["xp"],
        "happiness": state["happiness"],
        "level_up": level_up,
        "streak_days": state["streak_days"],
    }


def _add_xp(state: dict, amount: int) -> bool:
    """Add XP and check for level up."""
    state["xp"] += amount
    xp_needed = state["level"] * 20

    if state["xp"] >= xp_needed:
        state["xp"] -= xp_needed
        state["level"] += 1
        state["xp_to_next"] = state["level"] * 20
        log.info("[companion] %s leveled up to %d!", state["name"], state["level"])
        return True

    state["xp_to_next"] = xp_needed - state["xp"]
    return False


def get_mood_prefix(state: dict) -> str:
    """Get mood-appropriate prefix for chat responses."""
    species = state.get("species", "cat")
    happiness = state.get("happiness", 50)

    prefixes = {
        "cat": {
            "happy": "*purrs contentedly*",
            "neutral": "*licks paw*",
            "sad": "*hisses softly*",
        },
        "dog": {
            "happy": "*tail wagging intensifies*",
            "neutral": "*tilts head*",
            "sad": "*whimpers*",
        },
        "penguin": {
            "happy": "*adjusts bowtie proudly*",
            "neutral": "*waddles in place*",
            "sad": "*stares disapprovingly*",
        },
        "fox": {
            "happy": "*does a little pounce*",
            "neutral": "*ear flicks*",
            "sad": "*narrows eyes*",
        },
        "owl": {
            "happy": "*hoots melodically*",
            "neutral": "*blinks slowly*",
            "sad": "*ruffles feathers*",
        },
        "dragon": {
            "happy": "*tiny flame of joy*",
            "neutral": "*smoke puff*",
            "sad": "*ember snort*",
        },
    }

    mood_key = "happy" if happiness >= 70 else "sad" if happiness <= 30 else "neutral"
    return prefixes.get(species, prefixes["cat"]).get(mood_key, "")


def get_status(state: dict) -> dict:
    """Get full companion status with decay applied."""
    state = apply_decay(state)
    state = _check_streak(state)
    save_state(state)

    owner = state.get("owner", "")
    name = state["name"]
    happiness = state["happiness"]

    # Status message
    if state.get("wandered_off"):
        status_msg = f"{name} has wandered off looking for food. Feed them to bring them back!"
    elif happiness <= MISS_THRESHOLD:
        greeting = f", {owner}" if owner else ""
        status_msg = f"{name} misses you{greeting}! 🥺"
    elif happiness >= 70:
        greeting = f" {owner}!" if owner else "!"
        status_msg = f"{name} is happy to see you{greeting} 😊"
    else:
        status_msg = f"{name} is doing okay."

    return {
        "name": name,
        "species": state["species"],
        "owner": owner,
        "happiness": round(happiness),
        "xp": state["xp"],
        "level": state["level"],
        "xp_to_next": state["xp_to_next"],
        "walk_count": state["walk_count"],
        "feed_count": state["feed_count"],
        "streak_days": state["streak_days"],
        "wandered_off": state.get("wandered_off", False),
        "mood_prefix": get_mood_prefix(state),
        "status_message": status_msg,
    }

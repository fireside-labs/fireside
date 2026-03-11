"""
companion/sim.py — CompanionSim Engine (Tamagotchi mechanics).

Stats:
  hunger  — 0-100, passive decay every 60s
  mood    — 0-100, affected by feeding, walks, neglect
  energy  — 0-100, walks drain, resting recovers

Feeding: fish (+30 hunger), treat (+20 hunger, +15 mood),
         salad (+15 hunger), cake (+10 hunger, +25 mood)

Walks: 30 events (5 per species), unique outcomes.
XP: walks + feeding grant XP. Level up at level × 20 XP.
Mood affects chat response quality.
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
    "fish":  {"hunger": 30, "mood": 5,  "emoji": "🐟"},
    "treat": {"hunger": 20, "mood": 15, "emoji": "🍬"},
    "salad": {"hunger": 15, "mood": 0,  "emoji": "🥗"},
    "cake":  {"hunger": 10, "mood": 25, "emoji": "🎂"},
}

WALK_EVENTS = {
    "cat": [
        {"text": "Found a sunny spot and refused to move for 20 minutes.", "xp": 5, "mood": 10},
        {"text": "Chased a butterfly. Missed. Pretended it was on purpose.", "xp": 8, "mood": 15},
        {"text": "Discovered a cardboard box. This is home now.", "xp": 3, "mood": 20},
        {"text": "Made eye contact with a bird. Dominance established.", "xp": 10, "mood": 5},
        {"text": "Knocked a pinecone off the path. Felt powerful.", "xp": 6, "mood": 12},
    ],
    "dog": [
        {"text": "MET A NEW FRIEND! Sniffed butts. Best day ever!!", "xp": 10, "mood": 25},
        {"text": "Found a stick. THE stick. Life complete.", "xp": 8, "mood": 20},
        {"text": "Rolled in something mysterious. Owner not pleased.", "xp": 5, "mood": 15},
        {"text": "Chased tail for 3 full minutes. Personal best!", "xp": 6, "mood": 18},
        {"text": "Barked at a mailbox. It didn't bark back. Victory.", "xp": 7, "mood": 10},
    ],
    "penguin": [
        {"text": "Waddled with purpose. Destination: unknown. Confidence: absolute.", "xp": 8, "mood": 15},
        {"text": "Attempted to slide on grass. Physics disagreed.", "xp": 5, "mood": 10},
        {"text": "Found a puddle. Closest thing to the ocean. Wept a little.", "xp": 3, "mood": 5},
        {"text": "Adjusted bowtie 7 times. Looking impeccable.", "xp": 4, "mood": 20},
        {"text": "Organized the rocks by size. Someone had to.", "xp": 10, "mood": 12},
    ],
    "fox": [
        {"text": "Investigated a suspicious bush. Filed mental report.", "xp": 10, "mood": 15},
        {"text": "Pounced on a leaf pile. Evidence scattered.", "xp": 8, "mood": 20},
        {"text": "Located 3 escape routes from the park. Just in case.", "xp": 7, "mood": 10},
        {"text": "Cached a snack under a tree. Investment portfolio growing.", "xp": 6, "mood": 12},
        {"text": "Watched the sunset. Contemplated the universe.", "xp": 5, "mood": 18},
    ],
    "owl": [
        {"text": "Counted every tree in the park. 47. You're welcome.", "xp": 8, "mood": 10},
        {"text": "Spotted a mouse from 200 meters. Didn't tell anyone.", "xp": 10, "mood": 5},
        {"text": "Rotated head 270°. Tourists were alarmed.", "xp": 6, "mood": 15},
        {"text": "Blinked slowly at a squirrel. The squirrel understood.", "xp": 5, "mood": 12},
        {"text": "Found a quiet branch. Read for 2 hours. Perfect.", "xp": 4, "mood": 25},
    ],
    "dragon": [
        {"text": "Breathed fire at a dandelion. 10/10 aesthetic.", "xp": 10, "mood": 20},
        {"text": "Tried to fly. Wings too small. Ran instead. Still majestic.", "xp": 8, "mood": 15},
        {"text": "Found a shiny rock. Added to hoard (rock count: 847).", "xp": 6, "mood": 25},
        {"text": "Intimidated a duck. The duck was not intimidated.", "xp": 5, "mood": 10},
        {"text": "Napped on warm asphalt. Basically a natural heat stone.", "xp": 7, "mood": 18},
    ],
}

DECAY_RATE = {
    "hunger": -2,  # per minute
    "mood": -1,
    "energy": 1,   # recovers when not walking
}

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


def default_companion(name: str, species: str) -> dict:
    """Create a new companion."""
    return {
        "name": name,
        "species": species if species in SPECIES else "cat",
        "hunger": 80,
        "mood": 80,
        "energy": 100,
        "xp": 0,
        "level": 1,
        "xp_to_next": 20,
        "walk_count": 0,
        "feed_count": 0,
        "last_decay": time.time(),
        "created_at": time.time(),
    }


# ---------------------------------------------------------------------------
# Sim mechanics
# ---------------------------------------------------------------------------

def apply_decay(state: dict) -> dict:
    """Apply passive stat decay based on time elapsed."""
    now = time.time()
    elapsed_mins = (now - state.get("last_decay", now)) / 60.0

    if elapsed_mins >= 1:
        ticks = int(elapsed_mins)
        state["hunger"] = max(0, state["hunger"] + DECAY_RATE["hunger"] * ticks)
        state["mood"] = max(0, state["mood"] + DECAY_RATE["mood"] * ticks)
        state["energy"] = min(100, state["energy"] + DECAY_RATE["energy"] * ticks)
        state["last_decay"] = now
    return state


def feed(state: dict, food: str) -> dict:
    """Feed the companion."""
    if food not in FOOD_ITEMS:
        return {"ok": False, "error": f"Unknown food: {food}. Options: {list(FOOD_ITEMS.keys())}"}

    item = FOOD_ITEMS[food]
    state = apply_decay(state)

    state["hunger"] = min(100, state["hunger"] + item["hunger"])
    state["mood"] = min(100, state["mood"] + item["mood"])
    state["feed_count"] += 1

    # XP for feeding
    xp_gained = 3
    level_up = _add_xp(state, xp_gained)

    save_state(state)
    return {
        "ok": True,
        "food": food,
        "emoji": item["emoji"],
        "hunger": state["hunger"],
        "mood": state["mood"],
        "xp_gained": xp_gained,
        "level_up": level_up,
    }


def walk(state: dict) -> dict:
    """Take the companion for a walk."""
    state = apply_decay(state)

    if state["energy"] < 10:
        return {"ok": False, "error": f"{state['name']} is too tired! Let them rest."}

    species = state.get("species", "cat")
    events = WALK_EVENTS.get(species, WALK_EVENTS["cat"])
    event = random.choice(events)

    state["energy"] = max(0, state["energy"] - 15)
    state["mood"] = min(100, state["mood"] + event["mood"])
    state["walk_count"] += 1

    level_up = _add_xp(state, event["xp"])

    save_state(state)
    return {
        "ok": True,
        "event": event["text"],
        "xp_gained": event["xp"],
        "mood": state["mood"],
        "energy": state["energy"],
        "level_up": level_up,
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
    mood = state.get("mood", 50)

    prefixes = {
        "cat": {
            "happy": "*purrs contentedly*",
            "neutral": "*licks paw*",
            "grumpy": "*hisses softly*",
        },
        "dog": {
            "happy": "*tail wagging intensifies*",
            "neutral": "*tilts head*",
            "grumpy": "*whimpers*",
        },
        "penguin": {
            "happy": "*adjusts bowtie proudly*",
            "neutral": "*waddles in place*",
            "grumpy": "*stares disapprovingly*",
        },
        "fox": {
            "happy": "*does a little pounce*",
            "neutral": "*ear flicks*",
            "grumpy": "*narrows eyes*",
        },
        "owl": {
            "happy": "*hoots melodically*",
            "neutral": "*blinks slowly*",
            "grumpy": "*ruffles feathers*",
        },
        "dragon": {
            "happy": "*tiny flame of joy*",
            "neutral": "*smoke puff*",
            "grumpy": "*ember snort*",
        },
    }

    mood_key = "happy" if mood >= 70 else "grumpy" if mood <= 30 else "neutral"
    return prefixes.get(species, prefixes["cat"]).get(mood_key, "")


def get_status(state: dict) -> dict:
    """Get full companion status with decay applied."""
    state = apply_decay(state)
    save_state(state)
    return {
        "name": state["name"],
        "species": state["species"],
        "hunger": state["hunger"],
        "mood": state["mood"],
        "energy": state["energy"],
        "xp": state["xp"],
        "level": state["level"],
        "xp_to_next": state["xp_to_next"],
        "walk_count": state["walk_count"],
        "feed_count": state["feed_count"],
        "mood_prefix": get_mood_prefix(state),
    }

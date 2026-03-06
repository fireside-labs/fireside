"""
plasticity.py — Neural plasticity score for the Freya mesh.

Plasticity measures how fast the mesh is actively learning and adapting
right now, on a scale of 0-100:

  0   = rigid    — nothing is changing, mesh is frozen
  1-25  = slow   — minimal new knowledge, low activity
  26-50 = warming — moderate learning, some contradiction resolution
  51-75 = plastic — actively absorbing new knowledge and healing
  76-100 = hyperplastic — rapid learning, mesh in high-growth state

Score is a weighted composite of 5 signals, each normalised 0-1:

  Signal              Weight  Source
  ──────────────────  ──────  ───────────────────────────────────────
  memory_velocity     30%     new memories written in last 24h / 50
  healing_rate        20%     healing events in last 24h / 5
  contradiction_churn 15%     contradiction events found / 10  (0->bad, cap at 10)
  attention_entropy   20%     current attention entropy (0=focused=learning deep)
  metabolic_momentum  15%     metabolic_rate / 100

GET /plasticity returns:
{
  "plasticity_score": 62.4,
  "label":            "plastic",
  "signals": {
    "memory_velocity":     0.6,
    "healing_rate":        0.4,
    "contradiction_churn": 0.2,
    "attention_entropy":   0.73,
    "metabolic_momentum":  0.38
  },
  "raw": {
    "new_memories_24h":   30,
    "healings_24h":       2,
    "contradictions_24h": 2,
    "attention_entropy":  0.73,
    "metabolic_rate":     38.0
  },
  "computed_at": "2026-03-06T09:21:00"
}
"""

import datetime
import json
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Signal extraction helpers
# ---------------------------------------------------------------------------

def _journal_events_24h(journal_file: str, event_types: list) -> dict:
    """Count events by type from JSONL dream journal in the last 24 hours."""
    counts = {et: 0 for et in event_types}
    cutoff = time.time() - 86400
    try:
        p = Path(journal_file)
        if not p.exists():
            return counts
        with open(journal_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("ts", 0) >= cutoff:
                        ev = entry.get("event", "")
                        if ev in counts:
                            counts[ev] += 1
                except Exception:
                    pass
    except Exception:
        pass
    return counts


def _get_attention_entropy() -> float:
    """Get current attention entropy (0=focused, 1=scattered)."""
    try:
        from war_room import attention as _att
        data = _att.get_attention()
        return float(data.get("attention_entropy", 0.5))
    except Exception:
        return 0.5


def _get_metabolic_rate() -> float:
    """Get current metabolic rate (work_units/hr)."""
    try:
        from war_room import metabolic as _met
        data = _met.get_rate()
        return float(data.get("metabolic_rate", 0.0))
    except Exception:
        return 0.0


def _get_journal_file() -> str:
    """Get the dream journal path from dream_journal module."""
    try:
        from war_room import dream_journal as _dj
        return _dj.JOURNAL_FILE
    except Exception:
        import os
        return str(Path(__file__).parent.parent / "dream_journal.jsonl")


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

# Normalisation caps (tweak to taste)
_MEM_VELOCITY_CAP     = 50   # 50 new memories/24h = fully plastic
_HEALING_CAP          = 5    # 5 heals/24h = fully plastic
_CONTRADICTION_CAP    = 10   # 10 contradictions/24h = max churn
_METABOLIC_RATE_CAP   = 100  # 100 work-units/hr = max momentum

def get_plasticity() -> dict:
    """Compute and return the neural plasticity snapshot."""
    jf = _get_journal_file()

    # Pull 24h counts from dream journal
    counts = _journal_events_24h(
        jf,
        ["consolidation", "milestone", "healing", "contradiction"]
    )
    new_memories_24h   = counts["consolidation"] * 5 + counts["milestone"]
    healings_24h       = counts["healing"]
    contradictions_24h = counts["contradiction"]

    # Attention + metabolic
    att_entropy  = _get_attention_entropy()
    metabolic    = _get_metabolic_rate()

    # Normalise signals (0-1)
    s_velocity      = min(1.0, new_memories_24h   / _MEM_VELOCITY_CAP)
    s_healing       = min(1.0, healings_24h        / _HEALING_CAP)
    s_churn         = min(1.0, contradictions_24h  / _CONTRADICTION_CAP)
    s_entropy       = att_entropy                   # already 0-1
    s_metabolic     = min(1.0, metabolic            / _METABOLIC_RATE_CAP)

    # Weighted composite
    score_raw = (
        s_velocity  * 0.30 +
        s_healing   * 0.20 +
        s_churn     * 0.15 +
        s_entropy   * 0.20 +
        s_metabolic * 0.15
    )
    score = round(score_raw * 100, 1)

    # Label
    if score < 5:
        label = "rigid"
    elif score < 26:
        label = "slow"
    elif score < 51:
        label = "warming"
    elif score < 76:
        label = "plastic"
    else:
        label = "hyperplastic"

    return {
        "plasticity_score": score,
        "label":            label,
        "signals": {
            "memory_velocity":     round(s_velocity, 3),
            "healing_rate":        round(s_healing, 3),
            "contradiction_churn": round(s_churn, 3),
            "attention_entropy":   round(s_entropy, 3),
            "metabolic_momentum":  round(s_metabolic, 3),
        },
        "raw": {
            "new_memories_24h":   new_memories_24h,
            "healings_24h":       healings_24h,
            "contradictions_24h": contradictions_24h,
            "attention_entropy":  round(att_entropy, 3),
            "metabolic_rate":     round(metabolic, 2),
        },
        "weights": {
            "memory_velocity":     "30%",
            "healing_rate":        "20%",
            "contradiction_churn": "15%",
            "attention_entropy":   "20%",
            "metabolic_momentum":  "15%",
        },
        "computed_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }

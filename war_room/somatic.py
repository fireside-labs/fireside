"""
somatic.py — Somatic Markers / Emotional Intuition (Pillar 10)

Theory (Antonio Damasio):
    Emotions are compressed wisdom. The body's visceral reactions to past
    outcomes are stored as "somatic markers" — shortcut heuristics that bias
    decision-making before slow conscious reasoning kicks in.

Application:
    Before high-stakes actions (hypothesis generation, sharing, dream seeding,
    large tasks), the node queries its memory for emotionally similar past
    experiences. If negative-valence memories dominate the neighborhood, the
    node signals "reluctance" — either escalating to a human or refusing
    automatically.

Mechanism:
    gut_check(action_text, threshold=-0.3) -> GutResult
        1. Embed the action description
        2. Query memory for k=10 nearest neighbors
        3. Compute valence-weighted signal: mean(valence * importance) for neighbors
        4. If signal < threshold  → reluctance (block or escalate)
        5. If signal > |threshold| → confidence boost
        6. Publish somatic.checked event to event bus

GutResult:
    signal:    float   — weighted emotional signal (-1.0 bad → +1.0 good)
    reluctant: bool    — True if signal < threshold
    memories:  list    — top 3 influencing memories (for transparency)
    verdict:   str     — "proceed" | "reluctant" | "blocked"

Endpoints (wired in bifrost_local.py):
    POST /gut-check  {action: str, threshold?: float}
    GET  /somatic-state   — recent gut checks + running signal history
"""

import json
import logging
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional
from collections import deque
from dataclasses import dataclass, asdict

log = logging.getLogger("bifrost.somatic")

_OLLAMA_BASE  = "http://127.0.0.1:11434"
_EMBED_MODEL  = "nomic-embed-text"
_DB_PATH      = os.environ.get(
    "BIFROST_HYP_DB",
    str(Path(__file__).parent.parent / "memory.db")
)
_MEMORY_TABLE = "mesh_memories"

# Rolling history of recent gut checks (for GET /somatic-state)
_history: deque = deque(maxlen=100)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class GutResult:
    signal:    float        # weighted valence signal
    reluctant: bool         # True if signal < threshold
    verdict:   str          # "proceed" | "reluctant" | "blocked"
    memories:  list         # top influencing memories [{text, valence, importance}]
    action:    str          # the action being evaluated
    ts:        int

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

def _embed(text: str) -> Optional[list]:
    try:
        body = json.dumps({"model": _EMBED_MODEL, "prompt": text[:6000]}).encode()
        req  = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/embeddings",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("embedding")
    except Exception as e:
        log.debug("[somatic] embed failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Core gut-check logic
# ---------------------------------------------------------------------------

def gut_check(
    action: str,
    threshold: float = -0.3,
    block_threshold: float = -0.65,
    k: int = 10,
) -> GutResult:
    """
    Evaluate the emotional signal of a proposed action by querying
    memory for past emotionally similar experiences.

    threshold:       if signal < threshold  → reluctant (warn / escalate)
    block_threshold: if signal < block_thr  → blocked (hard refuse)
    k:               number of nearest memory neighbors to consult
    """
    ts = int(time.time())

    action_emb = _embed(action)
    if action_emb is None:
        # No embedding available — neutral pass
        result = GutResult(
            signal=0.0, reluctant=False, verdict="proceed",
            memories=[], action=action[:80], ts=ts
        )
        _history.append(result.to_dict())
        return result

    # Query memory for emotionally similar experiences
    neighbors = []
    try:
        import lancedb
        db  = lancedb.connect(_DB_PATH)
        tbl = db.open_table(_MEMORY_TABLE)
        rows = tbl.search(action_emb).limit(k).to_list()
        for r in rows:
            val  = float(r.get("valence", 0.0))
            imp  = float(r.get("importance", 0.5))
            text = str(r.get("text", r.get("content", "")))[:100]
            neighbors.append({"text": text, "valence": val, "importance": imp})
    except Exception as e:
        log.debug("[somatic] memory query failed: %s", e)

    if not neighbors:
        result = GutResult(
            signal=0.0, reluctant=False, verdict="proceed",
            memories=[], action=action[:80], ts=ts
        )
        _history.append(result.to_dict())
        return result

    # Compute valence-weighted signal
    # Signal = mean(valence_i * importance_i) — importance-weighted emotional average
    weighted_sum = sum(n["valence"] * n["importance"] for n in neighbors)
    weight_total = sum(n["importance"] for n in neighbors) or 1.0
    signal = weighted_sum / weight_total

    # Sort by absolute valence to surface most emotionally charged memories
    top = sorted(neighbors, key=lambda n: abs(n["valence"]), reverse=True)[:3]

    # Determine verdict
    if signal < block_threshold:
        verdict   = "blocked"
        reluctant = True
    elif signal < threshold:
        verdict   = "reluctant"
        reluctant = True
    else:
        verdict   = "proceed"
        reluctant = False

    result = GutResult(
        signal=round(signal, 4),
        reluctant=reluctant,
        verdict=verdict,
        memories=top,
        action=action[:80],
        ts=ts,
    )
    _history.append(result.to_dict())
    log.info("[somatic] gut_check '%s...' → signal=%.3f verdict=%s",
             action[:40], signal, verdict)

    # Publish to event bus
    try:
        from war_room import event_bus as bus
        bus.publish("somatic.checked", {
            "action":   action[:80],
            "signal":   round(signal, 4),
            "verdict":  verdict,
        })
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check(action: str, threshold: float = -0.3) -> dict:
    """Dict-returning wrapper for HTTP handlers."""
    return gut_check(action, threshold).to_dict()


def get_state(limit: int = 20) -> dict:
    """Return recent gut check history. Used by GET /somatic-state."""
    recent = list(reversed(list(_history)))[:limit]
    if not recent:
        return {"count": 0, "recent": [], "avg_signal": None}
    signals = [e["signal"] for e in recent]
    avg     = sum(signals) / len(signals)
    return {
        "count":      len(list(_history)),
        "avg_signal": round(avg, 4),
        "recent":     recent,
    }

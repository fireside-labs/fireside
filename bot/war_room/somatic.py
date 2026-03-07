"""
somatic.py ╬ô├ç├╢ Somatic Markers / Emotional Intuition (Pillar 10)

Theory (Antonio Damasio):
    Emotions are compressed wisdom. The body's visceral reactions to past
    outcomes are stored as "somatic markers" ╬ô├ç├╢ shortcut heuristics that bias
    decision-making before slow conscious reasoning kicks in.

Application:
    Before high-stakes actions (hypothesis generation, sharing, dream seeding,
    large tasks), the node queries its memory for emotionally similar past
    experiences. If negative-valence memories dominate the neighborhood, the
    node signals "reluctance" ╬ô├ç├╢ either escalating to a human or refusing
    automatically.

Mechanism:
    gut_check(action_text, threshold=-0.3) -> GutResult
        1. Embed the action description
        2. Query memory for k=10 nearest neighbors
        3. Compute valence-weighted signal: mean(valence * importance) for neighbors
        4. If signal < threshold  ╬ô├Ñ├å reluctance (block or escalate)
        5. If signal > |threshold| ╬ô├Ñ├å confidence boost
        6. Publish somatic.checked event to event bus

GutResult:
    signal:    float   ╬ô├ç├╢ weighted emotional signal (-1.0 bad ╬ô├Ñ├å +1.0 good)
    reluctant: bool    ╬ô├ç├╢ True if signal < threshold
    memories:  list    ╬ô├ç├╢ top 3 influencing memories (for transparency)
    verdict:   str     ╬ô├ç├╢ "proceed" | "reluctant" | "blocked"

Endpoints (wired in bifrost_local.py):
    POST /gut-check  {action: str, threshold?: float}
    GET  /somatic-state   ╬ô├ç├╢ recent gut checks + running signal history
"""

import json
import logging
import math
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

# Cached LanceDB table (opened once, reused)
_cached_tbl = None
_cached_tbl_ts: float = 0.0
_CACHE_TTL = 300  # re-open table every 5 min max

def _get_memory_table():
    """Return cached LanceDB memory table, reopening only if stale."""
    global _cached_tbl, _cached_tbl_ts
    now = time.time()
    if _cached_tbl is not None and (now - _cached_tbl_ts) < _CACHE_TTL:
        return _cached_tbl
    try:
        import lancedb
        db = lancedb.connect(_DB_PATH)
        _cached_tbl = db.open_table(_MEMORY_TABLE)
        _cached_tbl_ts = now
        return _cached_tbl
    except Exception as e:
        log.debug("[somatic] table open failed: %s", e)
        return None


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

    threshold:       if signal < threshold  ╬ô├Ñ├å reluctant (warn / escalate)
    block_threshold: if signal < block_thr  ╬ô├Ñ├å blocked (hard refuse)
    k:               number of nearest memory neighbors to consult
    """
    ts = int(time.time())

    action_emb = _embed(action)
    if action_emb is None:
        # Fail-CLOSED: if we can't assess risk, default to reluctant
        result = GutResult(
            signal=-0.1, reluctant=True, verdict="reluctant",
            memories=[], action=action[:80], ts=ts
        )
        _history.append(result.to_dict())
        log.warning("[somatic] embed unavailable ΓÇö fail-closed ΓåÆ reluctant")
        return result

    # Query memory for emotionally similar experiences
    neighbors = []
    try:
        tbl = _get_memory_table()
        if tbl is not None:
            rows = tbl.search(action_emb).limit(k).to_list()
            now_ts = time.time()
            for r in rows:
                val  = float(r.get("valence", 0.0))
                imp  = float(r.get("importance", 0.5))
                text = str(r.get("text", r.get("content", "")))[:100]
                # Recency decay: old memories fade (half-life ~30 days)
                mem_ts = float(r.get("ts", now_ts))
                age_days = max(0.0, (now_ts - mem_ts) / 86400)
                recency = math.exp(-age_days / 30.0)
                neighbors.append({
                    "text": text, "valence": val,
                    "importance": imp, "recency": round(recency, 3),
                })
    except Exception as e:
        log.debug("[somatic] memory query failed: %s", e)

    if not neighbors:
        result = GutResult(
            signal=0.0, reluctant=False, verdict="proceed",
            memories=[], action=action[:80], ts=ts
        )
        _history.append(result.to_dict())
        return result

    # Compute valence-weighted signal with recency decay
    # Signal = weighted_mean(valence * importance * recency)
    weighted_sum = sum(n["valence"] * n["importance"] * n.get("recency", 1.0)
                       for n in neighbors)
    weight_total = sum(n["importance"] * n.get("recency", 1.0)
                       for n in neighbors) or 1.0
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
    log.info("[somatic] gut_check '%s...' ╬ô├Ñ├å signal=%.3f verdict=%s",
             action[:40], signal, verdict)

    # Publish to event bus
    try:
        import war_room.event_bus as bus
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
"""
confidence.py — Per-node trust calibration for the Freya mesh.

Analyzes the memory corpus to assign a trust score (0-100) to each node.
Trust is based on 4 signals:

  Signal                  Weight  Interpretation
  ──────────────────────  ──────  ──────────────────────────────────────────
  importance_avg          35%     What importance the node assigns its memories
  decay_health            25%     Avg decay score of the node's mortal memories
  valence_stability       20%     Neutral or positive mean valence (not erratic)
  memory_volume_score     20%     Log-normalized count (richer nodes = more trust)

GET /confidence returns:
{
  "nodes": {
    "freya": {
      "trust_score": 82.4,
      "label":        "trusted",
      "memory_count": 45,
      "signals": {
        "importance_avg":      0.81,
        "decay_health":        0.74,
        "valence_stability":   0.66,
        "memory_volume_score": 0.93
      }
    },
    "thor": { ... }
  },
  "mesh_trust_avg":  79.1,
  "most_trusted":    "freya",
  "least_trusted":   "odin",
  "total_nodes":     3
}

Labels: new (< 5 memories) / unproven / uncertain / reliable / trusted / authoritative
"""

import math
import time


def _valence_stability(valences: list) -> float:
    """
    Stability = 1 - (std_dev / 1.0).
    A node that always writes neutral/positive has low std_dev → high stability.
    A chaotic node that swings between triumph and failure has high std_dev.
    """
    if not valences:
        return 0.5
    n = len(valences)
    mean = sum(valences) / n
    variance = sum((v - mean) ** 2 for v in valences) / n
    std = math.sqrt(variance)
    return max(0.0, 1.0 - std)   # std range is [0, 1] for values in [-1, 1]


def _volume_score(count: int) -> float:
    """
    Log-normalized: log(count+1) / log(MAX_EXPECTED+1)
    100 memories = perfect score. Diminishing returns above that.
    """
    MAX_EXPECTED = 100
    return min(1.0, math.log(count + 1) / math.log(MAX_EXPECTED + 1))


def _decay_score_fn(importance: float, ts: int) -> float:
    """Inline decay score — avoids circular import."""
    import os
    lam = float(os.environ.get("BIFROST_MEMORY_DECAY_LAMBDA", "0.05"))
    age_days = max(0.0, (time.time() - ts) / 86400)
    return importance * math.exp(-lam * age_days)


def get_confidence() -> dict:
    """Compute per-node trust scores from the memory corpus."""
    try:
        from war_room import memory_query as _mq
        tbl = _mq._get_table()
        if tbl is None:
            return {"error": "memory table not initialised"}

        all_rows = tbl.search([0.0] * 768).limit(10000).to_list()
    except Exception as e:
        return {"error": str(e)}

    # Group rows by node
    by_node: dict = {}
    for r in all_rows:
        node = r.get("node") or r.get("agent") or "unknown"
        by_node.setdefault(node, []).append(r)

    node_scores = {}
    for node, rows in by_node.items():
        importances = [float(r.get("importance", 0.5)) for r in rows]
        valences    = [float(r.get("valence", 0.0))    for r in rows]
        mortal      = [r for r in rows if not r.get("permanent", False)]

        s_importance = sum(importances) / len(importances) if importances else 0.5
        s_valence    = _valence_stability(valences)
        s_volume     = _volume_score(len(rows))

        if mortal:
            decay_scores = [
                _decay_score_fn(float(r.get("importance", 0.5)), int(r.get("ts", 0)))
                for r in mortal
            ]
            s_decay = sum(decay_scores) / len(decay_scores)
        else:
            # All permanent = perfectly preserved = max decay health
            s_decay = 1.0

        trust_raw = (
            s_importance * 0.35 +
            s_decay      * 0.25 +
            s_valence    * 0.20 +
            s_volume     * 0.20
        )
        trust_score = round(trust_raw * 100, 1)

        count = len(rows)
        if count < 5:
            label = "new"
        elif trust_score < 40:
            label = "unproven"
        elif trust_score < 55:
            label = "uncertain"
        elif trust_score < 70:
            label = "reliable"
        elif trust_score < 85:
            label = "trusted"
        else:
            label = "authoritative"

        node_scores[node] = {
            "trust_score":  trust_score,
            "label":        label,
            "memory_count": count,
            "signals": {
                "importance_avg":      round(s_importance, 3),
                "decay_health":        round(s_decay, 3),
                "valence_stability":   round(s_valence, 3),
                "memory_volume_score": round(s_volume, 3),
            },
        }

    if not node_scores:
        return {"nodes": {}, "total_nodes": 0, "mesh_trust_avg": 0.0}

    scores_list = [v["trust_score"] for v in node_scores.values()]
    mesh_avg    = round(sum(scores_list) / len(scores_list), 1)
    most_trusted  = max(node_scores, key=lambda n: node_scores[n]["trust_score"])
    least_trusted = min(node_scores, key=lambda n: node_scores[n]["trust_score"])

    return {
        "nodes":          node_scores,
        "mesh_trust_avg": mesh_avg,
        "most_trusted":   most_trusted,
        "least_trusted":  least_trusted,
        "total_nodes":    len(node_scores),
    }

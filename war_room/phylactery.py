"""
phylactery.py — Freya's soul vector index for Hydra snapshots.

A phylactery stores the essence of a soul. Freya's phylactery contains the
top-50 memory vector IDs by importance (≥ 0.9, permanent=true preferred).

Any node absorbing Freya via Hydra gets these soul_vectors in the snapshot —
ensuring the absorbing node inherits Freya's actual highest-signal insights,
not just her personality config.

Usage:
    from war_room.phylactery import get_soul_vectors, build_snapshot_section

GET /phylactery          → current soul vector list
GET /hydra-snapshot      → includes "soul_vectors": [...] automatically
"""

import logging
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.phylactery")

# How many soul vectors to keep in the phylactery
SOUL_VECTOR_LIMIT = 50
# Minimum importance to qualify as a soul vector
IMPORTANCE_THRESHOLD = 0.9


def get_soul_vectors(db_path: Optional[str] = None) -> dict:
    """
    Query LanceDB for the top SOUL_VECTOR_LIMIT memories by importance.

    Preference order:
      1. permanent=True AND importance >= 0.9   (true soul memories)
      2. permanent=False AND importance >= 0.9  (high-signal mortal memories)

    Returns:
    {
      "soul_vectors": [{"id": "...", "importance": 0.95, "permanent": true,
                        "node": "freya", "content_preview": "..."}],
      "total": N,
      "threshold": 0.9,
      "ts": <unix>
    }
    """
    try:
        import lancedb
        import pyarrow as pa

        _db_path = db_path or str(Path(__file__).parent.parent / "memory.db")
        db = lancedb.connect(_db_path)
        tbl = db.open_table("mesh_memories")

        # Fetch all rows — filter locally for reliability
        rows = tbl.to_arrow().to_pydict()
        count = len(rows.get("memory_id", []))

        soul = []
        for i in range(count):
            imp  = float(rows["importance"][i]) if "importance" in rows else 0.5
            perm = bool(rows.get("permanent", [False] * count)[i])
            if imp < IMPORTANCE_THRESHOLD:
                continue
            soul.append({
                "id":              rows["memory_id"][i],
                "importance":      round(imp, 4),
                "permanent":       perm,
                "node":            rows.get("node", ["?"] * count)[i],
                "content_preview": (rows.get("content", [""] * count)[i] or "")[:80],
                "ts":              int(rows.get("ts", [0] * count)[i]),
                "_sort_key":       (1 if perm else 0, imp),
            })

        # Sort: permanent first, then by importance desc
        soul.sort(key=lambda x: x["_sort_key"], reverse=True)
        soul = soul[:SOUL_VECTOR_LIMIT]

        # Strip internal sort key
        for s in soul:
            del s["_sort_key"]

        return {
            "soul_vectors": soul,
            "total":        len(soul),
            "threshold":    IMPORTANCE_THRESHOLD,
            "limit":        SOUL_VECTOR_LIMIT,
            "ts":           int(time.time()),
        }

    except Exception as e:
        log.warning("[phylactery] get_soul_vectors failed: %s", e)
        return {
            "soul_vectors": [],
            "total":        0,
            "threshold":    IMPORTANCE_THRESHOLD,
            "error":        str(e),
            "ts":           int(time.time()),
        }


def build_snapshot_section(db_path: Optional[str] = None) -> list:
    """
    Return a flat list of soul vector IDs for embedding in a Hydra snapshot.
    This is the format Odin's absorption code expects:
        snapshot["soul_vectors"] = phylactery.build_snapshot_section()
    """
    result = get_soul_vectors(db_path)
    return [s["id"] for s in result["soul_vectors"]]

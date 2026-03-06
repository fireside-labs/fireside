"""
procedures.py — Freya's Procedural Memory.

Captures *how to approach* a task type, not just what happened.
Procedures persist across sessions so the mesh gets smarter at
specific task types over time — no more rediscovering optimal
approaches every run.

LanceDB table: "procedures"

Schema:
{
  "id":          "proc_<uuid>",
  "task_type":   "crispr_prompt_optimization",
  "approach":    "Use layered specificity: broad biology → gene target → delivery.",
  "outcome":     "success" | "failure" | "partial",
  "confidence":  0.87,     # float 0.0–1.0
  "uses":        4,        # how many times this procedure was applied
  "last_used":   1741283000,
  "tags":        ["crispr", "prompt"],
  "permanent":   True,
}

Ranking: confidence × log(1 + uses)  → frequently-used successful procedures float up.

Endpoints (wired in bifrost_local.py):
  POST /procedure   {task_type, approach, outcome, confidence, tags, ...}
      → upsert: exact task_type match → update; novel → insert
  GET  /procedures?task_type=<t>&limit=5
      → top procedures by rank score

Philosopher's Stone hook:
  GET /procedures?limit=20 returns top-20 across all task types.
  Include in Odin's nightly prompt as ## Proven Approaches section.

Self-population:
  auto_record(task_type, approach, outcome, confidence) — called from
  bifrost_local after successful task completion or Stand downgrade.
"""

import json
import logging
import math
import os
import time
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.procedures")

PROC_DB_PATH = os.environ.get(
    "BIFROST_PROC_DB",
    str(Path(__file__).parent.parent / "memory.db"),
)
PROC_TABLE  = "procedures"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_BASE = "http://127.0.0.1:11434"
EMBED_MAX_CHARS = 6000   # same truncation guard as memory_query


# ---------------------------------------------------------------------------
# Embedding helper (reuse Ollama like memory_query does)
# ---------------------------------------------------------------------------

def _embed(text: str) -> Optional[list]:
    import urllib.request
    try:
        payload = json.dumps({"model": EMBED_MODEL, "prompt": text[:EMBED_MAX_CHARS]}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/embeddings",
            data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()).get("embedding")
    except Exception as e:
        log.warning("[procedures] embed failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_db   = None
_tbl  = None


def _get_db():
    global _db
    if _db is None:
        import lancedb
        _db = lancedb.connect(PROC_DB_PATH)
    return _db


def _get_table():
    global _tbl
    if _tbl is not None:
        return _tbl
    db = _get_db()
    if PROC_TABLE in db.table_names():
        _tbl = db.open_table(PROC_TABLE)
    return _tbl


def _ensure_table(dim: int):
    """Create procedures table if it doesn't exist yet."""
    global _tbl
    db = _get_db()
    if PROC_TABLE not in db.table_names():
        import pyarrow as pa
        schema = pa.schema([
            pa.field("id",        pa.string()),
            pa.field("task_type", pa.string()),
            pa.field("approach",  pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), dim)),
            pa.field("outcome",   pa.string()),
            pa.field("confidence",pa.float32()),
            pa.field("uses",      pa.int32()),
            pa.field("last_used", pa.int64()),
            pa.field("tags",      pa.list_(pa.string())),
            pa.field("permanent", pa.bool_()),
        ])
        _tbl = db.create_table(PROC_TABLE, data=[], schema=schema)
        log.info("[procedures] Created procedures table (dim=%d)", dim)
    else:
        _tbl = db.open_table(PROC_TABLE)
    return _tbl


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def _rank(confidence: float, uses: int) -> float:
    """confidence × log(1 + uses) — high-confidence frequently-used wins."""
    return float(confidence) * math.log1p(max(0, int(uses)))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upsert_procedure(
    task_type: str,
    approach: str,
    outcome: str = "success",
    confidence: float = 0.8,
    tags: Optional[list] = None,
    proc_id: Optional[str] = None,
    permanent: bool = True,
) -> dict:
    """
    Write or update a procedure.

    Update logic:
      1. Find existing procedures with same task_type.
      2. Embed new approach; check cosine similarity vs existing approaches.
      3. If similarity > 0.92 → update that row (bump uses, update confidence).
      4. Otherwise → insert as new procedure.

    Returns: {"ok": True, "id": "...", "action": "insert"|"update", "rank": float}
    """
    try:
        if not task_type or not approach:
            return {"error": "task_type and approach are required"}

        vec = _embed(approach)
        if vec is None:
            return {"error": "embedding failed — is Ollama running?"}

        dim = len(vec)
        tbl = _ensure_table(dim)

        # Look for existing procedures with the same task_type
        existing = []
        try:
            rows = tbl.to_arrow().to_pydict()
            n = len(rows.get("id", []))
            for i in range(n):
                if rows["task_type"][i] == task_type:
                    existing.append({
                        "id":         rows["id"][i],
                        "embedding":  list(rows["embedding"][i]),
                        "uses":       int(rows["uses"][i]),
                        "confidence": float(rows["confidence"][i]),
                    })
        except Exception:
            pass

        # Check similarity against existing approaches
        match_id = None
        if existing:
            from war_room.memory_query import _cosine_sim  # reuse existing helper
            for row in existing:
                sim = _cosine_sim(vec, row["embedding"])
                if sim > 0.92:
                    match_id = row["id"]
                    old_uses       = row["uses"]
                    old_confidence = row["confidence"]
                    break

        ts_now = int(time.time())

        if match_id:
            # Update existing: bump uses, blend confidence
            new_uses = old_uses + 1
            # Exponential moving average: 80% old, 20% new signal
            new_confidence = min(1.0, 0.8 * old_confidence + 0.2 * confidence)
            tbl.update(
                where=f"id = '{match_id}'",
                values={
                    "uses":       new_uses,
                    "confidence": new_confidence,
                    "last_used":  ts_now,
                    "outcome":    outcome,
                }
            )
            rank = _rank(new_confidence, new_uses)
            log.info("[procedures] Updated %s (uses=%d, conf=%.2f, rank=%.3f)",
                     match_id, new_uses, new_confidence, rank)
            return {"ok": True, "id": match_id, "action": "update",
                    "uses": new_uses, "confidence": round(new_confidence, 3),
                    "rank": round(rank, 3)}
        else:
            # Insert new procedure
            pid = proc_id or f"proc_{uuid.uuid4().hex[:12]}"
            row = {
                "id":         pid,
                "task_type":  task_type,
                "approach":   approach,
                "embedding":  [float(x) for x in vec],
                "outcome":    outcome,
                "confidence": float(confidence),
                "uses":       1,
                "last_used":  ts_now,
                "tags":       list(tags or []),
                "permanent":  bool(permanent),
            }
            tbl.add([row])
            rank = _rank(confidence, 1)
            log.info("[procedures] Inserted %s (task_type=%s, rank=%.3f)",
                     pid, task_type, rank)
            return {"ok": True, "id": pid, "action": "insert",
                    "uses": 1, "confidence": round(confidence, 3),
                    "rank": round(rank, 3)}

    except Exception as e:
        log.error("[procedures] upsert failed: %s", e)
        return {"error": str(e)}


def get_procedures(
    task_type: Optional[str] = None,
    limit: int = 5,
    min_confidence: float = 0.0,
) -> dict:
    """
    Retrieve top procedures ranked by confidence × log(1 + uses).

    If task_type given, filter to that type only.
    Philosopher's Stone calls this with limit=20, no task_type filter.
    """
    try:
        tbl = _get_table()
        if tbl is None:
            return {"procedures": [], "total": 0, "note": "no procedures recorded yet"}

        rows = tbl.to_arrow().to_pydict()
        n = len(rows.get("id", []))
        if n == 0:
            return {"procedures": [], "total": 0}

        results = []
        for i in range(n):
            tt  = rows["task_type"][i]
            conf = float(rows["confidence"][i])
            uses = int(rows["uses"][i])
            if task_type and tt != task_type:
                continue
            if conf < min_confidence:
                continue
            results.append({
                "id":         rows["id"][i],
                "task_type":  tt,
                "approach":   rows["approach"][i],
                "outcome":    rows["outcome"][i],
                "confidence": round(conf, 3),
                "uses":       uses,
                "last_used":  int(rows["last_used"][i]),
                "tags":       list(rows["tags"][i] or []),
                "permanent":  bool(rows["permanent"][i]),
                "rank":       round(_rank(conf, uses), 4),
            })

        results.sort(key=lambda x: x["rank"], reverse=True)
        results = results[:limit]

        return {
            "procedures":    results,
            "total":         len(results),
            "task_type":     task_type or "all",
            "limit":         limit,
        }

    except Exception as e:
        log.error("[procedures] get failed: %s", e)
        return {"error": str(e)}


def auto_record(
    task_type: str,
    approach: str,
    outcome: str = "success",
    confidence: float = 0.8,
    tags: Optional[list] = None,
) -> None:
    """
    Fire-and-forget procedure recording after task completion.
    Called from bifrost_local after successful task or Stand downgrade.
    """
    import threading
    def _do():
        try:
            result = upsert_procedure(task_type, approach, outcome,
                                      confidence, tags)
            log.debug("[procedures] auto_record: %s", result)
        except Exception as e:
            log.debug("[procedures] auto_record failed (non-critical): %s", e)
    threading.Thread(target=_do, daemon=True, name="proc-auto-record").start()


def stand_downgrade(task_type: str, approach_snippet: str) -> None:
    """
    Called when Thor's Stand flags a concern.
    Finds the closest matching procedure for this task_type and
    reduces its confidence by -0.1 (floor 0.1).
    """
    try:
        tbl = _get_table()
        if tbl is None:
            return
        vec = _embed(approach_snippet)
        if vec is None:
            return
        rows = tbl.to_arrow().to_pydict()
        n = len(rows.get("id", []))
        best_id, best_sim = None, 0.0
        from war_room.memory_query import _cosine_sim
        for i in range(n):
            if rows["task_type"][i] != task_type:
                continue
            sim = _cosine_sim(vec, list(rows["embedding"][i]))
            if sim > best_sim:
                best_sim = sim
                best_id  = rows["id"][i]
                best_conf = float(rows["confidence"][i])
        if best_id and best_sim > 0.7:
            new_conf = max(0.1, best_conf - 0.1)
            tbl.update(where=f"id = '{best_id}'",
                        values={"confidence": new_conf})
            log.info("[procedures] Stand downgrade: %s %.2f → %.2f",
                     best_id, best_conf, new_conf)
    except Exception as e:
        log.debug("[procedures] stand_downgrade failed: %s", e)

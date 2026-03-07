"""
procedures.py — Freya's Procedural Memory (v2).

Captures *how to approach* a task type — persistent skill across sessions.

LanceDB table: "procedures"

Schema:
  id          str   "proc_<uuid12>"
  task_type   str   "crispr_prompt_optimization"
  approach    str   full description of the approach taken
  embedding   f32[] nomic-embed-text vector of approach
  outcome     str   "success" | "failure" | "partial"
  confidence  f32   0.0 – 1.0
  uses        i32   times applied (incremented on each match-merge)
  last_used   i64   unix timestamp
  tags        str[] list of tag strings
  permanent   bool

Ranking:
  score = confidence × log(1 + uses) × recency_decay(last_used)
  where recency_decay = exp(-λ × age_days), λ=0.02 (half-life ~35 days)

  Frequently-used, recent, high-confidence procedures surface first.

Endpoints (wired in bifrost_local.py):
  POST  /procedure   {task_type, approach, outcome, confidence, tags}
  POST  /procedures  {procedures: [...]}   — batch insert
  GET   /procedures?task_type=t&q=text&limit=5&min_confidence=0.0
  DELETE /procedure?id=proc_xxx

Dedup: cosine similarity > 0.92 on same task_type → update, not insert.

Auto-population:
  auto_record(task_type, approach, outcome, confidence, tags)
  — fire-and-forget, called after /war-room/complete on Freya.

Stand downgrade:
  stand_downgrade(task_type, approach_snippet)
  — lowers confidence of closest matching procedure by 0.1.
"""

import json
import logging
import math
import os
import re
import time
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.procedures")

PROC_DB_PATH = os.environ.get(
    "BIFROST_PROC_DB",
    str(Path(__file__).parent.parent / "memory.db"),
)
PROC_TABLE    = "procedures"
EMBED_MODEL   = "nomic-embed-text"
OLLAMA_BASE   = "http://127.0.0.1:11434"
EMBED_MAX_CHARS = 6000
_DECAY_LAMBDA   = 0.02   # half-life ~35 days for recency factor


# ---------------------------------------------------------------------------
# Inline cosine similarity — no coupling to memory_query
# ---------------------------------------------------------------------------

def _cosine_sim(a: list, b: list) -> float:
    """Cosine similarity between two float vectors."""
    try:
        dot  = sum(x * y for x, y in zip(a, b))
        na   = math.sqrt(sum(x * x for x in a))
        nb   = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def _embed(text: str) -> Optional[list]:
    import urllib.request
    try:
        payload = json.dumps({
            "model": EMBED_MODEL,
            "prompt": text[:EMBED_MAX_CHARS],
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()).get("embedding")
    except Exception as e:
        log.warning("[procedures] embed failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# ID sanitization — prevent SQL injection via f-string where clauses
# ---------------------------------------------------------------------------

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

def _safe_id(value: str) -> str:
    """Raise ValueError if ID contains non-safe characters."""
    if not _SAFE_ID_RE.match(value):
        raise ValueError(f"Unsafe ID value: {value!r}")
    return value


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_db  = None
_tbl = None


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
    global _tbl
    db = _get_db()
    if PROC_TABLE not in db.table_names():
        import pyarrow as pa
        schema = pa.schema([
            pa.field("id",         pa.string()),
            pa.field("task_type",  pa.string()),
            pa.field("approach",   pa.string()),
            pa.field("embedding",  pa.list_(pa.float32(), dim)),
            pa.field("outcome",    pa.string()),
            pa.field("confidence", pa.float32()),
            pa.field("uses",       pa.int32()),
            pa.field("last_used",  pa.int64()),
            pa.field("tags",       pa.list_(pa.string())),
            pa.field("permanent",  pa.bool_()),
        ])
        _tbl = db.create_table(PROC_TABLE, data=[], schema=schema)
        log.info("[procedures] Created table (dim=%d)", dim)
    else:
        _tbl = db.open_table(PROC_TABLE)
    return _tbl


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def _rank(confidence: float, uses: int, last_used: int) -> float:
    """
    confidence × log(1 + uses) × recency_decay

    Recency decay: exp(-λ × age_days), λ=0.02, half-life ~35 days.
    A procedure used heavily but 6 months ago won't dominate a
    fresh but less-used one.
    """
    age_days = max(0.0, (time.time() - last_used) / 86400)
    recency  = math.exp(-_DECAY_LAMBDA * age_days)
    return float(confidence) * math.log1p(max(0, int(uses))) * recency


# ---------------------------------------------------------------------------
# Core upsert (single procedure)
# ---------------------------------------------------------------------------

def _upsert_one(
    task_type:  str,
    approach:   str,
    outcome:    str    = "success",
    confidence: float  = 0.8,
    tags:       list   = None,
    proc_id:    str    = None,
    permanent:  bool   = True,
) -> dict:
    """
    Inner upsert logic for a single procedure.
    Returns result dict with ok, id, action, uses, confidence, rank.
    """
    if not task_type or not approach:
        return {"error": "task_type and approach are required"}

    vec = _embed(approach)
    if vec is None:
        return {"error": "embedding failed — is Ollama running?"}

    dim = len(vec)
    tbl = _ensure_table(dim)
    ts_now = int(time.time())

    # Search for existing procedures with same task_type using LanceDB
    # vector search + where filter — avoids full table scan
    try:
        candidates = (
            tbl.search(vec)
               .where(f"task_type = '{task_type.replace(chr(39), '')}'")
               .limit(10)
               .to_list()
        )
    except Exception:
        candidates = []

    # Find a close enough match (cosine > 0.92)
    match_id      = None
    old_uses      = 0
    old_confidence = 0.0
    for row in candidates:
        sim = _cosine_sim(vec, list(row.get("embedding", [])))
        if sim > 0.92:
            match_id       = row["id"]
            old_uses       = int(row.get("uses", 0))
            old_confidence = float(row.get("confidence", 0.8))
            break

    if match_id:
        # Update existing — bump uses, EMA-blend confidence
        try:
            safe_mid  = _safe_id(match_id)
        except ValueError as e:
            return {"error": str(e)}

        new_uses       = old_uses + 1
        new_confidence = min(1.0, 0.8 * old_confidence + 0.2 * confidence)
        tbl.update(
            where=f"id = '{safe_mid}'",
            values={
                "uses":       new_uses,
                "confidence": new_confidence,
                "last_used":  ts_now,
                "outcome":    outcome,
            },
        )
        rank = _rank(new_confidence, new_uses, ts_now)
        log.info("[procedures] Updated %s (uses=%d conf=%.2f rank=%.3f)",
                 match_id, new_uses, new_confidence, rank)
        return {
            "ok":         True,
            "id":         match_id,
            "action":     "update",
            "uses":       new_uses,
            "confidence": round(new_confidence, 3),
            "rank":       round(rank, 3),
        }
    else:
        # Insert new
        pid = proc_id or f"proc_{uuid.uuid4().hex[:12]}"
        tbl.add([{
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
        }])
        rank = _rank(confidence, 1, ts_now)
        log.info("[procedures] Inserted %s (task_type=%s rank=%.3f)", pid, task_type, rank)
        return {
            "ok":         True,
            "id":         pid,
            "action":     "insert",
            "uses":       1,
            "confidence": round(confidence, 3),
            "rank":       round(rank, 3),
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upsert_procedure(
    task_type:  str,
    approach:   str,
    outcome:    str   = "success",
    confidence: float = 0.8,
    tags:       list  = None,
    proc_id:    str   = None,
    permanent:  bool  = True,
) -> dict:
    """POST /procedure — write or update a single procedure."""
    try:
        return _upsert_one(task_type, approach, outcome, confidence,
                           tags, proc_id, permanent)
    except Exception as e:
        log.error("[procedures] upsert failed: %s", e)
        return {"error": str(e)}


def upsert_batch(procedures: list) -> dict:
    """
    POST /procedures — batch upsert a list of procedures.
    Each item should have: task_type, approach, and optionally
    outcome, confidence, tags, id, permanent.
    Returns {"results": [...], "inserted": N, "updated": N, "errors": N}
    """
    results  = []
    inserted = updated = errors = 0
    for p in procedures:
        try:
            r = _upsert_one(
                task_type  = p.get("task_type", ""),
                approach   = p.get("approach", ""),
                outcome    = p.get("outcome", "success"),
                confidence = float(p.get("confidence", 0.8)),
                tags       = p.get("tags", []),
                proc_id    = p.get("id"),
                permanent  = bool(p.get("permanent", True)),
            )
            results.append(r)
            if r.get("ok"):
                if r["action"] == "insert": inserted += 1
                else:                        updated  += 1
            else:
                errors += 1
        except Exception as e:
            results.append({"error": str(e)})
            errors += 1

    return {"results": results, "inserted": inserted,
            "updated": updated, "errors": errors}


def get_procedures(
    task_type:      Optional[str] = None,
    q:              Optional[str] = None,
    limit:          int   = 5,
    min_confidence: float = 0.0,
) -> dict:
    """
    GET /procedures?task_type=t&q=text&limit=5&min_confidence=0.0

    If q is given: vector search on approach embedding, then filter.
    If task_type only: where-filter + vector search with zero vector.
    Both use LanceDB search — no full table scan.
    Ranked by: confidence × log(1+uses) × recency_decay.
    """
    try:
        tbl = _get_table()
        if tbl is None:
            return {"procedures": [], "total": 0,
                    "note": "no procedures recorded yet"}

        # Embed the query text (or use zero vector to get all rows ranked)
        if q:
            vec = _embed(q)
            if vec is None:
                return {"error": "embedding failed — is Ollama running?"}
        else:
            # Probe vector dimension from table, fall back to 768
            try:
                sample = tbl.search().limit(1).to_list()
                emb = sample[0].get("embedding", []) if sample else []
                dim = len(emb) if emb else 768
            except Exception:
                dim = 768
            vec = [0.0] * dim

        # Build where clause (task_type filter, safe)
        where = None
        if task_type:
            safe_tt = task_type.replace("'", "")
            where   = f"task_type = '{safe_tt}'"

        # LanceDB vector search with optional where filter
        search = tbl.search(vec).limit(limit * 4)
        if where:
            search = search.where(where)
        rows = search.to_list()

        # Post-filter on min_confidence, then rank and trim
        results = []
        for r in rows:
            conf = float(r.get("confidence", 0.0))
            if conf < min_confidence:
                continue
            uses      = int(r.get("uses", 1))
            last_used = int(r.get("last_used", 0))
            results.append({
                "id":         r["id"],
                "task_type":  r["task_type"],
                "approach":   r["approach"],
                "outcome":    r["outcome"],
                "confidence": round(conf, 3),
                "uses":       uses,
                "last_used":  last_used,
                "tags":       list(r.get("tags") or []),
                "permanent":  bool(r.get("permanent", False)),
                "rank":       round(_rank(conf, uses, last_used), 4),
            })

        results.sort(key=lambda x: x["rank"], reverse=True)
        results = results[:limit]

        return {
            "procedures":    results,
            "total":         len(results),
            "task_type":     task_type or "all",
            "query":         q,
            "limit":         limit,
        }

    except Exception as e:
        log.error("[procedures] get failed: %s", e)
        return {"error": str(e)}


def delete_procedure(proc_id: str) -> dict:
    """DELETE /procedure?id=proc_xxx — remove a bad procedure."""
    try:
        safe_mid = _safe_id(proc_id)
    except ValueError as e:
        return {"error": str(e)}

    try:
        tbl = _get_table()
        if tbl is None:
            return {"error": "procedures table not initialized"}

        # Verify it exists first
        rows = tbl.search().where(f"id = '{safe_mid}'").limit(1).to_list()
        if not rows:
            return {"error": f"procedure {proc_id!r} not found"}

        tbl.delete(f"id = '{safe_mid}'")
        log.info("[procedures] Deleted procedure %s", proc_id)
        return {"ok": True, "deleted": proc_id}

    except Exception as e:
        log.error("[procedures] delete failed: %s", e)
        return {"error": str(e)}


def auto_record(
    task_type:  str,
    approach:   str,
    outcome:    str   = "success",
    confidence: float = 0.8,
    tags:       list  = None,
) -> None:
    """
    Fire-and-forget procedure recording after task completion.
    Called from bifrost_local after /war-room/complete on Freya.
    """
    import threading
    def _do():
        try:
            r = _upsert_one(task_type, approach, outcome, confidence, tags)
            log.debug("[procedures] auto_record: %s", r)
        except Exception as e:
            log.debug("[procedures] auto_record failed (non-critical): %s", e)
    threading.Thread(target=_do, daemon=True, name="proc-auto-record").start()


def stand_downgrade(task_type: str, approach_snippet: str) -> None:
    """
    Called when Thor's Stand flags a concern.
    Finds the closest matching procedure for task_type via vector search
    and reduces its confidence by 0.1 (floor 0.1).
    """
    try:
        tbl = _get_table()
        if tbl is None:
            return
        vec = _embed(approach_snippet)
        if vec is None:
            return

        safe_tt = task_type.replace("'", "")
        rows = (
            tbl.search(vec)
               .where(f"task_type = '{safe_tt}'")
               .limit(3)
               .to_list()
        )
        if not rows:
            return

        # Pick closest by cosine similarity
        best = max(rows, key=lambda r: _cosine_sim(vec, list(r.get("embedding", []))))
        sim = _cosine_sim(vec, list(best.get("embedding", [])))
        if sim < 0.7:
            return  # not close enough to downgrade

        try:
            safe_mid = _safe_id(best["id"])
        except ValueError:
            return

        old_conf = float(best.get("confidence", 0.5))
        new_conf = max(0.1, old_conf - 0.1)
        tbl.update(where=f"id = '{safe_mid}'", values={"confidence": new_conf})
        log.info("[procedures] Stand downgrade: %s %.2f → %.2f (sim=%.2f)",
                 best["id"], old_conf, new_conf, sim)

    except Exception as e:
        log.debug("[procedures] stand_downgrade failed: %s", e)

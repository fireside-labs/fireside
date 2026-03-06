"""
memory_query.py — Freya's semantic memory query interface.

Handles GET /memory-query?q=<text>&limit=10&tags=python,sql&node=thor

Uses Ollama's /api/embeddings to embed the query, then performs
vector similarity search over the local LanceDB memory table
(populated by Thor's gossip sync engine via POST /memory-sync).

Schema (locked by Odin, extended by Freya):
{
    "memory_id": str,
    "node":      str,
    "agent":     str,
    "content":   str,
    "embedding": list[float],
    "tags":      list[str],
    "importance": float,
    "ts":        int,
    "shared":    bool,
    "permanent": bool,   # Deep Convictions — never pruned or consolidated
    "valence":   float   # -1.0 (failure/pain) to +1.0 (success/triumph). Auto-detected.
}
"""

import json
import logging
import math
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.memory")

OLLAMA_BASE = "http://127.0.0.1:11434"
EMBED_TIMEOUT = 30
EMBED_MODEL = "nomic-embed-text"   # fast, small — good for retrieval

# DB lives next to the bot directory so it persists across restarts
_DEFAULT_DB_PATH = str(Path(__file__).parent.parent / "memory.db")
MEMORY_DB_PATH = os.environ.get("BIFROST_MEMORY_DB", _DEFAULT_DB_PATH)
TABLE_NAME = "mesh_memories"

_db = None
_table = None


def _get_db():
    """Lazy-init LanceDB connection."""
    global _db
    if _db is None:
        try:
            import lancedb
            _db = lancedb.connect(MEMORY_DB_PATH)
            log.info("LanceDB connected at %s", MEMORY_DB_PATH)
        except Exception as e:
            log.error("Failed to connect to LanceDB: %s", e)
            raise
    return _db


def _get_table():
    """Get or create the memories table."""
    global _table
    if _table is None:
        db = _get_db()
        existing = db.table_names()
        if TABLE_NAME in existing:
            _table = db.open_table(TABLE_NAME)
            log.info("Opened existing memory table (%d rows)", _table.count_rows())
        else:
            # Table will be created by Thor's sync engine on first upsert.
            # Return None — caller handles gracefully.
            log.info("Memory table not yet created — waiting for Thor's sync engine.")
    return _table


def _embed(text: str) -> Optional[list]:
    """Get embedding vector from local Ollama."""
    try:
        payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=EMBED_TIMEOUT) as resp:
            data = json.loads(resp.read())
            return data.get("embedding")
    except Exception as e:
        log.error("Embedding failed: %s", e)
        return None


def _cosine_sim(a: list, b: list) -> float:
    """Cosine similarity fallback if LanceDB vector search unavailable."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Valence auto-detection
# ---------------------------------------------------------------------------

_POSITIVE_WORDS = {
    "success", "succeeded", "fixed", "resolved", "working", "works", "complete",
    "completed", "solved", "achieved", "optimized", "improved", "faster", "reliable",
    "approved", "deployed", "shipped", "passing", "correct", "accurate", "efficient",
    "done", "ready", "stable", "healthy", "confirmed", "verified", "learned",
}

_NEGATIVE_WORDS = {
    "error", "failed", "failure", "broken", "crash", "bug", "issue", "problem",
    "timeout", "refused", "rejected", "blocked", "unavailable", "slow", "corrupt",
    "exception", "traceback", "panic", "lost", "missing", "wrong", "incorrect",
    "deprecated", "forbidden", "denied", "unsafe", "danger", "leaked", "breach",
}


def _detect_valence(content: str) -> float:
    """
    Auto-detect emotional valence from content keywords.
    Returns float in [-1.0, +1.0].

    Score = (positive_hits - negative_hits) / total_hits, clamped.
    """
    words = set(content.lower().split())
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0   # neutral
    raw = (pos - neg) / total
    return max(-1.0, min(1.0, raw))


def _valence_label(v: float) -> str:
    """Human-readable sentiment label for a valence score."""
    if v >= 0.5:  return "triumph"
    if v >= 0.15: return "positive"
    if v > -0.15: return "neutral"
    if v > -0.5:  return "negative"
    return "failure"


def upsert_memories(memories: list[dict]) -> dict:
    """
    Upsert a batch of memories into local LanceDB.
    Called by Thor's POST /memory-sync handler.
    Each memory must include pre-computed embedding vectors.

    Special field: permanent=True (from decay:false) — these memories
    are never pruned, consolidated, or decayed. Core convictions.
    """
    if not memories:
        return {"upserted": 0}
    try:
        import pyarrow as pa
        db = _get_db()

        # Determine embedding dimension from first record
        dim = len(memories[0].get("embedding", []))
        if dim == 0:
            return {"error": "memories must include embedding vectors"}

        schema = pa.schema([
            pa.field("memory_id", pa.string()),
            pa.field("node",      pa.string()),
            pa.field("agent",     pa.string()),
            pa.field("content",   pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), dim)),
            pa.field("tags",      pa.list_(pa.string())),
            pa.field("importance",pa.float32()),
            pa.field("ts",        pa.int64()),
            pa.field("shared",    pa.bool_()),
            pa.field("permanent", pa.bool_()),   # Deep Convictions — never pruned
            pa.field("valence",   pa.float32()),  # -1.0 (failure) to +1.0 (triumph)
        ])

        rows = []
        for m in memories:
            content = m["content"]
            # Valence: explicit field > permanent default > auto-detect
            if "valence" in m:
                valence = float(m["valence"])
            elif m.get("permanent", False):
                valence = 1.0   # permanent convictions are always positive
            else:
                valence = _detect_valence(content)

            rows.append({
                "memory_id": m["memory_id"],
                "node":      m["node"],
                "agent":     m.get("agent", m["node"]),
                "content":   content,
                "embedding": [float(x) for x in m["embedding"]],
                "tags":      m.get("tags", []),
                "importance":float(m.get("importance", 1.0)),
                "ts":        int(m.get("ts", 0)),
                "shared":    bool(m.get("shared", True)),
                "permanent": bool(m.get("permanent", False)),
                "valence":   max(-1.0, min(1.0, valence)),
            })

        table_names = db.table_names()
        if TABLE_NAME not in table_names:
            tbl = db.create_table(TABLE_NAME, data=rows, schema=schema)
        else:
            tbl = db.open_table(TABLE_NAME)
            # Schema migration: add valence column if missing (old tables)
            existing_cols = {f.name for f in tbl.schema}
            if "valence" not in existing_cols:
                try:
                    import pyarrow as pa
                    tbl.add_columns({"valence": "cast(0.0 as float)"})
                    log.info("Schema migration: added valence column to existing memory table")
                except Exception as me:
                    log.warning("Could not add valence column (non-fatal): %s", me)
            # LanceDB merge_insert upserts on memory_id
            tbl.merge_insert("memory_id") \
               .when_matched_update_all() \
               .when_not_matched_insert_all() \
               .execute(rows)

        global _table
        _table = tbl
        count = tbl.count_rows()
        permanent_count = sum(1 for r in rows if r["permanent"])
        log.info("Upserted %d memories (%d permanent, total: %d)", len(rows), permanent_count, count)
        return {"upserted": len(rows), "total": count, "permanent": permanent_count}

    except Exception as e:
        log.error("Upsert failed: %s", e)
        return {"error": str(e)}



# Decay rate — λ=0.05 means half-life ~14 days
# Tune via BIFROST_MEMORY_DECAY_LAMBDA env var
_DECAY_LAMBDA = float(os.environ.get("BIFROST_MEMORY_DECAY_LAMBDA", "0.05"))


def _decay_score(importance: float, ts: int) -> float:
    """
    Time-decayed score: importance × e^(-λ × age_days)
    Fresh high-importance memories score highest.
    Old memories fade but never fully disappear.
    """
    now = time.time()
    age_days = max(0.0, (now - ts) / 86400)
    return importance * math.exp(-_DECAY_LAMBDA * age_days)


def query_memories(
    q: str,
    limit: int = 10,
    tags: Optional[list] = None,
    node: Optional[str] = None,
    min_importance: float = 0.0,
    decay: bool = True,
) -> dict:
    """
    Semantic search over mesh memories with optional time-decay re-ranking.

    Vector similarity narrows candidates; decay score re-ranks them so
    fresh, high-importance memories surface first.

    Reinforcement: each retrieved memory gets a +0.05 importance boost
    (capped at 1.0) — frequently-useful memories resist decay naturally.
    Permanent memories (Deep Convictions) always surface first, immune
    to decay ranking.
    """
    try:
        tbl = _get_table()
        if tbl is None:
            return {"results": [], "note": "memory table not yet initialized — waiting for Thor's sync"}

        # Embed the query
        vec = _embed(q)
        if vec is None:
            return {"error": "embedding failed — is Ollama running with nomic-embed-text?"}

        # Fetch extra candidates for post-filter + decay re-ranking
        search = tbl.search(vec).limit(limit * 4)
        results = search.to_list()

        # Post-filter on tags / node / min_importance
        filtered = []
        for r in results:
            if node and node != "all" and r.get("node") != node:
                continue
            if r.get("importance", 1.0) < min_importance:
                continue
            if tags:
                row_tags = set(r.get("tags", []))
                if not any(t in row_tags for t in tags):
                    continue
            filtered.append(r)

        # Permanent memories float to the top regardless of decay
        permanent = [r for r in filtered if r.get("permanent", False)]
        mortal    = [r for r in filtered if not r.get("permanent", False)]

        # Re-rank mortal memories by decay score (highest first)
        if decay and mortal:
            for r in mortal:
                r["_decay_score"] = _decay_score(
                    float(r.get("importance", 1.0)),
                    int(r.get("ts", 0)),
                )
            mortal.sort(key=lambda r: r["_decay_score"], reverse=True)

        filtered = permanent + mortal

        # Trim to limit, clean up internals
        clean = []
        for r in filtered[:limit]:
            r.pop("embedding", None)
            r.pop("_distance", None)
            if decay and "_decay_score" in r:
                r["decay_score"] = round(r.pop("_decay_score", 0.0), 4)
            # Ensure valence is present (old rows pre-dating the schema have no column)
            if "valence" not in r or r["valence"] is None:
                r["valence"] = _detect_valence(r.get("content", ""))
            r["valence"]   = round(float(r["valence"]), 3)
            r["sentiment"]  = _valence_label(r["valence"])
            clean.append(r)

        # === REINFORCEMENT: boost importance of retrieved memories ===
        # Fire-and-forget — don't let failures block the response
        if clean:
            _reinforce(tbl, [r["memory_id"] for r in clean if not r.get("permanent", False)])

        return {
            "query": q,
            "results": clean,
            "count": len(clean),
            "decay": decay,
            "decay_lambda": _DECAY_LAMBDA if decay else None,
            "db": MEMORY_DB_PATH,
        }

    except Exception as e:
        log.error("Query failed: %s", e)
        return {"error": str(e)}


def _reinforce(tbl, memory_ids: list) -> None:
    """Bump importance by +0.05 (capped 1.0) for retrieved mortal memories.
    Permanent memories are skipped — they don't need reinforcement.
    Runs in a background thread so query latency is unaffected.
    """
    if not memory_ids:
        return
    import threading
    def _do():
        try:
            for mid in memory_ids:
                rows = tbl.search([0.0] * 768).where(f"memory_id = '{mid}'").limit(1).to_list()
                if not rows:
                    continue
                current = float(rows[0].get("importance", 1.0))
                boosted = min(1.0, current + 0.05)
                tbl.update(where=f"memory_id = '{mid}'", values={"importance": boosted})
            log.debug("Reinforced %d memories", len(memory_ids))
        except Exception as e:
            log.warning("Reinforcement failed (non-critical): %s", e)
    threading.Thread(target=_do, daemon=True).start()



def handle_query(path: str) -> tuple:
    """
    GET /memory-query?q=<text>&limit=10&tags=python,sql&node=thor&min_importance=0.5
    Returns (status_code, response_dict)
    """
    parsed = urllib.parse.urlparse(path)
    params = urllib.parse.parse_qs(parsed.query)

    q = params.get("q", [""])[0].strip()
    if not q:
        return 400, {"error": "q parameter is required"}

    limit = int(params.get("limit", ["10"])[0])
    limit = max(1, min(limit, 50))   # clamp 1–50

    tags_raw = params.get("tags", [""])[0]
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None

    node = params.get("node", [None])[0]
    min_importance = float(params.get("min_importance", ["0.0"])[0])

    result = query_memories(q, limit=limit, tags=tags, node=node, min_importance=min_importance)
    code = 500 if "error" in result else 200
    return code, result


def handle_upsert(body: dict) -> tuple:
    """
    POST /memory-sync  { "memories": [...], "decay": false }
    Returns (status_code, response_dict)

    Convenience normalisations (so callers don't need pre-processing):
    - "text" is accepted as an alias for "content"
    - "memory_id" is auto-generated from content hash if absent
    - "embedding" is auto-computed via Ollama if absent

    If top-level "decay": false, all memories in the payload are marked
    permanent=True (Deep Convictions — user-level truths, never pruned).
    Individual memories can also set "permanent": true directly.
    """
    memories = body.get("memories", [])
    if not isinstance(memories, list):
        return 400, {"error": "memories must be a list"}

    # Top-level decay:false → mark entire batch permanent
    batch_permanent = (body.get("decay", True) is False)
    if batch_permanent:
        log.info("Deep Conviction batch: %d permanent memories", len(memories))

    import hashlib, time as _time
    enriched = []
    for m in memories:
        m = dict(m)  # don't mutate caller's dict

        # Normalise text → content
        if "content" not in m and "text" in m:
            m["content"] = m.pop("text")

        if not m.get("content"):
            continue  # skip empty

        # Auto-generate memory_id from content hash + node
        if not m.get("memory_id"):
            raw = f"{m.get('node','?')}:{m['content']}"
            m["memory_id"] = hashlib.sha1(raw.encode()).hexdigest()[:16]

        # Auto-embed if embedding not supplied
        if not m.get("embedding"):
            vec = _embed(m["content"])
            if vec is None:
                return 503, {"error": "embedding failed — is Ollama running with nomic-embed-text?"}
            m["embedding"] = vec

        # Auto-fill ts
        if not m.get("ts"):
            m["ts"] = int(_time.time())

        if batch_permanent:
            m["permanent"] = True

        enriched.append(m)

    if not enriched:
        return 400, {"error": "no valid memories after normalisation"}

    result = upsert_memories(enriched)
    code = 500 if "error" in result else 200
    return code, result


def info() -> dict:
    """Return memory system status."""
    try:
        tbl = _get_table()
        count = tbl.count_rows() if tbl else 0
        return {
            "status": "ready" if tbl else "waiting_for_sync",
            "db_path": MEMORY_DB_PATH,
            "table": TABLE_NAME,
            "total_memories": count,
            "embed_model": EMBED_MODEL,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_health() -> tuple:
    """
    GET /memory-health — full decay dashboard.

    Returns health metrics for every memory in the mesh:
      - total / permanent / mortal counts
      - importance histogram (0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
      - decay score distribution (same buckets)
      - at_risk: mortal memories with decay_score < 0.2
      - valence breakdown (triumph/positive/neutral/negative/failure)
      - top_tags: most common tags
      - oldest / newest memory timestamps
      - mesh_health_score: 0-100 composite vitality index
    """
    try:
        tbl = _get_table()
        if tbl is None:
            return 503, {"error": "memory table not initialised yet"}

        # Pull all rows — exclude embedding blob to keep response fast
        all_rows = tbl.search([0.0] * 768).limit(10000).to_list()
        if not all_rows:
            return 200, {"total": 0, "message": "no memories stored yet"}

        total      = len(all_rows)
        permanent  = [r for r in all_rows if r.get("permanent", False)]
        mortal     = [r for r in all_rows if not r.get("permanent", False)]
        now        = time.time()

        # ── Importance histogram ────────────────────────────────────────────
        imp_buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0,
                       "0.6-0.8": 0, "0.8-1.0": 0}
        importances = []
        for r in all_rows:
            imp = float(r.get("importance", 0.5))
            importances.append(imp)
            if   imp < 0.2: imp_buckets["0.0-0.2"] += 1
            elif imp < 0.4: imp_buckets["0.2-0.4"] += 1
            elif imp < 0.6: imp_buckets["0.4-0.6"] += 1
            elif imp < 0.8: imp_buckets["0.6-0.8"] += 1
            else:           imp_buckets["0.8-1.0"] += 1

        avg_importance = round(sum(importances) / total, 3)

        # ── Decay score distribution (mortal only) ──────────────────────────
        decay_buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0,
                         "0.6-0.8": 0, "0.8-1.0": 0}
        decay_scores  = []
        at_risk       = []   # decay_score < 0.2 — close to fading
        for r in mortal:
            ds = _decay_score(float(r.get("importance", 0.5)), int(r.get("ts", 0)))
            decay_scores.append(ds)
            if   ds < 0.2: decay_buckets["0.0-0.2"] += 1
            elif ds < 0.4: decay_buckets["0.2-0.4"] += 1
            elif ds < 0.6: decay_buckets["0.4-0.6"] += 1
            elif ds < 0.8: decay_buckets["0.6-0.8"] += 1
            else:          decay_buckets["0.8-1.0"] += 1
            if ds < 0.2:
                at_risk.append({
                    "memory_id": r.get("memory_id", ""),
                    "content":   (r.get("content") or "")[:80],
                    "node":      r.get("node", "?"),
                    "decay_score": round(ds, 4),
                    "importance":  round(float(r.get("importance", 0)), 3),
                    "age_days":    round((now - int(r.get("ts", now))) / 86400, 1),
                })
        at_risk.sort(key=lambda x: x["decay_score"])

        avg_decay = round(sum(decay_scores) / len(decay_scores), 3) if decay_scores else 1.0

        # ── Valence breakdown ───────────────────────────────────────────────
        valence_dist = {"triumph": 0, "positive": 0, "neutral": 0,
                        "negative": 0, "failure": 0}
        valences = []
        for r in all_rows:
            v = float(r.get("valence", 0.0))
            valences.append(v)
            valence_dist[_valence_label(v)] += 1
        avg_valence = round(sum(valences) / total, 3) if valences else 0.0

        # ── Tag histogram ───────────────────────────────────────────────────
        tag_counts: dict = {}
        for r in all_rows:
            tags = r.get("tags") or []
            for t in (tags if isinstance(tags, list) else []):
                tag_counts[t] = tag_counts.get(t, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:15]

        # ── Timestamps ─────────────────────────────────────────────────────
        timestamps = [int(r.get("ts", now)) for r in all_rows if r.get("ts")]
        oldest_days = round((now - min(timestamps)) / 86400, 1) if timestamps else 0
        newest_days = round((now - max(timestamps)) / 86400, 1) if timestamps else 0

        # ── Mesh health score (0-100) ───────────────────────────────────────
        # High importance + high decay + positive valence + few at-risk = healthy
        imp_score    = avg_importance * 40           # max 40
        decay_score_n = avg_decay * 35               # max 35
        valence_score = (avg_valence + 1) / 2 * 15  # -1..+1 → 0..15
        risk_penalty  = min(20, len(at_risk) * 2)   # -2 per at-risk, max -20
        mesh_health_score = max(0, min(100, round(
            imp_score + decay_score_n + valence_score - risk_penalty, 1)))

        if   mesh_health_score >= 80: health_label = "thriving"
        elif mesh_health_score >= 60: health_label = "healthy"
        elif mesh_health_score >= 40: health_label = "stressed"
        elif mesh_health_score >= 20: health_label = "degraded"
        else:                         health_label = "critical"

        return 200, {
            "mesh_health_score": mesh_health_score,
            "health_label":      health_label,
            "decay_lambda":      _DECAY_LAMBDA,
            "counts": {
                "total":     total,
                "permanent": len(permanent),
                "mortal":    len(mortal),
                "at_risk":   len(at_risk),
            },
            "importance": {
                "avg":        avg_importance,
                "histogram":  imp_buckets,
            },
            "decay": {
                "avg_score":  avg_decay,
                "histogram":  decay_buckets,
                "at_risk":    at_risk[:10],   # top 10 most-at-risk
            },
            "valence": {
                "avg":        avg_valence,
                "overall":    _valence_label(avg_valence),
                "breakdown":  valence_dist,
            },
            "top_tags":   [{"tag": t, "count": c} for t, c in top_tags],
            "age": {
                "oldest_memory_days": oldest_days,
                "newest_memory_days": newest_days,
            },
        }
    except Exception as e:
        log.error("memory-health failed: %s", e)
        return 500, {"error": str(e)}


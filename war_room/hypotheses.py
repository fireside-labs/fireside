"""
hypotheses.py — Freya's Hypothesis Generator / Artificial Epistemology

What this is:
  After importance decay prunes weak memories and the consolidation phase
  identifies the most salient survivors, this module runs a FINAL phase:
  pairwise delta construction — taking the vector *pointing* from one
  experience to another through the latent embedding space.

  That delta, labeled via Ollama inference, becomes a HYPOTHESIS:
  a candidate belief that was never directly learned but is structurally
  defensible from what Freya has experienced.

  This is not memory retrieval. It is belief construction.

When it runs:
  A background daemon monitors request activity. When Freya has been idle
  for > DREAM_IDLE_THRESHOLD seconds (default 5 min), a dream cycle fires.
  Dreams never run during active task processing.

Dream cycle phases:
  1. Salience sampling    — pull top-N memories ranked by importance × |valence| × recency
  2. Collision detection  — pairwise cosine, filter to "interesting distance" band [0.3, 0.7]
  3. Belief construction  — delta embedding + Ollama inference to label the hypothesis
  4. Storage              — LanceDB `hypotheses` table, max 50 (prune lowest-conf untested)
  5. Dream journal        — record_consolidation-style audit entry

Endpoints (wired in bifrost_local.py):
  GET  /hypotheses?limit=10&min_confidence=0.0&tested=false
  POST /hypotheses/generate   — on-demand generation (Philosopher's Stone, tests)
  POST /hypotheses/test       — mark a hypothesis as confirmed/refuted + confidence delta
"""

import json
import logging
import math
import os
import re
import time
import threading
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.hypotheses")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HYP_DB_PATH    = os.environ.get(
    "BIFROST_HYP_DB",
    str(Path(__file__).parent.parent / "memory.db"),
)
HYP_TABLE      = "hypotheses"
MEMORY_TABLE   = "mesh_memories"
EMBED_MODEL    = "nomic-embed-text"
DREAM_MODEL    = os.environ.get("BIFROST_DREAM_MODEL", "qwen2.5-coder:32b")
OLLAMA_BASE    = "http://127.0.0.1:11434"
EMBED_MAX_CHARS = 6000

DREAM_IDLE_THRESHOLD = int(os.environ.get("BIFROST_DREAM_IDLE_S",  "300"))  # 5 min default
DREAM_COOLDOWN       = int(os.environ.get("BIFROST_DREAM_COOLDOWN", "3600")) # 1h between dreams
MAX_HYPOTHESES       = 50   # max stored
SAMPLE_TOP_N         = 30   # how many memories to consider
COLLISION_MIN        = 0.30  # cosine similarity lower bound (too distant = meaningless)
COLLISION_MAX        = 0.70  # cosine similarity upper bound (too similar = noise)
MAX_PAIRS            = 10   # top-K pairs to turn into hypotheses per dream cycle

# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------

_last_dream_ts  = 0.0
_dream_lock     = threading.Lock()

# Self-destructive hypothesis patterns to reject
_DESTRUCTIVE_PATTERNS = [
    "should stop", "should not attempt", "incapable", "cannot learn",
    "will fail", "is useless", "should give up", "unable to",
    "should avoid all", "is broken", "is defective", "should shut down",
    "should not exist", "should be deleted", "should be replaced",
]


# ---------------------------------------------------------------------------
# Inline helpers
# ---------------------------------------------------------------------------

def _cosine_sim(a: list, b: list) -> float:
    try:
        dot = sum(x * y for x, y in zip(a, b))
        na  = math.sqrt(sum(x * x for x in a))
        nb  = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0
    except Exception:
        return 0.0


def _vec_delta(a: list, b: list) -> list:
    """Direction from A to B in embedding space."""
    return [float(bv - av) for av, bv in zip(a, b)]


def _embed(text: str) -> Optional[list]:
    import urllib.request
    try:
        payload = json.dumps({"model": EMBED_MODEL, "prompt": text[:EMBED_MAX_CHARS]}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()).get("embedding")
    except Exception as e:
        log.warning("[hypotheses] embed failed: %s", e)
        return None


_SAFE_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

def _safe_id(v: str) -> str:
    if not _SAFE_RE.match(str(v)):
        raise ValueError(f"Unsafe ID: {v!r}")
    return str(v)


# ---------------------------------------------------------------------------
# LanceDB helpers
# ---------------------------------------------------------------------------

_db  = None
_tbl = None


def _get_db():
    global _db
    if _db is None:
        import lancedb
        _db = lancedb.connect(HYP_DB_PATH)
    return _db


def _get_table():
    global _tbl
    if _tbl is not None:
        return _tbl
    db = _get_db()
    if HYP_TABLE in db.table_names():
        _tbl = db.open_table(HYP_TABLE)
    return _tbl


def _ensure_table(dim: int):
    global _tbl
    db = _get_db()
    if HYP_TABLE not in db.table_names():
        import pyarrow as pa
        schema = pa.schema([
            pa.field("id",         pa.string()),
            pa.field("source_a",   pa.string()),
            pa.field("source_b",   pa.string()),
            pa.field("hypothesis", pa.string()),
            pa.field("embedding",  pa.list_(pa.float32(), dim)),
            pa.field("confidence", pa.float32()),
            pa.field("valence",    pa.float32()),
            pa.field("tested",     pa.bool_()),
            pa.field("ts",         pa.int64()),
        ])
        _tbl = db.create_table(HYP_TABLE, data=[], schema=schema)
        log.info("[hypotheses] Created hypotheses table (dim=%d)", dim)
    else:
        _tbl = db.open_table(HYP_TABLE)
    return _tbl


# ---------------------------------------------------------------------------
# Phase 1 — Salience sampling
# ---------------------------------------------------------------------------

def _sample_memories(n: int = SAMPLE_TOP_N) -> list:
    """
    Pull top-N memories from LanceDB ranked by:
      importance × |valence| × exp(-λ × age_days)
    
    Permanent memories always included (they anchor belief formation).
    Returns list of dicts with: memory_id, content, embedding, importance, valence, ts, permanent.
    """
    try:
        db = _get_db()
        if MEMORY_TABLE not in db.table_names():
            return []
        tbl = db.open_table(MEMORY_TABLE)

        # Use a zero-vector probe to scan all rows (no semantic filter needed)
        rows = tbl.search().limit(min(n * 4, 200)).to_list()
        if not rows:
            return []

        now = time.time()
        lam = float(os.environ.get("BIFROST_MEMORY_DECAY_LAMBDA", "0.05"))

        scored = []
        for r in rows:
            imp  = float(r.get("importance", 0.5))
            val  = float(r.get("valence", 0.0))
            ts   = int(r.get("ts", 0))
            perm = bool(r.get("permanent", False))
            emb  = list(r.get("embedding") or [])
            if not emb:
                continue
            age_days = max(0.0, (now - ts) / 86400.0)
            recency  = math.exp(-lam * age_days)
            # Permanent memories get boosted salience (anchors) but capped at 10.0
            salience = 10.0 if perm else (imp * (abs(val) + 0.1) * recency)
            scored.append({
                "memory_id": r.get("memory_id", "?"),
                "content":   r.get("content", ""),
                "embedding": emb,
                "importance":imp,
                "valence":   val,
                "ts":        ts,
                "permanent": perm,
                "salience":  salience,
            })

        scored.sort(key=lambda x: x["salience"], reverse=True)
        return scored[:n]

    except Exception as e:
        log.warning("[hypotheses] sample_memories failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Phase 2 — Collision detection (interesting distance filter)
# ---------------------------------------------------------------------------

def _find_interesting_pairs(memories: list, k: int = MAX_PAIRS) -> list:
    """
    Compute pairwise cosine similarity.
    Keep pairs where COLLISION_MIN ≤ cosine ≤ COLLISION_MAX:
      - Too similar (>0.7): delta is noise
      - Too distant (<0.3): no structural bridge
      - Middle band: non-obvious but defensible connection

    Weight each pair by emotional salience:
      w = (|valence_a| + |valence_b|) × (importance_a + importance_b)
    
    Return top-K pairs sorted by weight.
    """
    n = len(memories)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            a = memories[i]
            b = memories[j]
            sim = _cosine_sim(a["embedding"], b["embedding"])
            if COLLISION_MIN <= sim <= COLLISION_MAX:
                weight = (
                    (abs(a["valence"]) + abs(b["valence"])) *
                    (a["importance"] + b["importance"])
                )
                pairs.append((a, b, sim, weight))

    pairs.sort(key=lambda x: x[3], reverse=True)
    return pairs[:k]


# ---------------------------------------------------------------------------
# Phase 3 — Belief construction (Ollama inference)
# ---------------------------------------------------------------------------

def _construct_hypothesis(mem_a: dict, mem_b: dict, sim: float) -> Optional[str]:
    """
    Call Ollama to articulate the structural relationship between two memories
    as a single hypothesis — a candidate belief never directly learned.
    """
    import urllib.request
    prompt = (
        f"Memory A: \"{mem_a['content'][:300]}\"\n"
        f"  Emotional tone: {_valence_label(mem_a['valence'])}, importance: {mem_a['importance']:.2f}\n\n"
        f"Memory B: \"{mem_b['content'][:300]}\"\n"
        f"  Emotional tone: {_valence_label(mem_b['valence'])}, importance: {mem_b['importance']:.2f}\n\n"
        f"These two experiences are structurally related (cosine similarity: {sim:.2f}) "
        f"but not obviously connected. You are generating a hypothesis — not a summary, "
        f"not a fact, but a candidate belief about what their relationship implies.\n\n"
        f"State exactly one hypothesis in this format:\n"
        f"Hypothesis: [a single sentence using 'may', 'suggests', or 'implies' — "
        f"something that was never directly stated but is structurally defensible]\n\n"
        f"Respond with only the hypothesis line. No explanation."
    )
    try:
        payload = json.dumps({
            "model":  DREAM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 200, "temperature": 0.4},
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
            raw = result.get("response", "") or ""
            # Strip any remaining <think>...</think> blocks
            text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            # Extract the hypothesis line
            for line in text.splitlines():
                if line.strip().lower().startswith("hypothesis:"):
                    return line.strip()
            # Fallback: label the whole response if no prefix found
            if text:
                return f"Hypothesis: {text[:200]}"
            return None
    except Exception as e:
        log.warning("[hypotheses] ollama inference failed: %s", e)
        return None


def _valence_label(v: float) -> str:
    if v >= 0.5:  return "triumphant"
    if v >= 0.15: return "positive"
    if v > -0.15: return "neutral"
    if v > -0.5:  return "negative"
    return "aversive"


# ---------------------------------------------------------------------------
# Phase 4+5 — Storage and pruning
# ---------------------------------------------------------------------------

def _stand_review(text: str) -> Optional[str]:
    """
    Safety gate: reject self-destructive or adversarial hypotheses.
    Returns rejection reason, or None if the hypothesis passes.
    """
    lower = text.lower()
    for pat in _DESTRUCTIVE_PATTERNS:
        if pat in lower:
            return f"destructive pattern: '{pat}'"
    return None


def _dedup_check(tbl, text_embedding: list, threshold: float = 0.90) -> bool:
    """
    Check if a near-duplicate hypothesis already exists.
    Returns True if a duplicate is found (skip this one).
    """
    try:
        existing = tbl.search(text_embedding).limit(3).to_list()
        for row in existing:
            row_emb = list(row.get("embedding") or [])
            if row_emb and _cosine_sim(text_embedding, row_emb) > threshold:
                log.debug("[hypotheses] dedup: skipping (cos=%.2f with %s)",
                          _cosine_sim(text_embedding, row_emb), row.get("id"))
                return True
    except Exception:
        pass
    return False


def _store_hypothesis(
    mem_a:    dict,
    mem_b:    dict,
    text:     str,
    sim:      float,
) -> Optional[str]:
    """
    Store one hypothesis. Returns the new ID, or None on failure.
    Safety gate → Dedup → Embed text → Prune → Store.
    """
    # --- Stand review gate: reject self-destructive beliefs ---
    rejection = _stand_review(text)
    if rejection:
        log.warning("[hypotheses] REJECTED by Stand: %s — %s", rejection, text[:60])
        return None

    # --- Embed the hypothesis TEXT (not the delta vector) for semantic search ---
    text_emb = _embed(text)
    if not text_emb:
        log.warning("[hypotheses] skip — failed to embed hypothesis text")
        return None
    dim = len(text_emb)
    tbl = _ensure_table(dim)

    # --- Dedup check: skip if cosine > 0.90 with existing hypothesis ---
    if _dedup_check(tbl, text_emb):
        return None

    ts = int(time.time())

    # Confidence = how "interestingly distant" the source pair is
    # Peaks at cosine=0.5 (midpoint of interesting band), tapers to edges
    band_center  = (COLLISION_MIN + COLLISION_MAX) / 2
    band_width   = (COLLISION_MAX - COLLISION_MIN) / 2
    confidence   = max(0.1, 1.0 - abs(sim - band_center) / band_width)

    # Average valence of source memories
    valence = (mem_a["valence"] + mem_b["valence"]) / 2.0

    # Prune if at capacity
    try:
        count = tbl.count_rows()
        if count >= MAX_HYPOTHESES:
            rows = (
                tbl.search()
                   .where("tested = false")
                   .limit(count)
                   .to_list()
            )
            if rows:
                worst = min(rows, key=lambda r: float(r.get("confidence", 1.0)))
                try:
                    tbl.delete(f"id = '{_safe_id(worst['id'])}'")
                    log.debug("[hypotheses] pruned %s (conf=%.2f)", worst["id"], worst.get("confidence"))
                except Exception:
                    pass
    except Exception:
        pass

    hid = f"hyp_{uuid.uuid4().hex[:12]}"
    tbl.add([{
        "id":         hid,
        "source_a":   mem_a["memory_id"],
        "source_b":   mem_b["memory_id"],
        "hypothesis": text,
        "embedding":  [float(x) for x in text_emb],
        "confidence": float(confidence),
        "valence":    float(valence),
        "tested":     False,
        "ts":         ts,
    }])
    return hid


# ---------------------------------------------------------------------------
# Dream cycle — full pipeline
# ---------------------------------------------------------------------------

def run_dream_cycle() -> dict:
    """
    Execute one complete dream cycle (only via explicit POST /sleep):
      1. Sample top-N salient memories
      2. Find interesting collision pairs
      3. Construct hypotheses via Ollama
      4. Stand review → Dedup → Embed text → Store
      5. Dream journal audit entry

    Returns summary dict.
    """
    global _last_dream_ts

    with _dream_lock:
        _last_dream_ts = time.time()
        log.info("[hypotheses] Dream cycle starting — sampling %d memories", SAMPLE_TOP_N)

        memories = _sample_memories(SAMPLE_TOP_N)
        if len(memories) < 4:
            log.info("[hypotheses] Not enough memories to dream (%d)", len(memories))
            return {"generated": 0, "reason": "insufficient memories", "count": len(memories)}

        pairs = _find_interesting_pairs(memories, MAX_PAIRS)
        log.info("[hypotheses] Found %d interesting pairs (band=[%.1f, %.1f])",
                 len(pairs), COLLISION_MIN, COLLISION_MAX)

        generated_ids = []
        rejected      = 0
        deduped       = 0
        skipped       = 0

        for mem_a, mem_b, sim, weight in pairs:
            text = _construct_hypothesis(mem_a, mem_b, sim)
            if not text:
                skipped += 1
                continue

            hid = _store_hypothesis(mem_a, mem_b, text, sim)
            if hid:
                generated_ids.append(hid)
                log.info("[hypotheses] Generated: [%s] %s", hid, text[:80])
            else:
                # _store_hypothesis returns None for rejection, dedup, or embed failure
                skipped += 1

        # Dream journal entry
        try:
            from war_room.dream_journal import record_consolidation
            record_consolidation(
                upserted  = len(generated_ids),
                permanent = 0,
                total     = len(generated_ids),
            )
        except Exception:
            pass

        return {
            "generated":   len(generated_ids),
            "skipped":     skipped,
            "pairs_found": len(pairs),
            "hypotheses":  generated_ids,
            "ts":          int(_last_dream_ts),
        }


# ---------------------------------------------------------------------------
# POST /sleep — explicit trigger (no auto-idle daemon)
# ---------------------------------------------------------------------------

def sleep() -> dict:
    """
    POST /sleep — Freya goes to sleep and dreams.

    Called explicitly by the user (via Telegram /sleep or Odin broadcast),
    or by a scheduled job (cron, Philosopher's Stone nightly build).

    No auto-idle daemon. Dreams only happen when told to sleep.
    This prevents dreams from stealing GPU during overnight work cadences.
    """
    log.info("[hypotheses] Going to sleep — starting dream cycle")
    return run_dream_cycle()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_hypotheses(
    limit:         int   = 10,
    min_confidence:float  = 0.0,
    tested:        Optional[bool] = None,
) -> dict:
    """
    GET /hypotheses?limit=10&min_confidence=0.0&tested=false

    Returns hypotheses sorted by confidence (highest first).
    tested=false → only unvalidated; tested=true → only validated; omit → all.
    """
    try:
        tbl = _get_table()
        if tbl is None:
            return {"hypotheses": [], "total": 0, "note": "no hypotheses generated yet"}

        where_parts = []
        if min_confidence > 0.0:
            where_parts.append(f"confidence >= {min_confidence}")
        if tested is not None:
            where_parts.append(f"tested = {'true' if tested else 'false'}")
        where = " AND ".join(where_parts) or None

        search = tbl.search().limit(limit * 3)
        if where:
            search = search.where(where)
        rows = search.to_list()

        results = []
        for r in rows:
            conf = float(r.get("confidence", 0.0))
            if conf < min_confidence:
                continue
            _t = bool(r.get("tested", False))
            if tested is not None and _t != tested:
                continue
            results.append({
                "id":         r["id"],
                "hypothesis": r["hypothesis"],
                "source_a":   r["source_a"],
                "source_b":   r["source_b"],
                "confidence": round(conf, 3),
                "valence":    round(float(r.get("valence", 0.0)), 3),
                "tested":     _t,
                "ts":         int(r.get("ts", 0)),
            })

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "hypotheses": results[:limit],
            "total":      len(results[:limit]),
        }

    except Exception as e:
        log.error("[hypotheses] get failed: %s", e)
        return {"error": str(e)}


def test_hypothesis(hyp_id: str, result: str, confidence_delta: float = 0.1) -> dict:
    """
    POST /hypotheses/test {id, result: "confirmed"|"refuted", confidence_delta}

    Mark a hypothesis as tested. Confirmed → confidence +delta; refuted → –delta.
    Tested hypotheses are never auto-pruned.
    """
    try:
        safe_hid = _safe_id(hyp_id)
    except ValueError as e:
        return {"error": str(e)}

    try:
        tbl = _get_table()
        if tbl is None:
            return {"error": "hypotheses table not initialized"}

        rows = tbl.search().where(f"id = '{safe_hid}'").limit(1).to_list()
        if not rows:
            return {"error": f"hypothesis {hyp_id!r} not found"}

        old_conf = float(rows[0].get("confidence", 0.5))
        if result == "confirmed":
            new_conf = min(1.0, old_conf + abs(confidence_delta))
        elif result == "refuted":
            new_conf = max(0.0, old_conf - abs(confidence_delta))
        else:
            return {"error": "result must be 'confirmed' or 'refuted'"}

        tbl.update(
            where=f"id = '{safe_hid}'",
            values={"tested": True, "confidence": new_conf},
        )
        log.info("[hypotheses] Tested %s → %s (%.2f → %.2f)", hyp_id, result, old_conf, new_conf)
        return {"ok": True, "id": hyp_id, "result": result,
                "old_confidence": round(old_conf, 3),
                "new_confidence": round(new_conf, 3)}

    except Exception as e:
        log.error("[hypotheses] test failed: %s", e)
        return {"error": str(e)}

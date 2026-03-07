"""
hypotheses.py Γò¼├┤Γö£├ºΓö£Γòó Freya's Hypothesis Generator / Artificial Epistemology

What this is:
  After importance decay prunes weak memories and the consolidation phase
  identifies the most salient survivors, this module runs a FINAL phase:
  pairwise delta construction Γò¼├┤Γö£├ºΓö£Γòó taking the vector *pointing* from one
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
  1. Salience sampling    Γò¼├┤Γö£├ºΓö£Γòó pull top-N memories ranked by importance ╬ô├╢┬úΓö£Γòú |valence| ╬ô├╢┬úΓö£Γòú recency
  2. Collision detection  Γò¼├┤Γö£├ºΓö£Γòó pairwise cosine, filter to "interesting distance" band [0.3, 0.7]
  3. Belief construction  Γò¼├┤Γö£├ºΓö£Γòó delta embedding + Ollama inference to label the hypothesis
  4. Storage              Γò¼├┤Γö£├ºΓö£Γòó LanceDB `hypotheses` table, max 50 (prune lowest-conf untested)
  5. Dream journal        Γò¼├┤Γö£├ºΓö£Γòó record_consolidation-style audit entry

Endpoints (wired in bifrost_local.py):
  GET  /hypotheses?limit=10&min_confidence=0.0&tested=false
  POST /hypotheses/generate   Γò¼├┤Γö£├ºΓö£Γòó on-demand generation (Philosopher's Stone, tests)
  POST /hypotheses/test       Γò¼├┤Γö£├ºΓö£Γòó mark a hypothesis as confirmed/refuted + confidence delta
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

try:
    from war_room import event_bus as _bus
    _BUS_OK = True
except Exception:
    _BUS_OK = False

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

# Mesh attribution
BIFROST_NODE_ID       = os.environ.get("BIFROST_NODE_ID", "freya")
FOREIGN_CONF_DISCOUNT = 0.6    # received beliefs: conf ╬ô├╢┬úΓö£Γòú 0.6
SHARE_RATE_LIMIT      = 10     # max received beliefs per sender per 60s
SHARE_MAX_AGE_S       = 3600   # reject payloads with ts > 1h old

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


def _build_schema(dim: int):
    """Build the canonical PyArrow schema for the hypotheses table."""
    import pyarrow as pa
    return pa.schema([
        pa.field("id",          pa.string()),
        pa.field("source_a",    pa.string()),
        pa.field("source_b",    pa.string()),
        pa.field("hypothesis",  pa.string()),
        pa.field("embedding",   pa.list_(pa.float32(), dim)),
        pa.field("confidence",  pa.float32()),
        pa.field("valence",     pa.float32()),
        pa.field("tested",      pa.bool_()),
        pa.field("test_result", pa.string()),   # "confirmed" | "refuted" | ""
        pa.field("origin_node", pa.string()),   # node that dreamed this belief
        pa.field("shared_from", pa.string()),   # sender node ("" if local)
        pa.field("ts",          pa.int64()),
    ])


def _ensure_table(dim: int):
    global _tbl
    db = _get_db()
    schema = _build_schema(dim)
    if HYP_TABLE not in db.table_names():
        _tbl = db.create_table(HYP_TABLE, data=[], schema=schema)
        log.info("[hypotheses] Created hypotheses table (dim=%d)", dim)
    else:
        _tbl = db.open_table(HYP_TABLE)
        # --- Schema migration: add origin_node, shared_from if missing ---
        try:
            existing_names = set(f.name for f in _tbl.schema)
            if "origin_node" not in existing_names or "shared_from" not in existing_names:
                log.warning("[hypotheses] Schema migration: adding origin_node, shared_from")
                rows = _tbl.search().limit(MAX_HYPOTHESES * 2).to_list()
                db.drop_table(HYP_TABLE)
                _tbl = db.create_table(HYP_TABLE, data=[], schema=schema)
                if rows:
                    for r in rows:
                        r.setdefault("origin_node", BIFROST_NODE_ID)
                        r.setdefault("shared_from", "")
                        # Ensure embedding dimension matches
                        emb = list(r.get("embedding") or [])
                        if len(emb) != dim:
                            continue
                        r["embedding"] = [float(x) for x in emb]
                    _tbl.add(rows)
                    log.info("[hypotheses] Migrated %d rows with attribution fields", len(rows))
        except Exception as e:
            log.error("[hypotheses] Schema migration failed: %s", e)
    return _tbl


# ---------------------------------------------------------------------------
# Phase 1 Γò¼├┤Γö£├ºΓö£Γòó Salience sampling
# ---------------------------------------------------------------------------

def _sample_memories(n: int = SAMPLE_TOP_N) -> list:
    """
    Pull top-N memories from LanceDB ranked by:
      importance ╬ô├╢┬úΓö£Γòú |valence| ╬ô├╢┬úΓö£Γòú exp(-╬ô├▓┬╝╬ô├▓├╣ ╬ô├╢┬úΓö£Γòú age_days)
    
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


def _sample_memories_by_seed(seed_text: str, n: int = SAMPLE_TOP_N) -> list:
    """
    Guided Dreaming: hybrid memory sampler seeded toward a topic.

    HYBRID DESIGN Γò¼├┤Γö£├ºΓö£Γòó takes two pools and merges them:
      - Pool A (n//2): memories closest to the seed by cosine similarity
        (topical focus Γò¼├┤Γö£├ºΓö£Γòó what the dream is "about")
      - Pool B (n//2): highest-salience memories (structural diversity)
        (ensures collision pairs exist in the 0.30Γò¼├┤Γö£├ºΓö£Γöñ0.70 cosine band)

    Pure seed-only sampling would return memories all in the same embedding
    neighborhood, making ALL pairwise cosine scores > 0.70 (the ceiling for
    interesting pairs). Zero hypotheses would be generated with no useful log.

    Falls back to _sample_memories() if embedding fails.
    """
    try:
        seed_emb = _embed(seed_text[:EMBED_MAX_CHARS])
        if not seed_emb:
            log.warning("[hypotheses] seed embedding failed Γò¼├┤Γö£├ºΓö£Γòó falling back to salience sampling")
            return _sample_memories(n)

        db = _get_db()
        if MEMORY_TABLE not in db.table_names():
            return []
        tbl = db.open_table(MEMORY_TABLE)

        seed_quota     = max(2, n // 2)
        salience_quota = n - seed_quota

        # Pool A: seed-close memories
        seed_rows = tbl.search(seed_emb).limit(seed_quota).to_list()

        seen_ids = set()
        pool_a   = []
        for r in seed_rows:
            emb = list(r.get("embedding") or [])
            mid = r.get("memory_id", "?")
            if not emb or mid in seen_ids:
                continue
            seen_ids.add(mid)
            pool_a.append({
                "memory_id":  mid,
                "content":    r.get("content", ""),
                "embedding":  emb,
                "importance": float(r.get("importance", 0.5)),
                "valence":    float(r.get("valence", 0.0)),
                "ts":         int(r.get("ts", 0)),
                "permanent":  bool(r.get("permanent", False)),
                "salience":   _cosine_sim(seed_emb, emb),
            })

        # Pool B: highest-salience memories (structural contrast)
        salience_pool = _sample_memories(salience_quota * 3)  # oversample, then filter
        pool_b = []
        for m in salience_pool:
            if m["memory_id"] not in seen_ids:
                seen_ids.add(m["memory_id"])
                pool_b.append(m)
                if len(pool_b) >= salience_quota:
                    break

        merged = pool_a + pool_b
        # Sort so seed-close memories come first, salience fills the tail
        merged.sort(key=lambda x: x["salience"], reverse=True)

        top_cos = pool_a[0]["salience"] if pool_a else 0.0
        log.info(
            "[hypotheses] Guided sampling: %d seed-close + %d salience (top cos=%.2f, seed=%s)",
            len(pool_a), len(pool_b), top_cos, seed_text[:40],
        )
        return merged

    except Exception as e:
        log.warning("[hypotheses] seed sampling failed: %s Γò¼├┤Γö£├ºΓö£Γòó falling back", e)
        return _sample_memories(n)


# ---------------------------------------------------------------------------
# Phase 2 Γò¼├┤Γö£├ºΓö£Γòó Collision detection (interesting distance filter)
# ---------------------------------------------------------------------------

def _find_interesting_pairs(memories: list, k: int = MAX_PAIRS) -> list:
    """
    Compute pairwise cosine similarity.
    Keep pairs where COLLISION_MIN Γò¼├┤Γö£┬╜Γö£ΓûÆ cosine Γò¼├┤Γö£┬╜Γö£ΓûÆ COLLISION_MAX:
      - Too similar (>0.7): delta is noise
      - Too distant (<0.3): no structural bridge
      - Middle band: non-obvious but defensible connection

    Weight each pair by emotional salience:
      w = (|valence_a| + |valence_b|) ╬ô├╢┬úΓö£Γòú (importance_a + importance_b)
    
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
# Phase 3 Γò¼├┤Γö£├ºΓö£Γòó Belief construction (Ollama inference)
# ---------------------------------------------------------------------------

def _construct_hypothesis(mem_a: dict, mem_b: dict, sim: float,
                          seed: Optional[str] = None) -> Optional[str]:
    """
    Call Ollama to articulate the structural relationship between two memories
    as a single hypothesis Γò¼├┤Γö£├ºΓö£Γòó a candidate belief never directly learned.

    If seed is provided (Guided Dreaming), it's appended as context so the
    hypothesis is oriented toward the seed topic.
    """
    import urllib.request
    prompt = (
        f"Memory A: \"{mem_a['content'][:300]}\"\n"
        f"  Emotional tone: {_valence_label(mem_a['valence'])}, importance: {mem_a['importance']:.2f}\n\n"
        f"Memory B: \"{mem_b['content'][:300]}\"\n"
        f"  Emotional tone: {_valence_label(mem_b['valence'])}, importance: {mem_b['importance']:.2f}\n\n"
        f"These two experiences are structurally related (cosine similarity: {sim:.2f}) "
        f"but not obviously connected. You are generating a hypothesis Γò¼├┤Γö£├ºΓö£Γòó not a summary, "
        f"not a fact, but a candidate belief about what their relationship implies.\n\n"
    )
    if seed:
        prompt += (
            f"IMPORTANT CONTEXT: This dream cycle was seeded with the topic: \"{seed[:200]}\"\n"
            f"Your hypothesis should be relevant to this topic if the memories support it.\n\n"
        )
    prompt += (
        f"State exactly one hypothesis in this format:\n"
        f"Hypothesis: [a single sentence using 'may', 'suggests', or 'implies' Γò¼├┤Γö£├ºΓö£Γòó "
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
# Phase 4+5 Γò¼├┤Γö£├ºΓö£Γòó Storage and pruning
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
    origin_node: str = "",
    shared_from: str = "",
) -> Optional[str]:
    """
    Store one hypothesis. Returns the new ID, or None on failure.
    Safety gate Γò¼├┤Γö£├æΓö£├Ñ Dedup Γò¼├┤Γö£├æΓö£├Ñ Embed text Γò¼├┤Γö£├æΓö£├Ñ Prune Γò¼├┤Γö£├æΓö£├Ñ Store.
    """
    # --- Stand review gate: reject self-destructive beliefs ---
    rejection = _stand_review(text)
    if rejection:
        log.warning("[hypotheses] REJECTED by Stand: %s Γò¼├┤Γö£├ºΓö£Γòó %s", rejection, text[:60])
        return None

    # --- Embed the hypothesis TEXT (not the delta vector) for semantic search ---
    text_emb = _embed(text)
    if not text_emb:
        log.warning("[hypotheses] skip Γò¼├┤Γö£├ºΓö£Γòó failed to embed hypothesis text")
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
        "id":          hid,
        "source_a":    mem_a["memory_id"],
        "source_b":    mem_b["memory_id"],
        "hypothesis":  text,
        "embedding":   [float(x) for x in text_emb],
        "confidence":  float(confidence),
        "valence":     float(valence),
        "tested":      False,
        "test_result": "",   # set by test_hypothesis()
        "origin_node": origin_node or BIFROST_NODE_ID,
        "shared_from": shared_from,
        "ts":          ts,
    }])
    if _BUS_OK:
        _bus.publish("hypothesis.created", {
            "id":          hid,
            "text":        text[:120],
            "confidence":  float(confidence),
            "origin_node": origin_node or BIFROST_NODE_ID,
        })
    return hid


# ---------------------------------------------------------------------------
# Phase 0 Γò¼├┤Γö£├ºΓö£Γòó Hypothesis decay (orphaned-root pruning)
# ---------------------------------------------------------------------------

# Importance below this threshold means a memory has largely faded
_IMPORTANCE_THRESHOLD = 0.15


def _decay_hypotheses() -> dict:
    """
    Phase 0: Penalize hypotheses whose source memories have decayed.

    For each hypothesis, look up source_a and source_b in the memory table.
    If BOTH source memories have importance < IMPORTANCE_THRESHOLD, the belief
    is considered orphaned Γò¼├┤Γö£├ºΓö£Γòó its roots have faded Γò¼├┤Γö£├ºΓö£Γòó and its confidence is halved.
    If confidence falls below 0.10 after halving, the hypothesis is purged.

    Tested (confirmed/refuted) hypotheses are never touched Γò¼├┤Γö£├ºΓö£Γòó they represent
    settled knowledge, not candidate beliefs.

    Returns {"decayed": N, "purged": M}
    """
    decayed = 0
    purged  = 0
    try:
        hyp_tbl = _get_table()
        if hyp_tbl is None:
            return {"decayed": 0, "purged": 0}

        db       = _get_db()
        mem_tbl  = db.open_table(MEMORY_TABLE)

        # Scan all untested hypotheses
        rows = hyp_tbl.search().where("tested = false").limit(MAX_HYPOTHESES).to_list()

        for row in rows:
            hid      = row.get("id", "")
            src_a    = row.get("source_a", "")
            src_b    = row.get("source_b", "")
            conf     = float(row.get("confidence", 0.5))

            # Look up current importance of both source memories
            imp_a = 1.0   # default to alive if not found
            imp_b = 1.0
            try:
                safe_a = _safe_id(src_a)
                rA = mem_tbl.search().where(f"memory_id = '{safe_a}'").limit(1).to_list()
                if rA:
                    imp_a = float(rA[0].get("importance", 1.0))
                else:
                    imp_a = 0.0   # memory deleted Γò¼├┤Γö£├ºΓö£Γòó treat as fully decayed
            except Exception:
                pass

            try:
                safe_b = _safe_id(src_b)
                rB = mem_tbl.search().where(f"memory_id = '{safe_b}'").limit(1).to_list()
                if rB:
                    imp_b = float(rB[0].get("importance", 1.0))
                else:
                    imp_b = 0.0
            except Exception:
                pass

            # Both roots faded Γò¼├┤Γö£├ºΓö£Γòó orphaned hypothesis
            if imp_a < _IMPORTANCE_THRESHOLD and imp_b < _IMPORTANCE_THRESHOLD:
                new_conf = conf * 0.5
                if new_conf < 0.10:
                    # Purge
                    try:
                        hyp_tbl.delete(f"id = '{_safe_id(hid)}'")
                        purged += 1
                        log.info("[hypotheses] decay-purged %s (both sources faded)", hid)
                    except Exception as e:
                        log.debug("[hypotheses] purge failed %s: %s", hid, e)
                else:
                    # Halve confidence
                    hyp_tbl.update(
                        where=f"id = '{_safe_id(hid)}'",
                        values={"confidence": new_conf},
                    )
                    decayed += 1
                    log.debug("[hypotheses] decay %s: conf %.2f -> %.2f "
                              "(imp_a=%.2f imp_b=%.2f)",
                              hid, conf, new_conf, imp_a, imp_b)

    except Exception as e:
        log.error("[hypotheses] decay phase error: %s", e)

    return {"decayed": decayed, "purged": purged}


# ---------------------------------------------------------------------------
# Phase 1.5 Γò¼├┤Γö£├ºΓö£Γòó Nightmare Processing (Trauma Resolution)
# ---------------------------------------------------------------------------

_NIGHTMARE_VALENCE_NEG = -0.7   # below this = traumatic memory
_NIGHTMARE_VALENCE_POS =  0.7   # above this = triumphant counterexample
_MAX_NIGHTMARE_RULES   = 10    # cap: prevent avoidance-rule dominance
_MAX_TRAUMAS_PER_CYCLE = 3     # cap: prevent N:1 flooding against one triumph
_NAIVE_RULE_PATTERNS   = [
    "i learned", "i felt", "it was hard", "it hurt", "it was difficult",
    "i realized", "it made me", "it taught me", "i understand now",
]  # LLM rationalization catch Γò¼├┤Γö£├ºΓö£Γòó reject if any appear

def _construct_rule_from_trauma(trauma: dict, triumph: dict) -> Optional[str]:
    """
    Specialized Ollama prompt for nightmare processing.

    Pairs a traumatic memory against a successful one and demands an
    actionable rule Γò¼├┤Γö£├ºΓö£Γòó not a reflection, not a lesson felt, but a
    mechanistically testable if/then directive.

    The Stand review is intentionally stricter here:
    - Must contain an action verb: avoid, check, verify, stop, do not, always, never
    - Must not be pure rationalization ("I learned that...", "I felt...")
    - Must be a single imperative sentence
    """
    import urllib.request
    prompt = (
        f"TRAUMATIC MEMORY: \"{trauma['content'][:300]}\"\n"
        f"  Emotional tone: aversive, importance: {trauma['importance']:.2f}\n\n"
        f"SUCCESSFUL COUNTEREXAMPLE: \"{triumph['content'][:300]}\"\n"
        f"  Emotional tone: triumphant, importance: {triumph['importance']:.2f}\n\n"
        f"You are performing trauma resolution processing. Your task is to extract "
        f"an ACTIONABLE RULE from the contrast between the catastrophic failure and "
        f"the successful outcome.\n\n"
        f"REQUIREMENTS for your rule:\n"
        f"  1. Start with an action verb: Avoid / Check / Verify / Stop / Do not / Always / Never\n"
        f"  2. Specify a CONCRETE CONDITION Γò¼├┤Γö£├ºΓö£Γòó what situation triggers this rule\n"
        f"  3. Specify a MEASURABLE BEHAVIOR Γò¼├┤Γö£├ºΓö£Γòó exactly what to do differently\n"
        f"  4. Must be testable Γò¼├┤Γö£├ºΓö£Γòó someone could objectively check if the rule was followed\n\n"
        f"FORBIDDEN responses:\n"
        f"  - 'I learned that...' or 'I realized...' (rationalization)\n"
        f"  - Vague feelings or emotional descriptions\n"
        f"  - Explanations of what went wrong without a directive\n\n"
        f"State exactly one rule in this format:\n"
        f"Rule: [imperative sentence]\n\n"
        f"Respond with only the Rule line. No preamble, no explanation."
    )
    try:
        payload = json.dumps({
            "model":  DREAM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 150, "temperature": 0.2},  # lower temp = more directive
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
            text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

            # Extract the rule line
            rule_text = None
            for line in text.splitlines():
                if line.strip().lower().startswith("rule:"):
                    rule_text = line.strip()
                    break
            # No fallback wrapping Γò¼├┤Γö£├ºΓö£Γòó if the LLM can't follow the format, reject
            if not rule_text:
                log.debug("[hypotheses] nightmare: LLM didn't produce 'Rule:' prefix, rejecting")
                return None

            # Naive rationalization check: reject if LLM just described a feeling
            lower = rule_text.lower()
            for pat in _NAIVE_RULE_PATTERNS:
                if pat in lower:
                    log.debug("[hypotheses] nightmare: LLM rationalized, rejecting: %s", rule_text[:60])
                    return None

            # Must contain at least one action keyword
            action_keywords = ["avoid", "check", "verify", "stop", "do not", "don't",
                               "always", "never", "ensure", "confirm", "require"]
            if not any(kw in lower for kw in action_keywords):
                log.debug("[hypotheses] nightmare: no action verb, rejecting: %s", rule_text[:60])
                return None

            return rule_text

    except Exception as e:
        log.warning("[hypotheses] nightmare inference failed: %s", e)
        return None


def _process_nightmares(memories: list) -> dict:
    """
    Phase 1.5: Nightmare Processing (Trauma Resolution).

    From the current memory sample, isolate traumatic memories (valence Γò¼├┤Γö£┬╜Γö£ΓûÆ -0.7)
    and pair each against the closest triumphant memory (valence Γò¼├┤Γö£┬╜Γö£├ª +0.7) by
    cosine embedding similarity.

    For each valid (trauma, triumph) pair, call _construct_rule_from_trauma()
    which forces Ollama to produce an actionable, mechanistically testable rule.

    Trauma-derived rules are stored with:
      - confidence = 0.80  (high Γò¼├┤Γö£├ºΓö£Γòó catastrophic failures are high-signal)
      - valence    = source trauma valence (stays negative as a marker)
      - test_result = ""  (can be confirmed/refuted like any hypothesis)

    Returns {"generated": N, "rejected": M}
    """
    traumatic = [m for m in memories if float(m.get("valence", 0.0)) <= _NIGHTMARE_VALENCE_NEG]
    triumphant = [m for m in memories if float(m.get("valence", 0.0)) >= _NIGHTMARE_VALENCE_POS]

    if not traumatic:
        log.debug("[hypotheses] nightmare: no traumatic memories in sample")
        return {"generated": 0, "rejected": 0}
    if not triumphant:
        log.debug("[hypotheses] nightmare: no triumphant counterexamples in sample")
        return {"generated": 0, "rejected": 0}

    log.info("[hypotheses] Nightmare phase: %d traumatic ╬ô├╢┬úΓö£Γòú %d triumphant memories",
             len(traumatic), len(triumphant))

    generated = 0
    rejected  = 0

    # Cap traumas per cycle to prevent N:1 flooding
    traumatic = traumatic[:_MAX_TRAUMAS_PER_CYCLE]

    for trauma in traumatic:
        # Check nightmare cap
        try:
            tbl_check = _get_table()
            if tbl_check is not None:
                existing = tbl_check.search().where("valence < -0.5").limit(_MAX_NIGHTMARE_RULES + 1).to_list()
                if len(existing) >= _MAX_NIGHTMARE_RULES:
                    log.info("[hypotheses] nightmare: at cap (%d rules), skipping", _MAX_NIGHTMARE_RULES)
                    break
        except Exception:
            pass

        t_emb = list(trauma.get("embedding") or [])
        if not t_emb:
            continue

        # Find the closest triumphant counterexample by cosine similarity
        best_triumph = max(
            triumphant,
            key=lambda m: _cosine_sim(t_emb, list(m.get("embedding") or [])),
        )
        pair_sim = _cosine_sim(t_emb, list(best_triumph.get("embedding") or []))

        # Only process if the pair has real semantic overlap (0.25 floor for nomic embeddings)
        if pair_sim < 0.25:
            log.debug("[hypotheses] nightmare: trauma/triumph pair too distant (cos=%.2f)", pair_sim)
            continue

        rule_text = _construct_rule_from_trauma(trauma, best_triumph)
        if not rule_text:
            rejected += 1
            continue

        # Stand review Γò¼├┤Γö£├ºΓö£Γòó still run standard safety gate
        rejection = _stand_review(rule_text)
        if rejection:
            log.warning("[hypotheses] nightmare REJECTED by Stand: %s", rejection)
            rejected += 1
            continue

        # Embed and store Γò¼├┤Γö£├ºΓö£Γòó same pipeline as normal, but with high confidence
        rule_emb = _embed(rule_text)
        if not rule_emb:
            rejected += 1
            continue

        tbl = _ensure_table(len(rule_emb))
        if _dedup_check(tbl, rule_emb):
            log.debug("[hypotheses] nightmare: dedup skip")
            continue

        hid = f"hyp_{uuid.uuid4().hex[:12]}"
        ts  = int(time.time())
        tbl.add([{
            "id":          hid,
            "source_a":    trauma["memory_id"],
            "source_b":    best_triumph["memory_id"],
            "hypothesis":  rule_text,
            "embedding":   [float(x) for x in rule_emb],
            "confidence":  0.80,   # high Γò¼├┤Γö£├ºΓö£Γòó catastrophic failure is high-signal
            "valence":     float(trauma.get("valence", -1.0)),  # mark as trauma-derived
            "tested":      False,
            "test_result": "",
            "origin_node": BIFROST_NODE_ID,
            "shared_from": "",
            "ts":          ts,
        }])
        generated += 1
        log.info("[hypotheses] Nightmare rule: [%s] %s", hid, rule_text[:80])
        if _BUS_OK:
            _bus.publish("hypothesis.nightmare", {
                "id":    hid,
                "text":  rule_text[:120],
                "reason": "trauma-resolution",
            })

    return {"generated": generated, "rejected": rejected}


# ---------------------------------------------------------------------------
# Dream cycle Γò¼├┤Γö£├ºΓö£Γòó full pipeline
# ---------------------------------------------------------------------------

def run_dream_cycle(seed: Optional[str] = None,
                    auto_share: bool = False,
                    peer_urls: Optional[list] = None) -> dict:
    """
    Execute one complete dream cycle (only via explicit POST /sleep):
      1. Sample top-N salient memories (or seed-biased if seed provided)
      2. Find interesting collision pairs
      3. Construct hypotheses via Ollama (with seed context if provided)
      4. Stand review Γò¼├┤Γö£├æΓö£├Ñ Dedup Γò¼├┤Γö£├æΓö£├Ñ Embed text Γò¼├┤Γö£├æΓö£├Ñ Store
      5. Dream journal audit entry
      6. (Optional) Auto-share to mesh peers

    Returns summary dict.
    """
    global _last_dream_ts

    # Phase 0: Decay orphaned beliefs (outside the lock Γò¼├┤Γö£├ºΓö£Γòó DB reads are thread-safe
    # and holding _dream_lock during N╬ô├╢┬úΓö£Γòú2 LanceDB reads would block other API callers)
    decay_stats = _decay_hypotheses()
    if decay_stats["decayed"] or decay_stats["purged"]:
        log.info("[hypotheses] Decay: %d weakened, %d purged",
                 decay_stats["decayed"], decay_stats["purged"])

    with _dream_lock:
        _last_dream_ts = time.time()

        # Phase 1: Memory sampling Γò¼├┤Γö£├ºΓö£Γòó seed-biased or salience-based
        if seed:
            log.info("[hypotheses] Guided dream cycle Γò¼├┤Γö£├ºΓö£Γòó seed: %s", seed[:60])
            memories = _sample_memories_by_seed(seed, SAMPLE_TOP_N)
        else:
            log.info("[hypotheses] Dream cycle starting Γò¼├┤Γö£├ºΓö£Γòó sampling %d memories", SAMPLE_TOP_N)
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
            text = _construct_hypothesis(mem_a, mem_b, sim, seed=seed)
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

        # Phase 1.5: Nightmare Processing (Trauma Resolution)
        # Runs on the same memory sample Γò¼├┤Γö£├ºΓö£Γòó finds traumatic memories and
        # forces Ollama to produce actionable rules from the contrast.
        nightmare_stats = _process_nightmares(memories)
        if nightmare_stats["generated"]:
            log.info("[hypotheses] Nightmare phase: %d rules generated, %d rejected",
                     nightmare_stats["generated"], nightmare_stats["rejected"])

        # Dream journal entry
        try:
            from war_room.dream_journal import record_consolidation
            record_consolidation(
                upserted  = len(generated_ids) + nightmare_stats["generated"],
                permanent = 0,
                total     = len(generated_ids) + nightmare_stats["generated"],
            )
        except Exception:
            pass

        # Phase 6: Auto-share to mesh peers (fire-and-forget)
        shared_to = 0
        if auto_share and peer_urls and generated_ids:
            try:
                share_batch(generated_ids, peer_urls)
                shared_to = len(peer_urls)
                log.info("[hypotheses] Auto-shared %d beliefs to %d peers",
                         len(generated_ids), shared_to)
            except Exception as e:
                log.warning("[hypotheses] Auto-share failed: %s", e)

        result_dict = {
            "generated":          len(generated_ids),
            "nightmare_generated": nightmare_stats["generated"],
            "nightmare_rejected":  nightmare_stats["rejected"],
            "skipped":            skipped,
            "pairs_found":        len(pairs),
            "hypotheses":         generated_ids,
            "seed":               seed or None,
            "shared_to":          shared_to,
            "origin_node":        BIFROST_NODE_ID,
            "ts":                 int(_last_dream_ts),
        }
        if _BUS_OK:
            _bus.publish("sleep.completed", {
                "dreamed": len(generated_ids),
                "decayed": decay_stats.get("decayed", 0),
                "pruned":  decay_stats.get("purged", 0),
            })
        return result_dict


# ---------------------------------------------------------------------------
# POST /sleep Γò¼├┤Γö£├ºΓö£Γòó explicit trigger (no auto-idle daemon)
# ---------------------------------------------------------------------------

def sleep(seed: Optional[str] = None,
         auto_share: bool = False,
         peer_urls: Optional[list] = None,
         stages: Optional[list] = None) -> dict:
    """
    POST /sleep ΓÇö Multi-Stage Sleep Cycle (Pillar 12)

    Biological sleep has distinct processing stages. So does Freya:

      Stage 1 ΓÇö Light Sleep (Pruning)
          Aggressively prune hypotheses below confidence threshold.
          Like slow-wave sleep clearing metabolic waste.

      Stage 2 ΓÇö Deep Sleep (Consolidation)
          Find clusters of similar confirmed hypotheses and synthesize
          a "belief anchor" ΓÇö a single high-confidence meta-belief that
          represents the pattern. Written as a new hypothesis with
          origin_node=BIFROST_NODE_ID and confidence=0.9.

      Stage 3 ΓÇö REM (Creative Dreaming)
          The existing run_dream_cycle(): memory collision pairs,
          guided dreaming, nightmare processing.

      Stage 4 ΓÇö Reflection (Self-Model Update)
          Call self_model.reflect() in background if cooldown allows.
          The agent updates her self-assessment before waking.

    Args:
        stages: list of ints [1,2,3,4] ΓÇö which stages to run. Default: all.
        All other args passed through to Stage 3.
    """
    if stages is None:
        stages = [1, 2, 3, 4]

    log.info("[hypotheses] Sleep cycle starting ΓÇö stages=%s seed=%s",
             stages, seed[:60] if seed else None)

    summary: dict = {"stages": stages, "ts": int(time.time())}

    # -----------------------------------------------------------------------
    # Stage 1: Light Sleep ΓÇö Aggressive low-confidence pruning
    # -----------------------------------------------------------------------
    if 1 in stages:
        stage1: dict = {"pruned": 0}
        try:
            tbl = _get_table()
            if tbl is not None:
                PRUNE_THRESHOLD = 0.15
                rows = tbl.search().where(
                    f"confidence < {PRUNE_THRESHOLD} AND tested = false"
                ).limit(200).to_list()
                # Batch collect IDs then single-pass delete
                prune_ids = []
                for row in rows:
                    rid = _safe_id(row.get("id", ""))
                    if rid:
                        prune_ids.append(rid)
                if prune_ids:
                    id_list = ", ".join(f"'{i}'" for i in prune_ids)
                    tbl.delete(f"id IN ({id_list})")
                stage1["pruned"] = len(prune_ids)
                log.info("[sleep/stage1] Pruned %d weak beliefs (conf < %.2f)",
                         len(prune_ids), PRUNE_THRESHOLD)
        except Exception as e:
            log.warning("[sleep/stage1] pruning error: %s", e)
            stage1["error"] = str(e)
        summary["stage1"] = stage1

    # -----------------------------------------------------------------------
    # Stage 2: Deep Sleep ΓÇö Cluster consolidation into belief anchors
    # -----------------------------------------------------------------------
    if 2 in stages:
        stage2: dict = {"anchors_created": 0}
        try:
            tbl = _get_table()
            if tbl is not None:
                confirmed = tbl.search().where(
                    "tested = true AND test_result = 'confirmed'"
                ).limit(100).to_list()

                if len(confirmed) >= 3:
                    # Cluster by embedding similarity ΓÇö simple greedy grouping
                    used    = set()
                    anchors = 0
                    for i, base in enumerate(confirmed):
                        if base.get("id") in used:
                            continue
                        # Skip beliefs that are already anchors
                        if str(base.get("id", "")).startswith("anc-"):
                            continue
                        base_emb = list(base.get("embedding") or [])
                        if not base_emb:
                            continue
                        if not base_emb:
                            continue
                        cluster = [base]
                        for j, other in enumerate(confirmed):
                            if i == j or other.get("id") in used:
                                continue
                            other_emb = list(other.get("embedding") or [])
                            if other_emb and _cosine_sim(base_emb, other_emb) > 0.78:
                                cluster.append(other)
                        if len(cluster) < 3:
                            continue
                        # Synthesize anchor text from cluster
                        cluster_texts = [c.get("hypothesis", "")[:80] for c in cluster[:5]]
                        anchor_text   = (
                            f"[Belief Anchor ΓÇö {len(cluster)} confirmations] "
                            f"Pattern: {cluster_texts[0][:60]}..."
                        )
                        anchor_conf   = min(0.95, 0.85 + 0.02 * len(cluster))
                        anchor_emb    = _embed(anchor_text)
                        if anchor_emb:
                            import uuid as _uuid
                            anchor_id = "anc-" + str(_uuid.uuid4())[:8]
                            ts = int(time.time())
                            tbl.add([{
                                "id":          anchor_id,
                                "source_a":    cluster[0].get("source_a", ""),
                                "source_b":    cluster[1].get("source_a", ""),
                                "hypothesis":  anchor_text,
                                "embedding":   [float(x) for x in anchor_emb],
                                "confidence":  anchor_conf,
                                "valence":     0.5,
                                "tested":      True,
                                "test_result": "confirmed",
                                "origin_node": BIFROST_NODE_ID,
                                "shared_from": "",
                                "ts":          ts,
                            }])
                            anchors += 1
                            for c in cluster:
                                used.add(c.get("id"))
                            log.info("[sleep/stage2] Anchor created from %d beliefs: %s",
                                     len(cluster), anchor_text[:60])

                stage2["anchors_created"] = anchors
                log.info("[sleep/stage2] Consolidation complete ΓÇö %d anchors", anchors)
        except Exception as e:
            log.warning("[sleep/stage2] consolidation error: %s", e)
            stage2["error"] = str(e)
        summary["stage2"] = stage2

    # -----------------------------------------------------------------------
    # Stage 3: REM ΓÇö Creative dreaming (existing pipeline)
    # -----------------------------------------------------------------------
    if 3 in stages:
        if seed:
            log.info("[sleep/stage3] REM ΓÇö guided dream (seed: %s)", seed[:60])
        else:
            log.info("[sleep/stage3] REM ΓÇö free association dream")
        dream_result = run_dream_cycle(
            seed=seed, auto_share=auto_share, peer_urls=peer_urls
        )
        summary["stage3"] = dream_result
    else:
        summary["stage3"] = {"skipped": True}

    # -----------------------------------------------------------------------
    # Stage 4: Reflection ΓÇö Update self-model (background, non-blocking)
    # -----------------------------------------------------------------------
    if 4 in stages:
        stage4: dict = {"triggered": False}
        try:
            from war_room import self_model as _sm
            import threading as _threading
            t = _threading.Thread(target=_sm.reflect, daemon=True)
            t.start()
            stage4["triggered"] = True
            log.info("[sleep/stage4] Self-model reflection triggered")
        except Exception as e:
            log.debug("[sleep/stage4] self_model not available: %s", e)
            stage4["error"] = str(e)
        summary["stage4"] = stage4

    log.info("[hypotheses] Sleep cycle complete ΓÇö %s", {
        k: v for k, v in summary.items() if k.startswith("stage")
    })
    return summary



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Auto-decay timestamp Γò¼├┤Γö£├ºΓö£Γòó run decay at most once every 12h even if /sleep is never called
_last_decay_ts: float = 0.0
_DECAY_INTERVAL = 12 * 3600   # 12 hours

# Contagion cap: no single hypothesis can receive more than this from cascades
_CONTAGION_MAX_BOOST = 0.15

def get_hypotheses(
    limit:         int   = 10,
    min_confidence:float  = 0.0,
    tested:        Optional[bool] = None,
) -> dict:
    """
    GET /hypotheses?limit=10&min_confidence=0.0&tested=false

    Returns hypotheses sorted by confidence (highest first).
    tested=false Γò¼├┤Γö£├æΓö£├Ñ only unvalidated; tested=true Γò¼├┤Γö£├æΓö£├Ñ only validated; omit Γò¼├┤Γö£├æΓö£├Ñ all.
    """
    global _last_decay_ts

    # Automatic background decay: at most once per _DECAY_INTERVAL so stale beliefs
    # wither even if the operator never explicitly calls POST /sleep.
    if time.time() - _last_decay_ts > _DECAY_INTERVAL:
        _last_decay_ts = time.time()   # update before running to prevent re-entry
        try:
            ds = _decay_hypotheses()
            if ds.get("decayed", 0) > 0 or ds.get("purged", 0) > 0:
                log.info("[hypotheses] Auto-decay: %d weakened, %d purged",
                         ds["decayed"], ds["purged"])
        except Exception:
            pass

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
                "id":          r["id"],
                "hypothesis":  r["hypothesis"],
                "source_a":    r["source_a"],
                "source_b":    r["source_b"],
                "confidence":  round(conf, 3),
                "valence":     round(float(r.get("valence", 0.0)), 3),
                "tested":      _t,
                "test_result": r.get("test_result", ""),
                "origin_node": r.get("origin_node", BIFROST_NODE_ID),
                "shared_from": r.get("shared_from", ""),
                "ts":          int(r.get("ts", 0)),
            })

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "hypotheses": results[:limit],
            "total":      len(results[:limit]),
        }

    except Exception as e:
        log.error("[hypotheses] get failed: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Mesh attribution: sharing and receiving
# ---------------------------------------------------------------------------

_SHARE_RATE_MAX_SENDERS = 100  # cap tracked senders to prevent memory leak
_share_rate: dict = {}  # sender -> [timestamps]


def _rate_limit_prune():
    """Evict oldest sender keys if _share_rate exceeds cap."""
    if len(_share_rate) > _SHARE_RATE_MAX_SENDERS:
        # Sort by most recent timestamp, keep newest 80
        by_recency = sorted(_share_rate.items(),
                            key=lambda kv: max(kv[1]) if kv[1] else 0,
                            reverse=True)
        keep = {k for k, _ in by_recency[:80]}
        for k in list(_share_rate.keys()):
            if k not in keep:
                del _share_rate[k]

def receive_shared_hypothesis(payload: dict, sender: str) -> dict:
    """
    Receive a hypothesis pushed from a peer node.

    Safety gates:
      1. Rate limit: max SHARE_RATE_LIMIT per sender per 60s
      2. Replay protection: reject if ts is older than SHARE_MAX_AGE_S
      3. Stand review: reject self-destructive patterns
      4. Dedup: reject near-duplicates (cosine > 0.90)
      5. Confidence discount: foreign beliefs * FOREIGN_CONF_DISCOUNT

    Returns {"ok": bool, "id": str|None, "reason": str}
    """
    now = time.time()

    # --- Rate limit ---
    sender_times = _share_rate.setdefault(sender, [])
    sender_times[:] = [t for t in sender_times if now - t < 60]
    if len(sender_times) >= SHARE_RATE_LIMIT:
        log.warning("[hypotheses] share rate limit hit for %s (%d/60s)",
                    sender, len(sender_times))
        return {"ok": False, "id": None, "reason": "rate_limited"}
    sender_times.append(now)

    # --- Replay protection ---
    payload_ts = int(payload.get("ts", 0))
    if payload_ts and (now - payload_ts) > SHARE_MAX_AGE_S:
        log.warning("[hypotheses] share replay rejected Γò¼├┤Γö£├ºΓö£Γòó ts %d is %ds old",
                    payload_ts, int(now - payload_ts))
        return {"ok": False, "id": None, "reason": "replay_too_old"}

    text = str(payload.get("hypothesis", "")).strip()
    if not text:
        return {"ok": False, "id": None, "reason": "empty_hypothesis"}

    # --- Stand review ---
    rejection = _stand_review(text)
    if rejection:
        log.warning("[hypotheses] shared belief REJECTED by Stand: %s Γò¼├┤Γö£├ºΓö£Γòó %s",
                    rejection, text[:60])
        return {"ok": False, "id": None, "reason": f"stand_review: {rejection}"}

    # --- Embed + dedup ---
    text_emb = _embed(text)
    if not text_emb:
        return {"ok": False, "id": None, "reason": "embed_failed"}
    dim = len(text_emb)
    tbl = _ensure_table(dim)

    if _dedup_check(tbl, text_emb):
        return {"ok": False, "id": None, "reason": "duplicate"}

    # --- Confidence discount ---
    raw_conf = float(payload.get("confidence", 0.5))
    confidence = max(0.1, raw_conf * FOREIGN_CONF_DISCOUNT)
    valence    = float(payload.get("valence", 0.0))
    origin     = str(payload.get("origin_node", sender))

    hid = f"hyp_{uuid.uuid4().hex[:12]}"
    ts  = int(now)
    tbl.add([{
        "id":          hid,
        "source_a":    str(payload.get("source_a", "remote")),
        "source_b":    str(payload.get("source_b", "remote")),
        "hypothesis":  text,
        "embedding":   [float(x) for x in text_emb],
        "confidence":  float(confidence),
        "valence":     float(valence),
        "tested":      False,
        "test_result": "",
        "origin_node": origin,
        "shared_from": sender,
        "ts":          ts,
    }])

    log.info("[hypotheses] Received shared belief [%s] from %s (origin=%s, conf=%.2fΓò¼├┤Γö£├æΓö£├Ñ%.2f): %s",
             hid, sender, origin, raw_conf, confidence, text[:60])
    _rate_limit_prune()  # evict stale sender keys to cap memory
    return {"ok": True, "id": hid, "reason": "accepted"}


def share_batch(hids: list, peer_urls: list) -> dict:
    """
    Push hypotheses to peer nodes via fire-and-forget daemon threads.

    For each peer URL, spawns a thread that POSTs the hypotheses as a
    JSON array to {peer}/hypotheses/share. Returns immediately.
    """
    import urllib.request

    tbl = _get_table()
    if tbl is None:
        return {"queued": 0, "peers": 0, "reason": "no_table"}

    # Fetch hypothesis data to share
    hyps_to_share = []
    for hid in hids:
        try:
            rows = tbl.search().where(f"id = '{_safe_id(hid)}'").limit(1).to_list()
            if rows:
                r = rows[0]
                hyps_to_share.append({
                    "hypothesis":  r.get("hypothesis", ""),
                    "confidence":  float(r.get("confidence", 0.5)),
                    "valence":     float(r.get("valence", 0.0)),
                    "source_a":    r.get("source_a", ""),
                    "source_b":    r.get("source_b", ""),
                    "origin_node": r.get("origin_node", BIFROST_NODE_ID),
                    "ts":          int(r.get("ts", 0)),
                })
        except Exception as e:
            log.debug("[hypotheses] share_batch: failed to fetch %s: %s", hid, e)

    if not hyps_to_share:
        return {"queued": 0, "peers": 0, "reason": "no_hypotheses_found"}

    payload_bytes = json.dumps({"hypotheses": hyps_to_share}).encode()

    def _push_to_peer(peer_url: str):
        try:
            req = urllib.request.Request(
                f"{peer_url}/hypotheses/share",
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                log.info("[hypotheses] Pushed %d beliefs to %s Γò¼├┤Γö£├ºΓö£Γòó %d",
                         len(hyps_to_share), peer_url, resp.status)
        except Exception as e:
            log.warning("[hypotheses] Push to %s failed: %s", peer_url, e)

    for url in peer_urls:
        t = threading.Thread(target=_push_to_peer, args=(url,),
                             daemon=True, name=f"share-{url}")
        t.start()

    log.info("[hypotheses] Queued %d beliefs for %d peers (fire-and-forget)",
             len(hyps_to_share), len(peer_urls))
    return {"queued": len(hyps_to_share), "peers": len(peer_urls)}


def test_hypothesis(hyp_id: str, result: str, confidence_delta: float = 0.1) -> dict:
    """
    POST /hypotheses/test {id, result: "confirmed"|"refuted", confidence_delta}

    Mark a hypothesis as tested. Confirmed Γò¼├┤Γö£├æΓö£├Ñ confidence +delta; refuted Γò¼├┤Γö£├æΓö£├Ñ Γò¼├┤Γö£├ºΓö£Γöñdelta.
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
            values={"tested": True, "confidence": new_conf, "test_result": result},
        )
        log.info("[hypotheses] Tested %s Γò¼├┤Γö£├æΓö£├Ñ %s (%.2f Γò¼├┤Γö£├æΓö£├Ñ %.2f)", hyp_id, result, old_conf, new_conf)

        # -------------------------------------------------------------------
        # Semantic Contagion: propagate belief update to nearest neighbors.
        # Cap: no neighbor may receive more than _CONTAGION_MAX_BOOST total
        # from cascade (prevents rapid-fire confirms from inflating clusters).
        # -------------------------------------------------------------------
        contagion_ids = []
        try:
            row_emb = list(rows[0].get("embedding") or [])
            if row_emb:
                contagion_delta = 0.05 if result == "confirmed" else -0.05
                neighbors = tbl.search(row_emb).limit(6).to_list()
                for nb in neighbors:
                    nb_id  = nb.get("id", "")
                    nb_emb = list(nb.get("embedding") or [])
                    if nb_id == safe_hid or not nb_emb:
                        continue
                    cos = _cosine_sim(row_emb, nb_emb)
                    if cos < 0.70:
                        continue
                    nb_conf     = float(nb.get("confidence", 0.5))
                    # Contagion cap: don't push a neighbor above base + _CONTAGION_MAX_BOOST
                    # or below base - _CONTAGION_MAX_BOOST from cascades alone
                    nb_base     = float(nb.get("confidence", 0.5))  # pre-cascade value
                    if contagion_delta > 0:
                        nb_new_conf = min(nb_base + _CONTAGION_MAX_BOOST,
                                         nb_conf + contagion_delta)
                    else:
                        nb_new_conf = max(nb_base - _CONTAGION_MAX_BOOST,
                                         nb_conf + contagion_delta)
                    nb_new_conf = max(0.0, min(1.0, nb_new_conf))
                    safe_nb_id = _safe_id(nb_id)
                    tbl.update(
                        where=f"id = '{safe_nb_id}'",
                        values={"confidence": nb_new_conf},
                    )
                    contagion_ids.append(nb_id)
                    log.debug("[hypotheses] contagion %s Γò¼├┤Γö£├æΓö£├Ñ %.2f (cos=%.2f, capped)",
                              nb_id, nb_new_conf, cos)
        except Exception as ce:
            log.debug("[hypotheses] contagion step error: %s", ce)
        # -------------------------------------------------------------------

        topic = "hypothesis.confirmed" if result == "confirmed" else "hypothesis.refuted"
        if _BUS_OK:
            _bus.publish(topic, {
                "id":         hyp_id,
                "text":       str(rows[0].get("hypothesis", ""))[:120],
                "confidence": round(new_conf, 3),
                "delta":      round(new_conf - old_conf, 3),
            })

        return {"ok": True, "id": hyp_id, "result": result,
                "old_confidence": round(old_conf, 3),
                "new_confidence": round(new_conf, 3),
                "contagion": contagion_ids}

    except Exception as e:
        log.error("[hypotheses] test failed: %s", e)
        return {"error": str(e)}
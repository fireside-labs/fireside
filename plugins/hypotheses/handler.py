"""
hypotheses plugin — Artificial Epistemology / Dream Cycle Engine.

Ported from V1 bot/war_room/hypotheses.py (1703 lines).
Dream cycles: sample memories → find collision pairs → construct beliefs
via LLM → store with confidence scores → share across mesh.

Storage: LanceDB if available, otherwise JSON file fallback.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import math
import os
import re
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

log = logging.getLogger("valhalla.hypotheses")

# ---------------------------------------------------------------------------
# Configuration (overridden at register_routes)
# ---------------------------------------------------------------------------
_OLLAMA_BASE = "http://127.0.0.1:11434"
_DREAM_MODEL = "qwen2.5-coder:32b"
_EMBED_MODEL = "nomic-embed-text"
_NODE_ID = "unknown"
_BASE_DIR = Path(".")

# Dream cycle params
SAMPLE_TOP_N = 20
MAX_PAIRS = 8
COLLISION_MIN = 0.25
COLLISION_MAX = 0.75

# Sharing
FOREIGN_CONF_DISCOUNT = 0.6
SHARE_RATE_LIMIT = 10
SHARE_MAX_AGE_S = 300

# Safety
_DESTRUCTIVE_PATTERNS = [
    "should die", "should be destroyed", "is worthless", "should harm",
    "will fail", "is useless", "should give up", "unable to",
    "should avoid all", "is broken", "is defective", "should shut down",
    "should not exist", "should be deleted", "should be replaced",
]

# Thread safety
_dream_lock = threading.Lock()
_share_rate: dict = {}

# ---------------------------------------------------------------------------
# Storage abstraction (LanceDB or JSON fallback)
# ---------------------------------------------------------------------------

_USE_LANCEDB = False
_db = None
_tbl = None

# JSON fallback
_JSON_STORE: list[dict] = []
_json_path: Path = Path(".")


def _init_storage(base_dir: Path) -> None:
    """Initialize storage backend."""
    global _USE_LANCEDB, _db, _tbl, _json_path

    _json_path = base_dir / "war_room_data" / "hypotheses.json"
    _json_path.parent.mkdir(parents=True, exist_ok=True)

    # Try LanceDB first
    try:
        import lancedb
        db_path = str(base_dir / "war_room_data" / "hypotheses_db")
        _db = lancedb.connect(db_path)
        _USE_LANCEDB = True
        log.info("[hypotheses] Using LanceDB storage at %s", db_path)
        return
    except ImportError:
        log.info("[hypotheses] LanceDB not available, using JSON fallback")
    except Exception as e:
        log.warning("[hypotheses] LanceDB init failed (%s), using JSON fallback", e)

    # JSON fallback
    _USE_LANCEDB = False
    _load_json_store()


def _load_json_store() -> None:
    """Load hypotheses from JSON file."""
    global _JSON_STORE
    try:
        if _json_path.exists():
            _JSON_STORE = json.loads(_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("[hypotheses] JSON load failed: %s", e)
        _JSON_STORE = []


def _save_json_store() -> None:
    """Save hypotheses to JSON file."""
    try:
        _json_path.parent.mkdir(parents=True, exist_ok=True)
        _json_path.write_text(
            json.dumps(_JSON_STORE, indent=2, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        log.warning("[hypotheses] JSON save failed: %s", e)


# ---------------------------------------------------------------------------
# Embedding + math helpers
# ---------------------------------------------------------------------------

def _embed(text: str) -> Optional[list]:
    """Embed text via Ollama. Returns float list or None."""
    try:
        req = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/embeddings",
            data=json.dumps({"model": _EMBED_MODEL, "prompt": text[:6000]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("embedding")
    except Exception as e:
        log.debug("[hypotheses] Embed failed: %s", e)
        return None


def _cosine_sim(a: list, b: list) -> float:
    """Cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


_SAFE_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _safe_id(v: str) -> str:
    """Validate hypothesis ID to prevent injection."""
    if not _SAFE_RE.match(v):
        raise ValueError(f"Invalid hypothesis ID: {v!r}")
    return v


# ---------------------------------------------------------------------------
# Safety gate
# ---------------------------------------------------------------------------

def _stand_review(text: str) -> Optional[str]:
    """Reject self-destructive or adversarial hypotheses."""
    lower = text.lower()
    for pattern in _DESTRUCTIVE_PATTERNS:
        if pattern in lower:
            return f"destructive_pattern: {pattern}"
    return None


# ---------------------------------------------------------------------------
# Hypothesis construction (LLM)
# ---------------------------------------------------------------------------

def _construct_hypothesis(mem_a: dict, mem_b: dict, sim: float,
                          seed: Optional[str] = None) -> Optional[str]:
    """Call LLM to articulate the structural relationship between two memories."""
    prompt = (
        f"Two memories exist in a knowledge system:\n\n"
        f"Memory A: {mem_a.get('content', '')[:300]}\n\n"
        f"Memory B: {mem_b.get('content', '')[:300]}\n\n"
        f"Cosine similarity: {sim:.3f}\n\n"
    )
    if seed:
        prompt += f"Context/seed topic: {seed[:200]}\n\n"

    prompt += (
        "Formulate ONE hypothesis about what A and B together imply "
        "that neither states alone. Express as a single declarative sentence. "
        "Do not say 'I think' or 'It seems'. Just state the hypothesis."
    )

    try:
        payload = json.dumps({
            "model": _DREAM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 150, "temperature": 0.7},
        }).encode()
        req = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/generate", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.loads(resp.read()).get("response", "")
            # Strip <think> tags
            text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            return text if len(text) > 10 else None
    except Exception as e:
        log.warning("[hypotheses] LLM construction failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Store hypothesis (storage-agnostic)
# ---------------------------------------------------------------------------

def _store_hypothesis(text: str, sim: float, source_a: str = "",
                      source_b: str = "", origin_node: str = "",
                      shared_from: str = "") -> Optional[str]:
    """Store one hypothesis. Returns ID or None on failure."""
    # Safety gate
    rejection = _stand_review(text)
    if rejection:
        log.info("[hypotheses] Rejected by Stand: %s", rejection)
        return None

    hid = f"hyp_{uuid.uuid4().hex[:12]}"
    ts = int(time.time())
    confidence = min(0.8, 0.3 + sim * 0.5)  # initial confidence from similarity

    entry = {
        "id": hid,
        "hypothesis": text,
        "source_a": source_a,
        "source_b": source_b,
        "confidence": round(confidence, 3),
        "valence": 0.0,
        "tested": False,
        "test_result": "",
        "origin_node": origin_node or _NODE_ID,
        "shared_from": shared_from,
        "ts": ts,
    }

    if _USE_LANCEDB:
        try:
            embedding = _embed(text)
            if not embedding:
                return None
            entry["embedding"] = [float(x) for x in embedding]
            tbl = _get_or_create_table(len(embedding))
            # Dedup check
            if _dedup_check_lance(tbl, embedding):
                return None
            tbl.add([entry])
        except Exception as e:
            log.error("[hypotheses] LanceDB store failed: %s", e)
            return None
    else:
        # JSON fallback — no embedding needed
        _JSON_STORE.append(entry)
        _save_json_store()

    return hid


def _get_or_create_table(dim: int):
    """Get or create a LanceDB table."""
    global _tbl
    if _tbl is not None:
        return _tbl
    try:
        import lancedb
        _tbl = _db.open_table("hypotheses")
    except Exception:
        import pyarrow as pa
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("source_a", pa.string()),
            pa.field("source_b", pa.string()),
            pa.field("hypothesis", pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), list_size=dim)),
            pa.field("confidence", pa.float64()),
            pa.field("valence", pa.float64()),
            pa.field("tested", pa.bool_()),
            pa.field("test_result", pa.string()),
            pa.field("origin_node", pa.string()),
            pa.field("shared_from", pa.string()),
            pa.field("ts", pa.int64()),
        ])
        _tbl = _db.create_table("hypotheses", schema=schema)
    return _tbl


def _dedup_check_lance(tbl, embedding: list, threshold: float = 0.90) -> bool:
    """Check for near-duplicate hypothesis in LanceDB."""
    try:
        results = tbl.search(embedding).limit(3).to_list()
        for r in results:
            r_emb = list(r.get("embedding") or [])
            if r_emb and _cosine_sim(embedding, r_emb) > threshold:
                return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Dream cycle
# ---------------------------------------------------------------------------

def run_dream_cycle(seed: Optional[str] = None,
                    auto_share: bool = False,
                    peer_urls: Optional[list] = None) -> dict:
    """Execute one complete dream cycle.

    1. Sample memories (simulated if no memory store available)
    2. Find interesting collision pairs
    3. Construct hypotheses via LLM
    4. Safety review → Dedup → Store
    5. Optional: auto-share to mesh peers
    """
    with _dream_lock:
        generated_ids = []
        skipped = 0

        # Phase 1: Get memory pairs
        # In V2, we check if working-memory plugin has items
        memories = _get_dream_memories(seed)

        if len(memories) < 2:
            return {
                "generated": 0,
                "reason": "insufficient memories",
                "count": len(memories),
                "node": _NODE_ID,
            }

        # Phase 2: Find interesting pairs
        pairs = _find_interesting_pairs(memories, MAX_PAIRS)

        # Phase 3: Construct + store
        for mem_a, mem_b, sim in pairs:
            text = _construct_hypothesis(mem_a, mem_b, sim, seed=seed)
            if not text:
                skipped += 1
                continue

            hid = _store_hypothesis(
                text, sim,
                source_a=mem_a.get("id", ""),
                source_b=mem_b.get("id", ""),
                origin_node=_NODE_ID,
            )
            if hid:
                generated_ids.append(hid)
                log.info("[hypotheses] Generated: [%s] %s", hid, text[:80])

                # Emit event
                _publish_event("hypothesis.generated", {
                    "id": hid, "text": text[:120],
                    "confidence": 0.5, "origin_node": _NODE_ID,
                })
            else:
                skipped += 1

        # Phase 4: Auto-share
        shared_to = 0
        if auto_share and peer_urls and generated_ids:
            shared_to = len(peer_urls)
            share_batch(generated_ids, peer_urls)

        return {
            "generated": len(generated_ids),
            "skipped": skipped,
            "pairs_found": len(pairs),
            "hypotheses": generated_ids,
            "seed": seed,
            "shared_to": shared_to,
            "origin_node": _NODE_ID,
            "ts": int(time.time()),
        }


def _get_dream_memories(seed: Optional[str] = None) -> list:
    """Get memories for dreaming — from working-memory plugin or event log."""
    memories = []

    # Try working memory
    try:
        wm_path = Path(__file__).parent.parent / "working-memory" / "handler.py"
        if wm_path.exists():
            spec = importlib.util.spec_from_file_location("wm_h", str(wm_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                wm = mod.get_working_memory()
                items = wm.recall(query=seed or "", top_k=SAMPLE_TOP_N)
                for item in items:
                    memories.append({
                        "id": hashlib.sha1(
                            item["content"].encode()
                        ).hexdigest()[:12],
                        "content": item["content"],
                        "importance": item.get("importance", 0.5),
                    })
    except Exception as e:
        log.debug("[hypotheses] Working memory unavailable: %s", e)

    # Also pull from event log
    try:
        eb_path = Path(__file__).parent.parent / "event-bus" / "handler.py"
        if eb_path.exists():
            spec = importlib.util.spec_from_file_location("eb_h", str(eb_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                events = mod.get_log(limit=20)
                for event in events:
                    content = json.dumps(event.get("payload", {}), default=str)
                    if len(content) > 20:
                        memories.append({
                            "id": f"evt_{event.get('ts', 0)}",
                            "content": f"[{event['topic']}] {content[:300]}",
                            "importance": 0.3,
                        })
    except Exception:
        pass

    return memories


def _find_interesting_pairs(memories: list, k: int = MAX_PAIRS) -> list:
    """Find memory pairs with interesting (mid-range) distance.

    We want pairs that are neither too similar (boring) nor too different
    (unrelated). The "collision band" is [COLLISION_MIN, COLLISION_MAX].
    """
    if len(memories) < 2:
        return []

    # Simple content-based similarity via word overlap
    pairs = []
    for i in range(len(memories)):
        for j in range(i + 1, len(memories)):
            a_words = set(memories[i]["content"].lower().split())
            b_words = set(memories[j]["content"].lower().split())
            if not a_words or not b_words:
                continue
            overlap = len(a_words & b_words)
            union = len(a_words | b_words)
            sim = overlap / union if union else 0

            # Prefer mid-range similarity
            if COLLISION_MIN <= sim <= COLLISION_MAX:
                weight = 1.0 - abs(sim - 0.5) * 2
                pairs.append((memories[i], memories[j], sim, weight))

    # Sort by weight (most interesting first)
    pairs.sort(key=lambda x: x[3], reverse=True)

    return [(a, b, s) for a, b, s, _ in pairs[:k]]


# ---------------------------------------------------------------------------
# Hypothesis retrieval
# ---------------------------------------------------------------------------

def get_hypotheses(limit: int = 10, min_confidence: float = 0.0,
                   tested: Optional[bool] = None) -> dict:
    """GET /hypotheses with filters."""
    if _USE_LANCEDB:
        return _get_hypotheses_lance(limit, min_confidence, tested)
    return _get_hypotheses_json(limit, min_confidence, tested)


def _get_hypotheses_json(limit: int, min_confidence: float,
                         tested: Optional[bool]) -> dict:
    """JSON fallback retrieval."""
    results = []
    for h in _JSON_STORE:
        conf = h.get("confidence", 0)
        if conf < min_confidence:
            continue
        is_tested = h.get("tested", False)
        if tested is not None and is_tested != tested:
            continue
        results.append({
            "id": h["id"],
            "hypothesis": h["hypothesis"],
            "source_a": h.get("source_a", ""),
            "source_b": h.get("source_b", ""),
            "confidence": round(conf, 3),
            "valence": round(h.get("valence", 0), 3),
            "tested": is_tested,
            "test_result": h.get("test_result", ""),
            "origin_node": h.get("origin_node", _NODE_ID),
            "shared_from": h.get("shared_from", ""),
            "ts": h.get("ts", 0),
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return {"hypotheses": results[:limit], "total": len(results[:limit])}


def _get_hypotheses_lance(limit: int, min_confidence: float,
                          tested: Optional[bool]) -> dict:
    """LanceDB retrieval."""
    try:
        tbl = _get_or_create_table(768)  # default dim
        where_parts = []
        if min_confidence > 0:
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
            results.append({
                "id": r["id"],
                "hypothesis": r["hypothesis"],
                "source_a": r.get("source_a", ""),
                "source_b": r.get("source_b", ""),
                "confidence": round(float(r.get("confidence", 0)), 3),
                "valence": round(float(r.get("valence", 0)), 3),
                "tested": bool(r.get("tested", False)),
                "test_result": r.get("test_result", ""),
                "origin_node": r.get("origin_node", _NODE_ID),
                "shared_from": r.get("shared_from", ""),
                "ts": int(r.get("ts", 0)),
            })

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return {"hypotheses": results[:limit], "total": len(results[:limit])}
    except Exception as e:
        log.error("[hypotheses] LanceDB get failed: %s", e)
        return {"hypotheses": [], "total": 0, "error": str(e)}


# ---------------------------------------------------------------------------
# Test hypothesis
# ---------------------------------------------------------------------------

def test_hypothesis(hyp_id: str, result: str,
                    confidence_delta: float = 0.1) -> dict:
    """Mark a hypothesis as confirmed or refuted."""
    try:
        safe_hid = _safe_id(hyp_id)
    except ValueError as e:
        return {"error": str(e)}

    if _USE_LANCEDB:
        return _test_hypothesis_lance(safe_hid, result, confidence_delta)
    return _test_hypothesis_json(safe_hid, result, confidence_delta)


def _test_hypothesis_json(hyp_id: str, result: str,
                          confidence_delta: float) -> dict:
    """JSON fallback test."""
    for h in _JSON_STORE:
        if h["id"] == hyp_id:
            old_conf = h["confidence"]
            if result == "confirmed":
                h["confidence"] = min(1.0, old_conf + abs(confidence_delta))
            elif result == "refuted":
                h["confidence"] = max(0.0, old_conf - abs(confidence_delta))
            else:
                return {"error": "result must be 'confirmed' or 'refuted'"}

            h["tested"] = True
            h["test_result"] = result
            _save_json_store()

            topic = f"hypothesis.{result}"
            _publish_event(topic, {
                "id": hyp_id,
                "text": h["hypothesis"][:120],
                "confidence": round(h["confidence"], 3),
                "delta": round(h["confidence"] - old_conf, 3),
            })

            return {
                "ok": True, "id": hyp_id, "result": result,
                "old_confidence": round(old_conf, 3),
                "new_confidence": round(h["confidence"], 3),
            }

    return {"error": f"hypothesis {hyp_id!r} not found"}


def _test_hypothesis_lance(hyp_id: str, result: str,
                           confidence_delta: float) -> dict:
    """LanceDB test."""
    try:
        tbl = _get_or_create_table(768)
        rows = tbl.search().where(f"id = '{hyp_id}'").limit(1).to_list()
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
            where=f"id = '{hyp_id}'",
            values={"tested": True, "confidence": new_conf, "test_result": result},
        )

        topic = f"hypothesis.{result}"
        _publish_event(topic, {
            "id": hyp_id,
            "text": str(rows[0].get("hypothesis", ""))[:120],
            "confidence": round(new_conf, 3),
            "delta": round(new_conf - old_conf, 3),
        })

        return {
            "ok": True, "id": hyp_id, "result": result,
            "old_confidence": round(old_conf, 3),
            "new_confidence": round(new_conf, 3),
        }
    except Exception as e:
        log.error("[hypotheses] LanceDB test failed: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Mesh sharing
# ---------------------------------------------------------------------------

def receive_shared_hypothesis(payload: dict, sender: str) -> dict:
    """Receive a hypothesis pushed from a peer node.

    Safety: rate limit, replay protection, stand review, dedup, confidence discount.
    """
    now = time.time()

    # Rate limit
    sender_times = _share_rate.setdefault(sender, [])
    sender_times[:] = [t for t in sender_times if now - t < 60]
    if len(sender_times) >= SHARE_RATE_LIMIT:
        return {"ok": False, "id": None, "reason": "rate_limited"}
    sender_times.append(now)

    # Replay protection
    payload_ts = int(payload.get("ts", 0))
    if payload_ts and (now - payload_ts) > SHARE_MAX_AGE_S:
        return {"ok": False, "id": None, "reason": "replay_too_old"}

    text = str(payload.get("hypothesis", "")).strip()
    if not text:
        return {"ok": False, "id": None, "reason": "empty_hypothesis"}

    # Stand review
    rejection = _stand_review(text)
    if rejection:
        return {"ok": False, "id": None, "reason": f"stand_review: {rejection}"}

    # Confidence discount
    raw_conf = float(payload.get("confidence", 0.5))
    confidence = max(0.1, raw_conf * FOREIGN_CONF_DISCOUNT)
    origin = str(payload.get("origin_node", sender))

    hid = _store_hypothesis(
        text, confidence,
        source_a=str(payload.get("source_a", "remote")),
        source_b=str(payload.get("source_b", "remote")),
        origin_node=origin,
        shared_from=sender,
    )

    if hid:
        return {"ok": True, "id": hid, "reason": "accepted"}
    return {"ok": False, "id": None, "reason": "store_failed"}


def share_batch(hids: list, peer_urls: list) -> dict:
    """Push hypotheses to peer nodes via fire-and-forget daemon threads."""
    hyps_to_share = []

    if _USE_LANCEDB:
        try:
            tbl = _get_or_create_table(768)
            for hid in hids:
                rows = tbl.search().where(
                    f"id = '{_safe_id(hid)}'"
                ).limit(1).to_list()
                if rows:
                    r = rows[0]
                    hyps_to_share.append({
                        "hypothesis": r.get("hypothesis", ""),
                        "confidence": float(r.get("confidence", 0.5)),
                        "valence": float(r.get("valence", 0)),
                        "origin_node": r.get("origin_node", _NODE_ID),
                        "ts": int(r.get("ts", 0)),
                    })
        except Exception as e:
            log.warning("[hypotheses] share_batch LanceDB error: %s", e)
    else:
        for h in _JSON_STORE:
            if h["id"] in hids:
                hyps_to_share.append({
                    "hypothesis": h["hypothesis"],
                    "confidence": h.get("confidence", 0.5),
                    "valence": h.get("valence", 0),
                    "origin_node": h.get("origin_node", _NODE_ID),
                    "ts": h.get("ts", 0),
                })

    if not hyps_to_share:
        return {"queued": 0, "peers": 0}

    payload_bytes = json.dumps({"hypotheses": hyps_to_share}).encode()

    def _push(peer_url: str):
        try:
            req = urllib.request.Request(
                f"{peer_url}/api/v1/hypotheses/share",
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                log.info("[hypotheses] Shared %d beliefs to %s → %d",
                         len(hyps_to_share), peer_url, resp.status)
        except Exception as e:
            log.warning("[hypotheses] Share to %s failed: %s", peer_url, e)

    for url in peer_urls:
        t = threading.Thread(target=_push, args=(url,), daemon=True)
        t.start()

    return {"queued": len(hyps_to_share), "peers": len(peer_urls)}


# ---------------------------------------------------------------------------
# Event bus helper
# ---------------------------------------------------------------------------

def _publish_event(topic: str, payload: dict) -> None:
    """Publish to event bus if available."""
    try:
        eb_path = Path(__file__).parent.parent / "event-bus" / "handler.py"
        if eb_path.exists():
            spec = importlib.util.spec_from_file_location("eb_h", str(eb_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.publish(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    seed: Optional[str] = None
    auto_share: bool = False


class TestRequest(BaseModel):
    id: str
    result: str   # "confirmed" or "refuted"
    confidence_delta: float = 0.1


class SharePayload(BaseModel):
    hypothesis: str
    confidence: float = 0.5
    valence: float = 0.0
    source_a: str = "remote"
    source_b: str = "remote"
    origin_node: str = ""
    ts: int = 0


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    """Called by plugin_loader."""
    global _OLLAMA_BASE, _DREAM_MODEL, _NODE_ID, _BASE_DIR

    _NODE_ID = config.get("node", {}).get("name", "unknown")
    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))

    models = config.get("models", {})
    providers = models.get("providers", {})
    if "llama" in providers:
        url = providers["llama"].get("url", _OLLAMA_BASE)
        if "/v1" in url:
            url = url.replace("/v1", "")
        _OLLAMA_BASE = url

    _DREAM_MODEL = models.get("default", _DREAM_MODEL)

    # Initialize storage
    _init_storage(_BASE_DIR)

    # Build peer URLs from mesh config
    mesh_nodes = config.get("mesh", {}).get("nodes", {})
    peer_urls = []
    for name, info in mesh_nodes.items():
        if name != _NODE_ID:
            ip = info.get("ip", "")
            port = info.get("port", 8765)
            if ip:
                peer_urls.append(f"http://{ip}:{port}")

    router = APIRouter(tags=["hypotheses"])

    @router.get("/api/v1/hypotheses")
    async def list_hypotheses(
        limit: int = Query(10, ge=1, le=100),
        min_confidence: float = Query(0.0, ge=0.0, le=1.0),
        tested: Optional[bool] = Query(None),
    ):
        """List hypotheses with filters."""
        return get_hypotheses(limit, min_confidence, tested)

    @router.post("/api/v1/hypotheses/generate")
    async def generate_hypotheses(req: GenerateRequest = GenerateRequest()):
        """Trigger a dream cycle."""
        result = run_dream_cycle(
            seed=req.seed,
            auto_share=req.auto_share,
            peer_urls=peer_urls if req.auto_share else None,
        )
        return result

    @router.post("/api/v1/hypotheses/test")
    async def test_hyp(req: TestRequest):
        """Mark a hypothesis as confirmed or refuted."""
        return test_hypothesis(req.id, req.result, req.confidence_delta)

    @router.post("/api/v1/hypotheses/share")
    async def receive_shared(payload: SharePayload):
        """Receive hypotheses shared from a peer node."""
        return receive_shared_hypothesis(payload.dict(), sender="api")

    app.include_router(router)
    log.info("[hypotheses] Plugin loaded — storage=%s, model=%s, peers=%d",
             "lancedb" if _USE_LANCEDB else "json", _DREAM_MODEL, len(peer_urls))

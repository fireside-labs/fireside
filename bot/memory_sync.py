"""
memory_sync.py -- Bifrost Agent Memory Sync Engine (Thor)
v1 -- gossip sync of high-importance memories across the mesh.

Schema (Odin-locked):
  {
    "memory_id": "uuid",
    "node":      "thor",
    "agent":     "thor",
    "content":   "...",
    "embedding": [0.1, 0.2, ...],   # generated locally via Ollama if missing
    "tags":      ["python", "sql"],
    "importance": 0.85,             # 0.0-1.0
    "ts":         1234567890,
    "shared":     true
  }

Sync rule: importance >= 0.7 AND shared == true gossip across nodes.
Embeddings generated via Ollama /api/embeddings (no external deps).
"""

import json
import logging
import threading
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional

log = logging.getLogger("bifrost.memory")

SYNC_IMPORTANCE_THRESHOLD = 0.7
EMBED_MODEL = "nomic-embed-text"   # Ollama embedding model — fast, small
EMBED_DIM   = 768                  # nomic-embed-text output dimension
OLLAMA_BASE = "http://localhost:11434"

# ---------------------------------------------------------------------------
# LanceDB table — lazy-init on first use
# ---------------------------------------------------------------------------
_db     = None
_table  = None
_lock   = threading.Lock()

def _get_table(db_path: Path):
    """Lazy-init LanceDB table. Thread-safe."""
    global _db, _table
    if _table is not None:
        return _table
    with _lock:
        if _table is not None:
            return _table
        try:
            import lancedb
            import pyarrow as pa
            _db = lancedb.connect(str(db_path))
            schema = pa.schema([
                pa.field("memory_id",  pa.string()),
                pa.field("node",       pa.string()),
                pa.field("agent",      pa.string()),
                pa.field("content",    pa.string()),
                pa.field("embedding",  pa.list_(pa.float32(), EMBED_DIM)),
                pa.field("tags",       pa.string()),  # JSON array stored as string
                pa.field("importance", pa.float32()),
                pa.field("ts",         pa.int64()),
                pa.field("shared",     pa.bool_()),
            ])
            if "memories" in _db.table_names():
                _table = _db.open_table("memories")
            else:
                _table = _db.create_table("memories", schema=schema)
                log.info("Created LanceDB memories table at %s", db_path)
        except Exception as e:
            log.error("LanceDB init failed: %s", e)
            raise
    return _table


def get_embedding(text: str, ollama_base: str = OLLAMA_BASE) -> Optional[list]:
    """Generate embedding via local Ollama. Returns list of floats or None."""
    try:
        payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
        req = urllib.request.Request(
            f"{ollama_base}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        embedding = data.get("embedding", [])
        if len(embedding) != EMBED_DIM:
            log.warning("Embedding dim mismatch: got %d, expected %d", len(embedding), EMBED_DIM)
            # Pad or truncate to match schema
            embedding = (embedding + [0.0] * EMBED_DIM)[:EMBED_DIM]
        return embedding
    except Exception as e:
        log.warning("Embedding generation failed: %s — using zero vector", e)
        return [0.0] * EMBED_DIM


def upsert_memories(batch: list[dict], db_path: Path, ollama_base: str = OLLAMA_BASE) -> dict:
    """
    Upsert a batch of memories into LanceDB.
    Generates embeddings for any memory missing one.
    Returns {"upserted": N, "skipped": N, "errors": [...]}
    """
    table = _get_table(db_path)
    upserted = 0
    skipped = 0
    errors = []

    rows = []
    for mem in batch:
        try:
            # Validate required fields
            content = mem.get("content", "").strip()
            if not content:
                skipped += 1
                continue

            importance = float(mem.get("importance", 0.0))
            shared = bool(mem.get("shared", False))

            # Generate embedding if not provided
            embedding = mem.get("embedding")
            if not embedding or len(embedding) != EMBED_DIM:
                embedding = get_embedding(content, ollama_base)

            row = {
                "memory_id":  mem.get("memory_id") or str(uuid.uuid4()),
                "node":       str(mem.get("node", "unknown")),
                "agent":      str(mem.get("agent", mem.get("node", "unknown"))),
                "content":    content,
                "embedding":  [float(x) for x in embedding],
                "tags":       json.dumps(mem.get("tags", [])),
                "importance": importance,
                "ts":         int(mem.get("ts") or time.time()),
                "shared":     shared,
            }
            rows.append(row)
            upserted += 1
        except Exception as e:
            errors.append(str(e))

    if rows:
        import pyarrow as pa
        table.merge_insert("memory_id") \
            .when_matched_update_all() \
            .when_not_matched_insert_all() \
            .execute(pa.Table.from_pylist(rows))

    log.info("Memory upsert: %d rows, %d skipped, %d errors", upserted, skipped, len(errors))
    return {"upserted": upserted, "skipped": skipped, "errors": errors}


def get_shareable_memories(db_path: Path) -> list[dict]:
    """
    Return all local memories that should gossip to peers:
    importance >= threshold AND shared == true.
    Strips embeddings from the payload (too bulky to gossip raw vectors).
    """
    table = _get_table(db_path)
    try:
        rows = table.search().where(
            f"importance >= {SYNC_IMPORTANCE_THRESHOLD} AND shared = true",
            prefilter=True,
        ).select(["memory_id", "node", "agent", "content", "tags", "importance", "ts", "shared"]) \
         .limit(500) \
         .to_list()
        for r in rows:
            if "tags" in r and isinstance(r["tags"], str):
                try:
                    r["tags"] = json.loads(r["tags"])
                except Exception:
                    r["tags"] = []
        return rows
    except Exception as e:
        log.error("get_shareable_memories failed: %s", e)
        return []


def push_memories_to_node(memories: list[dict], node_url: str) -> bool:
    """
    POST a batch of memories to another node's /memory-sync endpoint.
    Returns True on success.
    """
    if not memories:
        return True
    try:
        payload = json.dumps({"memories": memories}).encode()
        req = urllib.request.Request(
            f"{node_url}/memory-sync",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
        log.info("Pushed %d memories to %s: %s", len(memories), node_url, result)
        return True
    except Exception as e:
        log.warning("Memory push to %s failed: %s", node_url, e)
        return False


def stats(db_path: Path) -> dict:
    """Quick summary stats for the memories table."""
    try:
        table = _get_table(db_path)
        total = table.count_rows()
        shareable = table.count_rows(
            filter=f"importance >= {SYNC_IMPORTANCE_THRESHOLD} AND shared = true"
        )
        return {"total": total, "shareable": shareable, "threshold": SYNC_IMPORTANCE_THRESHOLD}
    except Exception as e:
        return {"error": str(e)}

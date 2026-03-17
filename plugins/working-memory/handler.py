"""
working-memory plugin — Human-inspired short-term memory buffer + LanceDB persistence.

Ported from V1 bot/working_memory.py (173 lines), extended with persistent
vector search via LanceDB.  Falls back to in-memory-only if lancedb is not
installed.

Hot cache:  in-memory LRU (last N items)
Cold store: LanceDB table at ~/.valhalla/lancedb/  (persistent vector search)
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

log = logging.getLogger("valhalla.working_memory")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_MAX_ITEMS = 10
_DECAY_SECONDS = 600   # items older than 10 min lose priority
_LANCEDB_DIR = Path.home() / ".valhalla" / "lancedb"
_EMBED_DIM = 384       # bag-of-words vector dimension


# ---------------------------------------------------------------------------
# Lightweight bag-of-words embedder (no external model needed)
# ---------------------------------------------------------------------------

class _BagOfWordsEmbedder:
    """Fallback: deterministic bag-of-words embedder using hashed term frequencies.

    Produces a fixed-dimension vector so LanceDB can index it.
    Used when sentence-transformers is not installed.
    """

    def __init__(self, dim: int = _EMBED_DIM):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        vec = [0.0] * self.dim
        if not tokens:
            return vec
        for token in tokens:
            idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        # L2-normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class _SentenceTransformerEmbedder:
    """Semantic embedder using all-MiniLM-L6-v2 (384-dim).

    Loads model lazily on first call to avoid startup overhead.
    Produces real semantic vectors for high-quality similarity search.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self):
        self._model = None

    def _load(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self.MODEL_NAME)
        log.info("[working-memory] Loaded embedding model: %s", self.MODEL_NAME)

    def embed(self, text: str) -> list[float]:
        if self._model is None:
            self._load()
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()


def _create_embedder():
    """Create the best available embedder, falling back to bag-of-words."""
    try:
        import sentence_transformers  # noqa: F401
        log.info("[working-memory] sentence-transformers available — using semantic embeddings")
        return _SentenceTransformerEmbedder()
    except ImportError:
        log.warning("[working-memory] sentence-transformers not installed — "
                    "using bag-of-words fallback. "
                    "Install with: pip install sentence-transformers")
        return _BagOfWordsEmbedder()


_embedder = _create_embedder()


# ---------------------------------------------------------------------------
# LanceDB persistent store (graceful fallback)
# ---------------------------------------------------------------------------

class LanceDBStore:
    """Persistent vector store backed by LanceDB.

    If lancedb is not installed, all methods are no-ops.
    """

    def __init__(self, db_path: Path = _LANCEDB_DIR):
        self._db = None
        self._table = None
        self._available = False
        self._db_path = db_path

        try:
            import lancedb as _ldb  # noqa: F401
            import pyarrow as pa

            db_path.mkdir(parents=True, exist_ok=True)
            self._db = _ldb.connect(str(db_path))

            # Create or open the memories table
            schema = pa.schema([
                pa.field("key", pa.utf8()),
                pa.field("content", pa.utf8()),
                pa.field("importance", pa.float32()),
                pa.field("source", pa.utf8()),
                pa.field("ts", pa.float64()),
                pa.field("vector", pa.list_(pa.float32(), _EMBED_DIM)),
            ])

            if "memories" in self._db.table_names():
                self._table = self._db.open_table("memories")
            else:
                self._table = self._db.create_table("memories", schema=schema)

            self._available = True
            log.info("[working-memory] LanceDB connected at %s", db_path)
        except ImportError:
            log.warning("[working-memory] lancedb not installed — "
                        "running in-memory-only mode. "
                        "Install with: pip install lancedb")
        except Exception as e:
            log.warning("[working-memory] LanceDB init failed: %s — "
                        "running in-memory-only mode", e)

    @property
    def available(self) -> bool:
        return self._available

    def upsert(self, key: str, content: str, importance: float,
               source: str, ts: float) -> None:
        """Insert or update a memory in LanceDB."""
        if not self._available:
            return
        try:
            vec = _embedder.embed(content)
            row = {
                "key": key,
                "content": content,
                "importance": importance,
                "source": source,
                "ts": ts,
                "vector": vec,
            }
            # Delete existing row with same key, then add
            try:
                self._table.delete(f"key = '{key}'")
            except Exception:
                pass
            self._table.add([row])
        except Exception as e:
            log.debug("[working-memory] LanceDB upsert failed: %s", e)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Vector similarity search."""
        if not self._available:
            return []
        try:
            vec = _embedder.embed(query)
            results = (
                self._table
                .search(vec)
                .limit(top_k)
                .to_list()
            )
            return [
                {
                    "content": r["content"],
                    "importance": r["importance"],
                    "source": r["source"],
                    "ts": r["ts"],
                    "score": r.get("_distance", 0.0),
                }
                for r in results
            ]
        except Exception as e:
            log.debug("[working-memory] LanceDB search failed: %s", e)
            return []

    def count(self) -> int:
        if not self._available:
            return 0
        try:
            return self._table.count_rows()
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# WorkingMemory class (ported from V1, extended with LanceDB)
# ---------------------------------------------------------------------------

class WorkingMemory:
    """Thread-safe LRU buffer of recently-used memories.

    Hot path: in-memory OrderedDict (fast, last N items).
    Cold path: LanceDB (persistent, vector-searchable).
    """

    def __init__(self, max_items: int = _MAX_ITEMS,
                 lance_store: Optional[LanceDBStore] = None):
        self._max = max_items
        self._buffer: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._lance = lance_store

    def _key(self, content: str) -> str:
        return hashlib.sha1(content.encode()).hexdigest()[:12]

    def observe(self, content: str, importance: float = 0.5,
                source: str = "unknown") -> str:
        """Add or refresh a memory in working memory. Returns key."""
        k = self._key(content)
        now = time.time()
        with self._lock:
            if k in self._buffer:
                self._buffer.move_to_end(k)
                self._buffer[k]["ts"] = now
                self._buffer[k]["hits"] = self._buffer[k].get("hits", 0) + 1
            else:
                self._buffer[k] = {
                    "content": content,
                    "importance": importance,
                    "source": source,
                    "ts": now,
                    "hits": 1,
                }
            while len(self._buffer) > self._max:
                self._buffer.popitem(last=False)

        # Persist to LanceDB (fire-and-forget, non-blocking)
        if self._lance and self._lance.available:
            try:
                self._lance.upsert(k, content, importance, source, now)
            except Exception:
                pass

        return k

    def recall(self, query: str = "", top_k: int = 5) -> list:
        """Return top-k items ranked by recency + importance."""
        now = time.time()
        with self._lock:
            items = list(self._buffer.values())

        if query:
            terms = query.lower().split()
            items = [m for m in items
                     if any(t in m["content"].lower() for t in terms)]

        scored = []
        for m in items:
            age = now - m["ts"]
            recency = max(0.1, 1.0 - (age / _DECAY_SECONDS))
            score = m["importance"] * recency * (1 + 0.1 * m.get("hits", 1))
            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [s[1] for s in scored[:top_k]]

        if results:
            self._hits += 1
        else:
            self._misses += 1

        return results

    def vector_search(self, query: str, top_k: int = 5) -> list:
        """Search persistent LanceDB store via vector similarity.

        Falls back to in-memory keyword recall if LanceDB is unavailable.
        """
        if self._lance and self._lance.available:
            results = self._lance.search(query, top_k)
            if results:
                return results
        # Fallback to in-memory keyword recall
        return self.recall(query, top_k)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return len(text) // 4 if text else 0

    def as_prompt_context(self, query: str = "", max_tokens: int = 2000,
                          existing_system_tokens: int = 0) -> str:
        """Format working memory as a system prompt injection block.

        Token-budget-aware: sheds lowest-scored memories first when
        the combined system prompt would exceed max_tokens.
        """
        items = self.recall(query, top_k=7)
        if not items:
            return ""

        available_tokens = max_tokens - existing_system_tokens
        if available_tokens < 100:
            return ""

        header = "[WORKING MEMORY - Recent context, no network fetch needed]"
        footer = "[END WORKING MEMORY]"
        overhead_tokens = self.estimate_tokens(header + footer)
        budget = available_tokens - overhead_tokens

        lines = [header]
        included = 0

        for i, m in enumerate(items):
            snippet = m["content"][:300]
            line = f"  {i+1}. [{m['source']}] {snippet}"
            line_tokens = self.estimate_tokens(line)
            if line_tokens > budget:
                continue
            lines.append(line)
            budget -= line_tokens
            included += 1

        if included == 0:
            return ""

        lines.append(footer)
        return "\n".join(lines)

    def clear(self):
        with self._lock:
            self._buffer.clear()

    def status(self) -> dict:
        with self._lock:
            lance_count = self._lance.count() if self._lance else 0
            return {
                "items": len(self._buffer),
                "capacity": self._max,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
                "lancedb_available": bool(self._lance and self._lance.available),
                "lancedb_total": lance_count,
                "contents": [
                    {
                        "key": k,
                        "source": v["source"],
                        "importance": v["importance"],
                        "age_s": round(time.time() - v["ts"], 1),
                        "hits": v.get("hits", 1),
                        "preview": v["content"][:80],
                    }
                    for k, v in self._buffer.items()
                ],
            }


# Global instances
_lance_store = LanceDBStore()
_wm = WorkingMemory(lance_store=_lance_store)


def get_working_memory() -> WorkingMemory:
    """Return the global WorkingMemory instance."""
    return _wm


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ObserveRequest(BaseModel):
    content: str
    importance: float = 0.5
    source: str = "api"


class RecallRequest(BaseModel):
    query: str = ""
    top_k: int = 5


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    """Called by plugin_loader."""
    router = APIRouter(tags=["working-memory"])

    @router.get("/api/v1/working-memory")
    async def get_wm_status():
        """Current working memory items and stats."""
        return _wm.status()

    @router.get("/api/v1/working-memory/status")
    async def get_wm_status_alias():
        """Alias for /api/v1/working-memory — frontend compatibility."""
        return _wm.status()

    @router.post("/api/v1/working-memory/observe")
    async def wm_observe(req: ObserveRequest):
        """Add an observation to working memory."""
        key = _wm.observe(req.content, req.importance, req.source)

        # Publish event
        try:
            from plugins.event_bus_api import publish
            publish("memory.observed", {
                "key": key,
                "source": req.source,
                "importance": req.importance,
            })
        except ImportError:
            pass

        return {
            "ok": True,
            "key": key,
            "items": _wm.status()["items"],
        }

    @router.post("/api/v1/working-memory/recall")
    async def wm_recall(req: RecallRequest):
        """Query working memory by relevance."""
        results = _wm.recall(req.query, req.top_k)

        try:
            from plugins.event_bus_api import publish
            publish("memory.recalled", {
                "query": req.query,
                "results": len(results),
            })
        except ImportError:
            pass

        return {
            "results": results,
            "count": len(results),
            "query": req.query,
        }

    @router.post("/api/v1/working-memory/search")
    async def wm_search(req: SearchRequest):
        """Vector similarity search across persistent memory (LanceDB).

        Falls back to keyword recall if LanceDB is not installed.
        """
        results = _wm.vector_search(req.query, req.top_k)

        try:
            from plugins.event_bus_api import publish
            publish("memory.searched", {
                "query": req.query,
                "results": len(results),
            })
        except ImportError:
            pass

        return {
            "results": results,
            "count": len(results),
            "query": req.query,
            "backend": "lancedb" if (_lance_store and _lance_store.available) else "in-memory",
        }

    app.include_router(router)
    log.info("[working-memory] Plugin loaded — %d item capacity, LanceDB: %s",
             _MAX_ITEMS, "active" if _lance_store.available else "unavailable")

"""
working-memory plugin — Human-inspired short-term memory buffer.

Ported from V1 bot/working_memory.py (173 lines).
Maintains a hot cache of the last N memories, injected into /ask
system prompts to eliminate network round-trips for recent context.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict

from fastapi import APIRouter, Query
from pydantic import BaseModel

log = logging.getLogger("valhalla.working_memory")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_MAX_ITEMS = 10
_DECAY_SECONDS = 600   # items older than 10 min lose priority


# ---------------------------------------------------------------------------
# WorkingMemory class (ported from V1)
# ---------------------------------------------------------------------------

class WorkingMemory:
    """Thread-safe LRU buffer of recently-used memories."""

    def __init__(self, max_items: int = _MAX_ITEMS):
        self._max = max_items
        self._buffer: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _key(self, content: str) -> str:
        return hashlib.sha1(content.encode()).hexdigest()[:12]

    def observe(self, content: str, importance: float = 0.5,
                source: str = "unknown") -> str:
        """Add or refresh a memory in working memory. Returns key."""
        k = self._key(content)
        with self._lock:
            if k in self._buffer:
                self._buffer.move_to_end(k)
                self._buffer[k]["ts"] = time.time()
                self._buffer[k]["hits"] = self._buffer[k].get("hits", 0) + 1
            else:
                self._buffer[k] = {
                    "content": content,
                    "importance": importance,
                    "source": source,
                    "ts": time.time(),
                    "hits": 1,
                }
            while len(self._buffer) > self._max:
                self._buffer.popitem(last=False)
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
            return {
                "items": len(self._buffer),
                "capacity": self._max,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
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


# Global instance
_wm = WorkingMemory()


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

    app.include_router(router)
    log.info("[working-memory] Plugin loaded — %d item capacity", _MAX_ITEMS)

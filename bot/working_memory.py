# -*- coding: utf-8 -*-
"""
working_memory.py -- Human-inspired short-term memory buffer.

Maintains a hot cache of the last N memories used in the current session.
Injected into /ask system prompts BEFORE querying Freya, eliminating
network round-trips for recently-used context.

The "7 +/- 2" rule: humans hold ~7 items in working memory.
We use 10 as our buffer size for a slightly larger working set.
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict

log = logging.getLogger("bifrost")

_MAX_ITEMS = 10
_DECAY_SECONDS = 600  # items older than 10 min lose priority


class WorkingMemory:
    """Thread-safe LRU buffer of recently-used memories."""

    def __init__(self, max_items: int = _MAX_ITEMS):
        self._max = max_items
        self._buffer: OrderedDict = OrderedDict()  # key -> {content, ts, importance, source}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _key(self, content: str) -> str:
        return hashlib.sha1(content.encode()).hexdigest()[:12]

    def observe(self, content: str, importance: float = 0.5, source: str = "unknown"):
        """Add or refresh a memory in working memory."""
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
            # Evict oldest if over capacity
            while len(self._buffer) > self._max:
                self._buffer.popitem(last=False)

    def recall(self, query: str = "", top_k: int = 5) -> list:
        """Return top-k items from working memory, ranked by recency + importance.
        If query is provided, filter to items containing query terms.
        """
        now = time.time()
        with self._lock:
            items = list(self._buffer.values())

        if query:
            terms = query.lower().split()
            items = [m for m in items if any(t in m["content"].lower() for t in terms)]

        # Score: importance * recency_factor
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
        """Rough token estimate: ~4 chars per token for English text."""
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

        # Calculate available token budget
        available_tokens = max_tokens - existing_system_tokens
        if available_tokens < 100:
            log.info("[wm] Context budget exhausted (available=%d tokens), shedding all", available_tokens)
            self._shed_count = getattr(self, "_shed_count", 0) + len(items)
            return ""

        header = "[WORKING MEMORY - Recent context, no network fetch needed]"
        footer = "[END WORKING MEMORY]"
        overhead_tokens = self.estimate_tokens(header + footer)
        budget = available_tokens - overhead_tokens

        lines = [header]
        included = 0
        shed = 0

        for i, m in enumerate(items):
            snippet = m["content"][:300]
            line = f"  {i+1}. [{m['source']}] {snippet}"
            line_tokens = self.estimate_tokens(line)
            if line_tokens > budget:
                shed += 1
                continue
            lines.append(line)
            budget -= line_tokens
            included += 1

        if shed > 0:
            self._shed_count = getattr(self, "_shed_count", 0) + shed
            log.info("[wm] Shed %d memories due to token budget (included %d)", shed, included)

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
    return _wm

# -*- coding: utf-8 -*-
"""
inference_cache.py -- Procedural memory / inference deduplication.

SHA256(prompt + system + model) keyed LRU cache with TTL.
Skips full Ollama inference when the same prompt was answered recently.
Like human muscle memory — repeated patterns become instant reflexes.

Usage:
    from inference_cache import InferenceCache
    cache = InferenceCache()
    hit = cache.get(prompt, system, model)
    if hit:
        return hit  # skip inference
    result = ollama.generate(...)
    cache.put(prompt, system, model, result)
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict

log = logging.getLogger("bifrost")

_DEFAULT_TTL = 300      # 5 minutes
_DEFAULT_MAX_SIZE = 500  # max cached entries


class InferenceCache:
    def __init__(self, ttl: float = _DEFAULT_TTL, max_size: int = _DEFAULT_MAX_SIZE):
        self._ttl = ttl
        self._max_size = max_size
        self._cache: OrderedDict = OrderedDict()  # key -> {response, ts, hits}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _key(self, prompt: str, system: str, model: str) -> str:
        raw = f"{model}:{system}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, system: str = "", model: str = "local") -> dict | None:
        """Look up cached inference result. Returns None on miss."""
        k = self._key(prompt, system, model)
        with self._lock:
            entry = self._cache.get(k)
            if entry is None:
                self._misses += 1
                return None
            # Check TTL
            if time.time() - entry["ts"] > self._ttl:
                del self._cache[k]
                self._misses += 1
                return None
            # Cache hit — move to end (most recently used)
            self._cache.move_to_end(k)
            entry["hits"] += 1
            self._hits += 1
            log.info("[icache] HIT key=%s hits=%d", k[:12], entry["hits"])
            return entry["response"]

    def put(self, prompt: str, system: str, model: str, response: dict):
        """Store an inference result in cache."""
        k = self._key(prompt, system, model)
        with self._lock:
            self._cache[k] = {
                "response": response,
                "ts": time.time(),
                "hits": 0,
                "prompt_preview": prompt[:80],
                "model": model,
            }
            self._cache.move_to_end(k)
            # Evict oldest if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
                self._evictions += 1

    def invalidate(self, prompt: str = "", system: str = "", model: str = ""):
        """Invalidate a specific entry or clear all if no args."""
        if not prompt:
            with self._lock:
                self._cache.clear()
            return
        k = self._key(prompt, system, model)
        with self._lock:
            self._cache.pop(k, None)

    def _purge_expired(self):
        """Remove all expired entries."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._cache.items() if now - v["ts"] > self._ttl]
            for k in expired:
                del self._cache[k]
            return len(expired)

    def status(self) -> dict:
        self._purge_expired()
        with self._lock:
            return {
                "cached_entries": len(self._cache),
                "capacity": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
                "evictions": self._evictions,
                "top_entries": [
                    {
                        "key": k[:12],
                        "model": v["model"],
                        "hits": v["hits"],
                        "age_s": round(time.time() - v["ts"], 1),
                        "preview": v["prompt_preview"],
                    }
                    for k, v in list(self._cache.items())[-10:]
                ],
            }


# Global instance
_icache = InferenceCache()


def get_inference_cache() -> InferenceCache:
    return _icache

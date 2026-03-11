"""
predictions plugin — Predictive Processing Engine (Free Energy Principle).

Ported from V1 bot/war_room/prediction.py (282 lines).
Before each /ask: predict(query) → generate expected answer embedding.
After each /ask:  score(hash, response) → compute prediction error.
High-surprise results → emit prediction.scored events.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import time
import urllib.request
from collections import deque
from typing import Optional

from fastapi import APIRouter, Query

log = logging.getLogger("valhalla.predictions")

# ---------------------------------------------------------------------------
# Configuration (overridden by valhalla.yaml at register_routes)
# ---------------------------------------------------------------------------
_EMBED_ENDPOINT = "http://127.0.0.1:11434"   # Ollama default
_EMBED_MODEL = "nomic-embed-text"
_HIGH_ERROR_THR = 0.55   # cosine distance above this = "surprising"
_LOW_ERROR_THR = 0.20    # below this = "boring" / well-predicted

# Rolling window
_MAX_HISTORY = 200
_history: deque = deque(maxlen=_MAX_HISTORY)

# Pending predictions: query_hash → {expected_embed, ts}
_pending: dict[str, dict] = {}

# Topic keywords for synthetic expected-answer generation
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "code": ["code", "function", "class", "bug", "error", "implement", "refactor",
             "python", "javascript", "test", "debug"],
    "memory": ["remember", "recall", "forgot", "memory", "earlier", "last time",
               "you said", "context"],
    "creative": ["write", "story", "poem", "imagine", "creative", "design",
                 "brainstorm", "idea"],
    "analysis": ["analyze", "compare", "explain", "why", "how does", "what is",
                 "difference", "evaluate"],
    "task": ["do", "make", "create", "build", "set up", "configure", "install",
             "deploy", "run"],
}


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

def _embed(text: str) -> Optional[list]:
    """Embed text via Ollama nomic-embed-text. Returns float list or None."""
    try:
        req = urllib.request.Request(
            f"{_EMBED_ENDPOINT}/api/embeddings",
            data=json.dumps({"model": _EMBED_MODEL, "prompt": text[:4000]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("embedding")
    except Exception as e:
        log.debug("[predictions] Embedding failed: %s", e)
        return None


def _cosine_sim(a: list, b: list) -> float:
    """Cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Synthetic expected-answer generation
# ---------------------------------------------------------------------------

def _synthesize_expected(query: str) -> str:
    """Generate a synthetic expected-answer string for embedding.

    Matches the query against topic keyword buckets.
    Falls back to a generic frame if no topic matches.
    """
    q_lower = query.lower()

    # Find best matching topic
    best_topic = "general"
    best_score = 0
    for topic, keywords in _TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > best_score:
            best_score = score
            best_topic = topic

    templates = {
        "code": f"Here's the implementation. The function handles {query[:50]}. "
                "I've included error handling and tests.",
        "memory": f"Based on our earlier conversation about {query[:50]}, "
                  "I recall the key points and context.",
        "creative": f"Here's a creative take on {query[:50]}. "
                    "I've explored multiple angles and perspectives.",
        "analysis": f"Let me break down {query[:50]}. "
                    "The key factors are: structure, purpose, and implications.",
        "task": f"I've completed the task related to {query[:50]}. "
                "Here are the steps taken and the results.",
        "general": f"Regarding {query[:50]}, here's a comprehensive response "
                   "covering the main points.",
    }

    return templates.get(best_topic, templates["general"])


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def predict(query: str) -> Optional[str]:
    """Called BEFORE /ask dispatch.

    Generates a synthetic expected-answer, embeds it, and stores it keyed
    by query_hash. Returns the query_hash (used to match score() call).
    """
    query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

    expected = _synthesize_expected(query)
    expected_embed = _embed(expected)

    if expected_embed is None:
        log.debug("[predictions] Skipping prediction (embedding failed)")
        return None

    _pending[query_hash] = {
        "expected_embed": expected_embed,
        "expected_text": expected[:200],
        "query": query[:200],
        "ts": time.time(),
    }

    # Clean old pending entries (>5 min)
    cutoff = time.time() - 300
    stale = [k for k, v in _pending.items() if v["ts"] < cutoff]
    for k in stale:
        del _pending[k]

    return query_hash


def score(query_hash: Optional[str], actual_response: str) -> Optional[float]:
    """Called AFTER /ask completes.

    Embeds the actual response, computes cosine distance from the
    predicted embed, and publishes prediction.scored to the event bus.
    Returns the error float, or None if scoring is not possible.
    """
    if query_hash is None or query_hash not in _pending:
        return None

    pending = _pending.pop(query_hash)
    actual_embed = _embed(actual_response[:4000])

    if actual_embed is None:
        return None

    sim = _cosine_sim(pending["expected_embed"], actual_embed)
    error = 1.0 - sim  # distance: 0 = perfect prediction, 1 = totally wrong

    result = {
        "query_hash": query_hash,
        "query": pending["query"],
        "error": round(error, 4),
        "similarity": round(sim, 4),
        "surprising": error > _HIGH_ERROR_THR,
        "predicted": error < _LOW_ERROR_THR,
        "ts": int(time.time()),
    }

    _history.append(result)

    # Publish event
    try:
        # Try importing from the event-bus plugin
        import importlib.util
        from pathlib import Path
        handler_path = Path(__file__).parent.parent / "event-bus" / "handler.py"
        if handler_path.exists():
            spec = importlib.util.spec_from_file_location("eb_handler", str(handler_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.publish("prediction.scored", result)
    except Exception:
        pass

    level = "⚡" if result["surprising"] else "📊"
    log.info("[predictions] %s error=%.3f query=%s",
             level, error, pending["query"][:60])

    return error


def get_stats() -> dict:
    """Return rolling accuracy stats."""
    if not _history:
        return {
            "total": 0,
            "surprising": 0,
            "predicted": 0,
            "avg_error": 0.0,
            "recent": [],
        }

    errors = [r["error"] for r in _history]
    surprising = sum(1 for r in _history if r["surprising"])
    predicted = sum(1 for r in _history if r["predicted"])

    return {
        "total": len(_history),
        "surprising": surprising,
        "predicted": predicted,
        "avg_error": round(sum(errors) / len(errors), 4),
        "surprise_rate": round(surprising / len(_history), 3),
        "prediction_rate": round(predicted / len(_history), 3),
        "recent": list(_history)[-20:],
    }


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    """Called by plugin_loader."""
    global _EMBED_ENDPOINT

    # Read inference config
    models = config.get("models", {})
    providers = models.get("providers", {})

    # Prefer local Ollama for embeddings
    if "llama" in providers:
        url = providers["llama"].get("url", _EMBED_ENDPOINT)
        # Ollama embedding endpoint is on base URL, not /v1
        if "/v1" in url:
            url = url.replace("/v1", "")
        _EMBED_ENDPOINT = url

    router = APIRouter(tags=["predictions"])

    @router.get("/api/v1/predictions")
    async def get_predictions(
        limit: int = Query(20, ge=1, le=100),
    ):
        """Rolling prediction accuracy stats + recent scores."""
        stats = get_stats()
        if limit < len(stats.get("recent", [])):
            stats["recent"] = stats["recent"][-limit:]
        return stats

    app.include_router(router)
    log.info("[predictions] Plugin loaded — endpoint=%s, model=%s",
             _EMBED_ENDPOINT, _EMBED_MODEL)

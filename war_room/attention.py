"""
attention.py — Mesh attention gradient tracker.

Answers the question: "What is the mesh currently thinking about?"

Every /memory-query call passes its query text through record_query().
We maintain a rolling 1-hour sliding window of query terms.
Clustering by word frequency reveals the mesh's current cognitive focus.

Exposes GET /attention:
{
  "focus":        ["consolidation", "api", "memory"],   # top 3 topics
  "focus_phrase": "consolidation and api management",   # human sentence
  "topics": [
    {"term": "consolidation", "hits": 12, "weight": 0.84},
    ...
  ],
  "query_count_1hr": 28,
  "window_seconds": 3600,
  "attention_entropy": 0.73   # 0=hyperfocused, 1=scattered
}

Entropy near 0 = mesh hammering one topic (crisis or deep work).
Entropy near 1 = mesh browsing broadly (exploration or idle).
"""

import collections
import math
import re
import threading
import time
from typing import Optional

_lock = threading.Lock()

# Rolling window of (timestamp, query_text)
_WINDOW_SECONDS = 3600      # 1 hour
_MAX_ENTRIES    = 500       # cap memory regardless of traffic

_queries: collections.deque = collections.deque(maxlen=_MAX_ENTRIES)

# Stopwords — filtered before frequency counting
_STOPWORDS = {
    "a", "an", "the", "is", "it", "in", "of", "to", "and", "or", "for",
    "on", "at", "by", "be", "as", "with", "this", "that", "from", "are",
    "was", "not", "do", "we", "i", "my", "me", "all", "can", "has",
    "have", "get", "set", "use", "get", "via", "into", "out", "up",
    "if", "so", "but", "its", "no", "will", "you", "what", "how",
    "node", "memory", "query",   # too common in this system to be informative
}


# ---------------------------------------------------------------------------
# Public record API
# ---------------------------------------------------------------------------

def record_query(query_text: str) -> None:
    """Record a /memory-query call. Called by the GET handler."""
    if not query_text or not query_text.strip():
        return
    with _lock:
        _queries.append((time.time(), query_text.strip().lower()[:200]))


# ---------------------------------------------------------------------------
# Attention computation
# ---------------------------------------------------------------------------

def _recent_queries() -> list:
    """Return queries within the current window."""
    cutoff = time.time() - _WINDOW_SECONDS
    with _lock:
        return [(ts, q) for ts, q in _queries if ts >= cutoff]


def _tokenize(text: str) -> list:
    """Split text into meaningful words, filtering stopwords."""
    words = re.findall(r"[a-z][a-z0-9_\-]{2,}", text)  # min 3 chars
    return [w for w in words if w not in _STOPWORDS]


def _entropy(weights: list) -> float:
    """Normalised Shannon entropy of a weight distribution."""
    total = sum(weights)
    if total == 0 or len(weights) < 2:
        return 0.0
    probs = [w / total for w in weights]
    raw   = -sum(p * math.log2(p) for p in probs if p > 0)
    max_e = math.log2(len(weights))
    return round(raw / max_e, 3) if max_e > 0 else 0.0


def _focus_phrase(top_terms: list) -> str:
    """Build a natural-sounding focus phrase from top terms."""
    if not top_terms:
        return "nothing in particular"
    if len(top_terms) == 1:
        return top_terms[0]
    if len(top_terms) == 2:
        return f"{top_terms[0]} and {top_terms[1]}"
    return f"{top_terms[0]}, {top_terms[1]}, and {top_terms[2]}"


def get_attention() -> dict:
    """Compute and return current attention gradient."""
    recent = _recent_queries()
    total  = len(recent)

    if total == 0:
        return {
            "focus":             [],
            "focus_phrase":      "nothing yet — mesh is quiet",
            "topics":            [],
            "query_count_1hr":   0,
            "window_seconds":    _WINDOW_SECONDS,
            "attention_entropy": 0.0,
        }

    # Count term frequencies across all recent queries
    freq: dict = collections.Counter()
    for _, q in recent:
        for tok in _tokenize(q):
            freq[tok] += 1

    # Top 15 terms by frequency
    top = freq.most_common(15)
    max_hits = top[0][1] if top else 1

    topics = [
        {
            "term":   term,
            "hits":   count,
            "weight": round(count / max_hits, 3),
        }
        for term, count in top
    ]

    top_terms  = [t["term"] for t in topics[:3]]
    focus_terms = [t["term"] for t in topics[:5]]
    weights    = [t["hits"] for t in topics]
    entropy    = _entropy(weights)

    # Attention state label
    if total < 3:
        state = "awakening"
    elif entropy < 0.3:
        state = "hyperfocused"
    elif entropy < 0.6:
        state = "focused"
    elif entropy < 0.8:
        state = "exploring"
    else:
        state = "scattered"

    return {
        "focus":             focus_terms,
        "focus_phrase":      _focus_phrase(top_terms),
        "attention_state":   state,
        "topics":            topics,
        "query_count_1hr":   total,
        "window_seconds":    _WINDOW_SECONDS,
        "attention_entropy": entropy,
    }

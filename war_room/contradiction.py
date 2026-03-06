"""
contradiction.py — Contradiction detection between memories.

When a new memory is upserted, this module checks whether any existing
high-similarity memories make the opposite claim.

Two memories are flagged as contradictory if:
  1. They share the same topic (cosine similarity above threshold)
  2. They have opposite valence (one positive, one negative)
  3. They contain opposed assertion keyword pairs

Returns a list of contradiction suspects, each with:
  {
    "existing_id":   "mem_abc...",
    "existing_text": "API calls succeed consistently.",
    "new_text":      "API calls are timing out repeatedly.",
    "similarity":    0.91,
    "conflict_type": "valence"    # "valence" | "keyword" | "both"
    "confidence":    0.78         # combined signal
  }

We journal contradictions via dream_journal automatically.
"""

import re

# ── Opposed keyword pairs ───────────────────────────────────────────────────
# If memory A contains the left word and memory B contains the right (or vice versa),
# they are likely making contradictory claims about the same subject.

_OPPOSED_PAIRS = [
    ("works",      "broken"),
    ("works",      "fail"),
    ("works",      "failed"),
    ("working",    "broken"),
    ("working",    "failed"),
    ("resolved",   "broken"),
    ("resolved",   "failing"),
    ("resolved",   "unresolved"),
    ("fixed",      "broken"),
    ("fixed",      "failing"),
    ("fixed",      "crash"),
    ("deployed",   "failed"),
    ("deployed",   "rollback"),
    ("stable",     "crash"),
    ("stable",     "unstable"),
    ("success",    "failure"),
    ("success",    "failed"),
    ("correct",    "wrong"),
    ("correct",    "incorrect"),
    ("healthy",    "error"),
    ("healthy",    "crash"),
    ("available",  "unavailable"),
    ("available",  "timeout"),
    ("up",         "down"),
    ("passing",    "failing"),
    ("fast",       "slow"),
    ("reliable",   "unreliable"),
    ("reliable",   "flaky"),
    ("approved",   "rejected"),
    ("approved",   "denied"),
    ("connected",  "disconnected"),
    ("connected",  "refused"),
]

# Minimum cosine similarity to consider memories as "about the same thing"
SIMILARITY_THRESHOLD = 0.72

# Minimum valence gap to count as opposite-valence
VALENCE_GAP_THRESHOLD = 0.6


def _keywords(text: str) -> set:
    """Extract meaningful words (lowercase) from text."""
    return set(re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()))


def _keyword_conflict(words_a: set, words_b: set) -> bool:
    """Return True if A and B contain any opposed keyword pair."""
    for left, right in _OPPOSED_PAIRS:
        if (left in words_a and right in words_b) or (right in words_a and left in words_b):
            return True
    return False


def check(
    new_content: str,
    new_valence: float,
    new_embedding: list,
    existing_memories: list,   # list of dicts from LanceDB search
    cosine_fn,                 # callable(a, b) -> float
) -> list:
    """
    Check for contradictions between new_content and existing_memories.

    existing_memories: top-K similar memories already retrieved from LanceDB.
    Returns a list of contradiction dicts sorted by confidence (highest first).
    """
    suspects = []
    new_words = _keywords(new_content)

    for mem in existing_memories:
        # Skip non-content or system memories
        tags = mem.get("tags") or []
        if "mycelium" in tags or "healing" in tags:
            continue

        existing_content = mem.get("content", "")
        if not existing_content:
            continue

        # Compute similarity if we have both embeddings
        existing_emb = mem.get("embedding")
        similarity = 0.0
        if existing_emb and new_embedding:
            try:
                similarity = cosine_fn(new_embedding, existing_emb)
            except Exception:
                similarity = 0.5   # assume possible match on error

        if similarity < SIMILARITY_THRESHOLD:
            continue

        existing_valence = float(mem.get("valence", 0.0))
        existing_words   = _keywords(existing_content)

        valence_conflict  = abs(new_valence - existing_valence) >= VALENCE_GAP_THRESHOLD
        keyword_conflict  = _keyword_conflict(new_words, existing_words)

        if not (valence_conflict or keyword_conflict):
            continue

        # Determine conflict type and confidence
        if valence_conflict and keyword_conflict:
            conflict_type = "both"
            confidence    = min(1.0, similarity * 0.5 + 0.5)
        elif keyword_conflict:
            conflict_type = "keyword"
            confidence    = min(1.0, similarity * 0.6 + 0.2)
        else:
            conflict_type = "valence"
            confidence    = min(1.0, similarity * 0.4 + 0.1)

        suspects.append({
            "existing_id":   mem.get("memory_id", ""),
            "existing_node": mem.get("node", "?"),
            "existing_text": existing_content[:120],
            "new_text":      new_content[:120],
            "similarity":    round(similarity, 3),
            "conflict_type": conflict_type,
            "confidence":    round(confidence, 3),
            "existing_valence": round(existing_valence, 3),
            "new_valence":      round(new_valence, 3),
        })

    # Sort by confidence descending
    suspects.sort(key=lambda x: x["confidence"], reverse=True)
    return suspects

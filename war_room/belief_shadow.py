"""
belief_shadow.py — Theory of Mind / Peer Belief Modeling (Pillar 11)

Theory (Premack & Woodruff, Baron-Cohen):
    The ability to model what *others* believe is fundamental to high-level
    cooperation and negotiation. True intelligence isn't just knowing what
    you know — it's knowing what your teammates know differently.

Application:
    Each node maintains a "Belief Shadow" of its peers: a compact model of
    what hypotheses that peer has confirmed, shared, and holds with high
    confidence.

    Before sharing a belief, Freya checks it against Thor's shadow:
    - Already in Thor's shadow? → skip (no point sharing what he knows)
    - Contradicts Thor's shadow? → flag for debate, don't quietly share
    - Novel to Thor? → high-value share

Mechanism:
    1. When a peer shares a hypothesis (hypothesis.received), update their shadow
    2. When a peer confirms/refutes via mesh test result, update their shadow
    3. Before share_batch(), filter out beliefs already in peer shadows
    4. Expose GET /belief-shadow/{node} for mesh introspection

Shadow schema (in-memory, bounded):
    _shadows: dict[node_id, dict]
        node_id → {
            "confirmed": deque([{id, text, confidence, ts}], maxlen=200),
            "shared": deque([{id, text, ts}], maxlen=200),
            "last_updated": int
        }

Endpoints:
    GET  /belief-shadow/{node}     — current shadow for a peer
    GET  /belief-shadows           — all known peer shadows (summary)
    POST /belief-shadow/update     — manually push a belief to a peer's shadow
"""

import logging
import time
from collections import deque
from typing import Optional

log = logging.getLogger("bifrost.belief_shadow")

# ---------------------------------------------------------------------------
# In-memory shadow store
# ---------------------------------------------------------------------------

_SHADOW_MAXLEN = 200   # max beliefs tracked per peer
_OVERLAP_SIM_THRESHOLD = 0.85   # cosine similarity above which = "already known"

_shadows: dict = {}   # node_id → {"confirmed": deque, "shared": deque, "last_updated": int}


def _get_shadow(node_id: str) -> dict:
    """Get or create a shadow for a node."""
    if node_id not in _shadows:
        _shadows[node_id] = {
            "confirmed":    deque(maxlen=_SHADOW_MAXLEN),
            "shared":       deque(maxlen=_SHADOW_MAXLEN),
            "last_updated": int(time.time()),
        }
    return _shadows[node_id]


# ---------------------------------------------------------------------------
# Shadow update API
# ---------------------------------------------------------------------------

def record_received(sender: str, hyp_id: str, text: str, confidence: float) -> None:
    """
    Record a hypothesis received from a peer.
    Called automatically when hypothesis.received fires on the event bus.
    """
    shadow = _get_shadow(sender)
    shadow["shared"].append({
        "id":         hyp_id,
        "text":       text[:120],
        "confidence": round(confidence, 3),
        "ts":         int(time.time()),
    })
    shadow["last_updated"] = int(time.time())
    log.debug("[belief_shadow] recorded shared belief from %s: %s", sender, hyp_id)


def record_confirmed(node_id: str, hyp_id: str, text: str, confidence: float) -> None:
    """
    Record a belief that a peer has confirmed (via test result propagation).
    """
    shadow = _get_shadow(node_id)
    # Avoid duplicates
    existing_ids = {e["id"] for e in shadow["confirmed"]}
    if hyp_id not in existing_ids:
        shadow["confirmed"].append({
            "id":         hyp_id,
            "text":       text[:120],
            "confidence": round(confidence, 3),
            "ts":         int(time.time()),
        })
        shadow["last_updated"] = int(time.time())
        log.debug("[belief_shadow] recorded confirmed belief for %s: %s", node_id, hyp_id)


# ---------------------------------------------------------------------------
# Relevance filtering before sharing
# ---------------------------------------------------------------------------

def filter_for_peer(hyp_ids: list, peer_node: str, get_hyp_fn) -> tuple:
    """
    Filter a list of hypothesis IDs before sharing to a peer.

    Returns (to_share, skipped_already_known, skipped_novel_count)

    get_hyp_fn: callable(hyp_id) → {hypothesis: str, confidence: float, ...}
        e.g. lambda hid: hypotheses.get_hypotheses(limit=1, ...)  # simplified
    """
    if peer_node not in _shadows:
        # No shadow yet — share everything, we'll learn as we go
        return hyp_ids, 0, len(hyp_ids)

    shadow = _shadows[peer_node]
    peer_known_ids = {e["id"] for e in shadow["shared"]} | {e["id"] for e in shadow["confirmed"]}

    to_share    = []
    already_known = 0

    for hid in hyp_ids:
        if hid in peer_known_ids:
            already_known += 1
            log.debug("[belief_shadow] skip %s → already in %s's shadow", hid, peer_node)
        else:
            to_share.append(hid)

    return to_share, already_known, len(to_share)


def novelty_score(hyp_id: str, hyp_text: str, peer_node: str) -> float:
    """
    Return a 0-1 novelty score for a hypothesis relative to a peer's shadow.
    1.0 = completely novel to this peer
    0.0 = already known / redundant

    Currently uses ID-based dedup. Future: embedding similarity check.
    """
    if peer_node not in _shadows:
        return 1.0  # Unknown peer → assume everything is novel

    shadow = _shadows[peer_node]
    all_known_ids = {e["id"] for e in shadow["shared"]} | {e["id"] for e in shadow["confirmed"]}

    if hyp_id in all_known_ids:
        return 0.0

    # Check for near-semantic-duplicate in shadow text (lightweight keyword overlap)
    hyp_words = set(hyp_text.lower().split())
    for entry in list(shadow["confirmed"]) + list(shadow["shared"]):
        entry_words = set(entry.get("text", "").lower().split())
        if not entry_words:
            continue
        overlap = len(hyp_words & entry_words) / max(len(hyp_words | entry_words), 1)
        if overlap > 0.6:
            log.debug("[belief_shadow] near-dup detected for %s vs %s's shadow (overlap=%.2f)",
                      hyp_id, peer_node, overlap)
            return max(0.0, 1.0 - overlap)

    return 1.0


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def get_shadow(node_id: str) -> dict:
    """Return the full shadow for a node. Used by GET /belief-shadow/{node}."""
    if node_id not in _shadows:
        return {
            "node":         node_id,
            "known":        False,
            "confirmed":    [],
            "shared":       [],
            "last_updated": None,
        }
    shadow = _shadows[node_id]
    return {
        "node":         node_id,
        "known":        True,
        "confirmed":    list(shadow["confirmed"]),
        "shared":       list(shadow["shared"]),
        "confirmed_count": len(shadow["confirmed"]),
        "shared_count":    len(shadow["shared"]),
        "last_updated": shadow["last_updated"],
    }


def get_all_shadows() -> dict:
    """Summary of all tracked peer shadows. Used by GET /belief-shadows."""
    return {
        node_id: {
            "confirmed_count": len(s["confirmed"]),
            "shared_count":    len(s["shared"]),
            "last_updated":    s["last_updated"],
        }
        for node_id, s in _shadows.items()
    }


# ---------------------------------------------------------------------------
# Event bus wiring (called from register_routes)
# ---------------------------------------------------------------------------

def wire_event_bus() -> None:
    """
    Subscribe to relevant event bus topics to auto-update shadows.
    Call once from bifrost_local.py's register_routes().
    """
    try:
        from war_room import event_bus as bus
        bus.subscribe("hypothesis.received", lambda e: record_received(
            sender     = e.get("sender", "unknown"),
            hyp_id     = e.get("id", ""),
            text       = e.get("text", ""),
            confidence = e.get("confidence", 0.5),
        ))
        bus.subscribe("hypothesis.confirmed", lambda e: (
            record_confirmed(
                node_id    = e.get("origin_node", ""),
                hyp_id     = e.get("id", ""),
                text       = e.get("text", ""),
                confidence = e.get("confidence", 0.5),
            ) if e.get("origin_node") else None
        ))
        log.info("[belief_shadow] wired to event bus")
    except Exception as e:
        log.warning("[belief_shadow] event bus wire failed: %s", e)

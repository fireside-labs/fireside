"""
dream_journal.py — Mesh dream journal / consolidation audit log.

Like an organism's dream cycle that processes the day's experiences,
this module records significant mesh events as journal entries:
  - Memory consolidation events (large batches written)
  - Mycelium healing events (nodes healed, vaccines recorded)
  - Stress episodes (nodes that spiked high-severity events)
  - Attention shifts (when the mesh's focus topic changes significantly)
  - Milestone memories written (permanent/high-importance)

Journal entries are persisted to a JSONL file (one JSON object per line).
GET /dream-journal returns the most recent N entries in reverse order.

Each entry:
{
  "id":       "dj_<timestamp_hex>",
  "ts":       1741234567.89,
  "ts_human": "2026-03-06T09:12:34",
  "event":    "consolidation",
  "summary":  "Wrote 12 memories in one batch (2 permanent). Largest batch today.",
  "detail":   {...},
  "valence":  0.8
}
"""

import datetime
import json
import os
import threading
import time
from pathlib import Path

_lock = threading.Lock()

_DEFAULT_JOURNAL_FILE = str(Path(__file__).parent.parent / "dream_journal.jsonl")
JOURNAL_FILE = os.environ.get("BIFROST_DREAM_JOURNAL", _DEFAULT_JOURNAL_FILE)

# In-memory recent entries cache (last 200)
_cache: list = []
_CACHE_MAX = 200

# Thresholds for what's worth journaling
_BATCH_CONSOLIDATION_THRESHOLD = 5    # write ≥5 memories at once → journal it
_HIGH_IMPORTANCE_THRESHOLD     = 0.85 # importance ≥ this → notable memory


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_id() -> str:
    return f"dj_{int(time.time() * 1000):x}"


def _ts_human() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _write_entry(entry: dict) -> None:
    """Append entry to JSONL file and update in-memory cache."""
    with _lock:
        try:
            with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass   # never let journaling break the caller
        _cache.append(entry)
        if len(_cache) > _CACHE_MAX:
            _cache.pop(0)


def _load_recent_from_disk(n: int = 100) -> list:
    """Read last N lines from JSONL file."""
    try:
        if not Path(JOURNAL_FILE).exists():
            return []
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        entries = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
            if len(entries) >= n:
                break
        return entries   # already in reverse-chronological order
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Public record API — called by bifrost_local patches
# ---------------------------------------------------------------------------

def record_consolidation(upserted: int, permanent: int, total: int) -> None:
    """Journal a memory write batch if it meets the threshold."""
    if upserted < _BATCH_CONSOLIDATION_THRESHOLD:
        return
    summary = (
        f"Wrote {upserted} memories in one batch "
        f"({permanent} permanent, {total} total in mesh)."
    )
    entry = {
        "id":       _make_id(),
        "ts":       time.time(),
        "ts_human": _ts_human(),
        "event":    "consolidation",
        "summary":  summary,
        "detail":   {"upserted": upserted, "permanent": permanent, "total": total},
        "valence":  0.7 if permanent > 0 else 0.4,
    }
    _write_entry(entry)


def record_healing(node: str, memories_injected: int, via_vaccine: bool = False) -> None:
    """Journal a mycelium healing event."""
    mode = "vaccine (instant)" if via_vaccine else "fresh search"
    summary = (
        f"Mycelium healed {node} with {memories_injected} memories via {mode}."
    )
    entry = {
        "id":       _make_id(),
        "ts":       time.time(),
        "ts_human": _ts_human(),
        "event":    "healing",
        "summary":  summary,
        "detail":   {"node": node, "injected": memories_injected, "via_vaccine": via_vaccine},
        "valence":  0.8 if via_vaccine else 0.6,
    }
    _write_entry(entry)


def record_stress(node: str, event_count: int) -> None:
    """Journal a node stress episode."""
    summary = f"Node {node} hit stress threshold: {event_count} high-severity events in 5 min."
    entry = {
        "id":       _make_id(),
        "ts":       time.time(),
        "ts_human": _ts_human(),
        "event":    "stress",
        "summary":  summary,
        "detail":   {"node": node, "event_count": event_count},
        "valence":  -0.5,
    }
    _write_entry(entry)


def record_milestone(content: str, importance: float, permanent: bool) -> None:
    """Journal a high-importance or permanent memory write."""
    flag = "permanent conviction" if permanent else f"importance={importance:.2f}"
    summary = f"Notable memory recorded ({flag}): {content[:80]}..."
    entry = {
        "id":       _make_id(),
        "ts":       time.time(),
        "ts_human": _ts_human(),
        "event":    "milestone",
        "summary":  summary,
        "detail":   {"content_preview": content[:120], "importance": importance, "permanent": permanent},
        "valence":  1.0 if permanent else 0.8,
    }
    _write_entry(entry)


def record_attention_shift(old_focus: list, new_focus: list) -> None:
    """Journal a significant change in the mesh's attention focus."""
    summary = (
        f"Attention shifted: [{', '.join(old_focus[:3])}] "
        f"→ [{', '.join(new_focus[:3])}]"
    )
    entry = {
        "id":       _make_id(),
        "ts":       time.time(),
        "ts_human": _ts_human(),
        "event":    "attention_shift",
        "summary":  summary,
        "detail":   {"from": old_focus[:5], "to": new_focus[:5]},
        "valence":  0.3,
    }
    _write_entry(entry)


# ---------------------------------------------------------------------------
# Query API — GET /dream-journal
# ---------------------------------------------------------------------------

def get_journal(limit: int = 20, event_filter: str = "") -> dict:
    """Return recent journal entries, newest first."""
    with _lock:
        cached = list(reversed(_cache))

    if not cached:
        cached = _load_recent_from_disk(limit * 2)

    if event_filter:
        cached = [e for e in cached if e.get("event") == event_filter]

    entries = cached[:limit]

    # Stats
    by_event: dict = {}
    for e in cached:
        ev = e.get("event", "unknown")
        by_event[ev] = by_event.get(ev, 0) + 1

    return {
        "entries":     entries,
        "count":       len(entries),
        "total_logged": len(cached),
        "by_event":    by_event,
        "journal_file": JOURNAL_FILE,
    }

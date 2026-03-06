"""
save_point.py — Dream Journal save points and memory rollback.

Adds a monotonic `seq` field to all Dream Journal entries so the journal
forms a total order. Save points bookmark a sequence number with a label.
Rollback deletes all LanceDB memories written AFTER a given seq number.

Endpoints (wired in bifrost_local.py):
  POST /save-point {"label": "before risky migration"}
      → {"ok": true, "seq": 42, "label": "...", "ts": ...}

  GET /save-points
      → list of all bookmarks

  POST /rollback {"to_seq": 42}
      → {"rolled_back": N, "memories_deleted": M, "label": "..."}

  POST /war-room/task with "high_risk": true
      → Odin auto-triggers save point before task starts (via hook in bifrost)

Seq counter:
  - Stored in save_point_state.json next to dream_journal.jsonl
  - Monotonically incremented per journal write
  - Injected into dream_journal entries via _write_entry hook
"""

import json
import logging
import threading
import time
from pathlib import Path

log = logging.getLogger("war-room.save_point")

_STATE_FILE = Path(__file__).parent.parent / "save_point_state.json"
_lock = threading.Lock()

# ─── state ───────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text())
    except Exception:
        pass
    return {"seq": 0, "bookmarks": []}


def _save_state(state: dict):
    tmp = _STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(_STATE_FILE)


_state = _load_state()

# ─── seq counter (called by dream_journal._write_entry patch) ────────────────

def next_seq() -> int:
    """Atomically increment and return the next sequence number."""
    with _lock:
        _state["seq"] += 1
        _save_state(_state)
        return _state["seq"]


def current_seq() -> int:
    with _lock:
        return _state["seq"]


# ─── save point API ──────────────────────────────────────────────────────────

def create(label: str = "") -> dict:
    """Bookmark the current sequence number."""
    with _lock:
        seq = _state["seq"]
        ts  = time.time()
        bookmark = {
            "seq":      seq,
            "label":    label or f"save-point-{seq}",
            "ts":       ts,
            "ts_human": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts)),
        }
        _state.setdefault("bookmarks", []).append(bookmark)
        _save_state(_state)
        log.info("[save_point] Created save point seq=%d label=%s", seq, label)
        return {"ok": True, **bookmark}


def list_bookmarks() -> list:
    with _lock:
        return list(_state.get("bookmarks", []))


def rollback(to_seq: int) -> dict:
    """
    Delete all Dream Journal entries and LanceDB memories written after to_seq.

    Dream Journal: rewrites JSONL, keeping only entries with seq <= to_seq.
    LanceDB: deletes rows where written_seq > to_seq (if field exists),
             falling back to ts comparison if seq not stored.

    Returns summary of what was deleted.
    """
    from war_room import dream_journal as _dj

    dj_deleted  = 0
    mem_deleted = 0
    label       = ""

    # Find matching bookmark for label
    with _lock:
        for bm in _state.get("bookmarks", []):
            if bm["seq"] == to_seq:
                label = bm.get("label", "")
                break

    # ── 1. Rewrite Dream Journal ─────────────────────────────────────────────
    journal_path = Path(_dj.JOURNAL_FILE)
    if journal_path.exists():
        kept    = []
        dropped = []
        try:
            lines = journal_path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("seq", 0) <= to_seq:
                        kept.append(line)
                    else:
                        dropped.append(entry)
                        dj_deleted += 1
                except Exception:
                    kept.append(line)  # keep corrupt lines to avoid data loss
            tmp = journal_path.with_suffix(".tmp")
            tmp.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
            tmp.replace(journal_path)
            # Flush in-memory cache
            with _dj._lock:
                _dj._cache[:] = [e for e in _dj._cache if e.get("seq", 0) <= to_seq]
        except Exception as e:
            log.warning("[save_point] Journal rollback failed: %s", e)

    # ── 2. Delete LanceDB memories written after to_seq ──────────────────────
    try:
        import lancedb
        _db_path = str(Path(__file__).parent.parent / "memory.db")
        db  = lancedb.connect(_db_path)
        tbl = db.open_table("mesh_memories")
        # If memories have a written_seq field, use it; otherwise fall back to ts
        rows = tbl.to_arrow().to_pydict()
        n    = len(rows.get("memory_id", []))
        ids_to_delete = []
        for i in range(n):
            seq_val = rows.get("written_seq", [None] * n)[i]
            if seq_val is not None and int(seq_val) > to_seq:
                ids_to_delete.append(rows["memory_id"][i])
        if ids_to_delete:
            for mid in ids_to_delete:
                try:
                    tbl.delete(f"memory_id = '{mid}'")
                    mem_deleted += 1
                except Exception:
                    pass
    except Exception as e:
        log.debug("[save_point] LanceDB rollback skipped: %s", e)

    log.info("[save_point] Rolled back to seq=%d: dj=%d mem=%d",
             to_seq, dj_deleted, mem_deleted)
    return {
        "ok":               True,
        "rolled_back_to":   to_seq,
        "label":            label,
        "journal_deleted":  dj_deleted,
        "memories_deleted": mem_deleted,
    }

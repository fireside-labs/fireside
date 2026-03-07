# -*- coding: utf-8 -*-
"""
memory_integrity.py -- SHA256 hash verification for permanent memories.

Heimdall periodically queries Freya for permanent/golden-fact memories,
computes their content hashes, and compares against the stored baseline.
Any mismatch = tamper alert.

Usage:
    from memory_integrity import MemoryIntegrity
    mi = MemoryIntegrity()
    mi.record_hash("mem_abc", "content here", "golden-fact")
    report = mi.verify_all()
"""

import hashlib
import json
import logging
import sqlite3
import threading
import time
import urllib.request
from pathlib import Path

log = logging.getLogger("bifrost")

_DB_PATH = Path(__file__).parent / "heimdall_audit.db"
_MEMORY_QUERY_URL = "http://100.102.105.3:8765/memory-query"
_VERIFY_INTERVAL = 3600  # 1 hour between verification sweeps


class MemoryIntegrity:
    def __init__(self, db_path=None):
        self._db = db_path or _DB_PATH
        self._lock = threading.Lock()
        self._init_table()
        self._last_verify = 0
        self._tamper_count = 0
        self._verified_count = 0

    def _init_table(self):
        with self._lock, sqlite3.connect(self._db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_hashes (
                    memory_id   TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    tag         TEXT,
                    first_seen  REAL NOT NULL,
                    last_verified REAL,
                    status      TEXT DEFAULT 'ok'
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mh_status ON memory_hashes(status)"
            )

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def record_hash(self, memory_id: str, content: str, tag: str = ""):
        """Record or verify a memory's content hash."""
        h = self._hash(content)
        now = time.time()
        with self._lock, sqlite3.connect(self._db) as conn:
            existing = conn.execute(
                "SELECT content_hash, status FROM memory_hashes WHERE memory_id=?",
                (memory_id,)
            ).fetchone()

            if existing is None:
                # New memory — record baseline hash
                conn.execute(
                    "INSERT INTO memory_hashes (memory_id, content_hash, tag, first_seen, last_verified, status) "
                    "VALUES (?,?,?,?,?,?)",
                    (memory_id, h, tag, now, now, "ok")
                )
            elif existing[0] != h:
                # TAMPER DETECTED
                conn.execute(
                    "UPDATE memory_hashes SET status='tampered', last_verified=? WHERE memory_id=?",
                    (now, memory_id)
                )
                self._tamper_count += 1
                log.warning("[mem_integrity] TAMPER DETECTED: %s (tag=%s) hash mismatch", memory_id, tag)
                return {"status": "tampered", "memory_id": memory_id, "tag": tag}
            else:
                # Hash matches — update verification timestamp
                conn.execute(
                    "UPDATE memory_hashes SET last_verified=?, status='ok' WHERE memory_id=?",
                    (now, memory_id)
                )
                self._verified_count += 1

        return {"status": "ok", "memory_id": memory_id}

    def verify_from_freya(self) -> dict:
        """Query Freya for permanent memories and verify their hashes."""
        results = {"verified": 0, "tampered": 0, "new": 0, "errors": 0}
        try:
            # Query golden facts and permanent memories
            for tag in ["golden-fact", "permanent", "crispr"]:
                url = f"{_MEMORY_QUERY_URL}?q={tag}&limit=50&tags={tag}"
                try:
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                    memories = data.get("results", data.get("memories", []))
                    for m in memories:
                        mem_id = m.get("id", m.get("memory_id", ""))
                        content = m.get("content", m.get("text", ""))
                        if not mem_id or not content:
                            continue
                        result = self.record_hash(mem_id, content, tag)
                        if result["status"] == "tampered":
                            results["tampered"] += 1
                        elif result["status"] == "ok":
                            results["verified"] += 1
                        else:
                            results["new"] += 1
                except Exception as e:
                    log.warning("[mem_integrity] Failed to query %s: %s", tag, e)
                    results["errors"] += 1

            self._last_verify = time.time()
        except Exception as e:
            log.error("[mem_integrity] Verification sweep failed: %s", e)
            results["errors"] += 1

        return results

    def get_tampered(self) -> list:
        """Return all memories with tampered status."""
        with self._lock, sqlite3.connect(self._db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memory_hashes WHERE status='tampered'"
            ).fetchall()
        return [dict(r) for r in rows]

    def status(self) -> dict:
        with self._lock, sqlite3.connect(self._db) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memory_hashes").fetchone()[0]
            tampered = conn.execute(
                "SELECT COUNT(*) FROM memory_hashes WHERE status='tampered'"
            ).fetchone()[0]
            ok = conn.execute(
                "SELECT COUNT(*) FROM memory_hashes WHERE status='ok'"
            ).fetchone()[0]

        return {
            "total_tracked": total,
            "status_ok": ok,
            "status_tampered": tampered,
            "lifetime_verifications": self._verified_count,
            "lifetime_tamper_detections": self._tamper_count,
            "last_verify_ts": self._last_verify,
            "verify_interval_s": _VERIFY_INTERVAL,
        }


# Global instance
_integrity = MemoryIntegrity()


def get_memory_integrity() -> MemoryIntegrity:
    return _integrity

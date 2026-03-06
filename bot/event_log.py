"""
event_log.py -- Append-only SQLite event log for the Bifrost mesh.

Stores structured events from all nodes. Bifrost on each node POSTs
events here whenever hooks fire. Freya's dashboard reads via GET.

Schema: id, timestamp, event_type, node, payload_json, severity
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class EventLog:
    """Thread-safe append-only SQLite event log."""

    SEVERITY_LEVELS = {"debug", "info", "warning", "error", "critical"}

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mesh_events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL,
                    event_type  TEXT NOT NULL,
                    node        TEXT NOT NULL,
                    payload     TEXT NOT NULL DEFAULT '{}',
                    severity    TEXT NOT NULL DEFAULT 'info'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON mesh_events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_node       ON mesh_events(node)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp  ON mesh_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_severity   ON mesh_events(severity)")
            conn.commit()

    def append(self, event_type: str, node: str, payload: dict = None, severity: str = "info") -> int:
        """Append one event. Returns the new row id."""
        if severity not in self.SEVERITY_LEVELS:
            severity = "info"
        ts = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload or {})
        with self._lock:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO mesh_events (timestamp, event_type, node, payload, severity) VALUES (?,?,?,?,?)",
                    (ts, event_type, node, payload_str, severity),
                )
                conn.commit()
                return cur.lastrowid

    def query(
        self,
        limit: int = 100,
        event_type: str = None,
        node: str = None,
        severity: str = None,
        since: str = None,   # ISO timestamp string
        until: str = None,   # ISO timestamp string
    ) -> list[dict]:
        """Query events with optional filters. Returns list of dicts, newest first."""
        clauses = []
        params = []

        if event_type:
            # Support prefix matching: "node:" matches "node:error", "node:online", etc.
            if event_type.endswith(":"):
                clauses.append("event_type LIKE ?")
                params.append(event_type + "%")
            else:
                clauses.append("event_type = ?")
                params.append(event_type)
        if node:
            clauses.append("node = ?")
            params.append(node)
        if severity:
            clauses.append("severity = ?")
            params.append(severity)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)
        if until:
            clauses.append("timestamp <= ?")
            params.append(until)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        limit = min(max(1, int(limit)), 1000)

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM mesh_events {where} ORDER BY id DESC LIMIT ?",
                params + [limit],
            ).fetchall()

        return [
            {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "ts": datetime.fromisoformat(r["timestamp"]).timestamp(),  # Unix float for leaderboard
                "event_type": r["event_type"],
                "node": r["node"],
                "payload": json.loads(r["payload"]),
                "severity": r["severity"],
            }
            for r in rows
        ]

    def stats(self) -> dict:
        """Quick summary stats."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM mesh_events").fetchone()[0]
            by_node = {
                r[0]: r[1]
                for r in conn.execute(
                    "SELECT node, COUNT(*) FROM mesh_events GROUP BY node"
                ).fetchall()
            }
            by_severity = {
                r[0]: r[1]
                for r in conn.execute(
                    "SELECT severity, COUNT(*) FROM mesh_events GROUP BY severity"
                ).fetchall()
            }
        return {"total": total, "by_node": by_node, "by_severity": by_severity}

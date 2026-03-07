"""
memory_query.py -- Freya's LanceDB memory interface.
Freya is the mesh memory master: all nodes proxy /memory-query and
/memory-sync through her.

Provides:
  MemoryQueryHandler(base_dir)
    .query(q, node, limit)   -- semantic search via embedding
    .upsert(body)            -- write/update a memory record
    .info()                  -- table stats
"""

import json
import logging
import os
import time
import urllib.request
from pathlib import Path

log = logging.getLogger("bifrost.memory")

_OLLAMA_BASE  = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
_EMBED_MODEL  = os.environ.get("EMBED_MODEL", "nomic-embed-text")
_DB_NAME      = "memory"
_TABLE_NAME   = "memories"
_VECTOR_DIM   = 768


def _embed(text: str) -> list[float] | None:
    """Get embedding from Ollama. Returns None on any failure."""
    try:
        payload = json.dumps({"model": _EMBED_MODEL, "prompt": text[:2000]}).encode()
        req = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            emb = data.get("embedding", [])
            return emb if len(emb) == _VECTOR_DIM else None
    except Exception as e:
        log.debug("Embed failed: %s", e)
        return None


class MemoryQueryHandler:
    def __init__(self, base_dir: Path):
        self._db_path = Path(base_dir) / "memory.db"
        self._db  = None
        self._tbl = None
        self._connect()

    def _connect(self):
        try:
            import lancedb
            self._db  = lancedb.connect(str(self._db_path))
            tables = self._db.table_names()
            if _TABLE_NAME in tables:
                self._tbl = self._db.open_table(_TABLE_NAME)
                log.info("[memory_query] Connected to '%s' (%d rows)", _TABLE_NAME, self._tbl.count_rows())
            else:
                self._tbl = None
                log.info("[memory_query] Table '%s' not found yet (empty DB)", _TABLE_NAME)
        except Exception as e:
            log.warning("[memory_query] LanceDB connect failed: %s", e)
            self._db = self._tbl = None

    def _get_table(self):
        """Lazy reconnect if table was created after startup."""
        if self._tbl is not None:
            return self._tbl
        if self._db is not None:
            tables = self._db.table_names()
            if _TABLE_NAME in tables:
                self._tbl = self._db.open_table(_TABLE_NAME)
        return self._tbl

    def query(self, q: str, node: str = None, limit: int = 10) -> list[dict]:
        """Semantic search. Falls back to full-table scan if Ollama down."""
        tbl = self._get_table()
        if tbl is None:
            return []
        try:
            emb = _embed(q)
            if emb:
                results = tbl.search(emb).limit(limit).to_list()
            else:
                # Fallback: text filter
                results = tbl.search().limit(limit * 3).to_list()
                if q:
                    q_low = q.lower()
                    results = [r for r in results if q_low in str(r.get("text", "")).lower()][:limit]
            # Apply node filter
            if node:
                results = [r for r in results if r.get("node") == node]
            # Clean up non-serializable fields
            out = []
            for r in results:
                row = {k: v for k, v in r.items() if k != "vector" and not isinstance(v, bytes)}
                out.append(row)
            return out
        except Exception as e:
            log.error("[memory_query] query error: %s", e)
            return []

    def upsert(self, body: dict) -> dict:
        """Write or update a memory record. Auto-embeds the text field."""
        if self._db is None:
            return {"error": "LanceDB not connected"}
        try:
            import lancedb
            import pyarrow as pa

            text  = body.get("text", "")
            node  = body.get("node", "unknown")
            tags  = body.get("tags", [])
            ts    = body.get("timestamp", time.time())
            mem_id = body.get("id", f"mem-{int(ts*1000)}")

            emb = _embed(text) or [0.0] * _VECTOR_DIM

            row = {
                "id":        mem_id,
                "text":      text,
                "node":      node,
                "tags":      json.dumps(tags),
                "timestamp": float(ts),
                "vector":    emb,
            }

            tbl = self._get_table()
            if tbl is None:
                # Create table on first write
                schema = pa.schema([
                    pa.field("id",        pa.utf8()),
                    pa.field("text",      pa.utf8()),
                    pa.field("node",      pa.utf8()),
                    pa.field("tags",      pa.utf8()),
                    pa.field("timestamp", pa.float64()),
                    pa.field("vector",    pa.list_(pa.float32(), _VECTOR_DIM)),
                ])
                self._tbl = self._db.create_table(_TABLE_NAME, schema=schema)
                tbl = self._tbl
                log.info("[memory_query] Created table '%s'", _TABLE_NAME)

            # Delete existing row with same id (upsert)
            try:
                tbl.delete(f"id = '{mem_id}'")
            except Exception:
                pass
            tbl.add([row])
            log.info("[memory_query] Upserted memory %s (%s)", mem_id, node)
            return {"status": "ok", "id": mem_id, "node": node}
        except Exception as e:
            log.error("[memory_query] upsert error: %s", e)
            return {"error": str(e)}

    def info(self) -> dict:
        tbl = self._get_table()
        if tbl is None:
            return {"status": "empty", "table": _TABLE_NAME, "rows": 0, "db": str(self._db_path)}
        try:
            count = tbl.count_rows()
            nodes = {}
            for row in tbl.search().limit(1000).to_list():
                n = row.get("node", "unknown")
                nodes[n] = nodes.get(n, 0) + 1
            return {
                "status": "ok",
                "table":  _TABLE_NAME,
                "rows":   count,
                "nodes":  nodes,
                "db":     str(self._db_path),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

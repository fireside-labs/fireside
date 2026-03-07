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
_TABLE_NAME   = "mesh_memories"   # actual table name in memory.db
_VECTOR_DIM   = 768
_EMBED_FIELD  = "embedding"       # vector column name


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
            available = self._db.table_names()
            if _TABLE_NAME in available:
                self._tbl = self._db.open_table(_TABLE_NAME)
                log.info("[memory_query] Connected to '%s' (%d rows)", _TABLE_NAME, self._tbl.count_rows())
            else:
                self._tbl = None
                log.info("[memory_query] Table '%s' not found — available: %s", _TABLE_NAME, available)
        except Exception as e:
            log.warning("[memory_query] LanceDB connect failed: %s", e)
            self._db = self._tbl = None

    def _get_table(self):
        """Lazy reconnect if table was created after startup."""
        if self._tbl is not None:
            return self._tbl
        if self._db is not None:
            if _TABLE_NAME in self._db.table_names():
                self._tbl = self._db.open_table(_TABLE_NAME)
        return self._tbl

    def query(self, q: str, node: str = None, limit: int = 10) -> list[dict]:
        """Semantic search over mesh_memories. Falls back to text scan if Ollama down."""
        tbl = self._get_table()
        if tbl is None:
            return []
        try:
            emb = _embed(q)
            if emb:
                results = tbl.search(emb, vector_column_name=_EMBED_FIELD).limit(limit).to_list()
            else:
                # Fallback: text filter on 'content' field
                results = tbl.search().limit(limit * 5).to_list()
                if q:
                    q_low = q.lower()
                    results = [r for r in results
                               if q_low in str(r.get("content", "")).lower()][:limit]
            # Apply node/agent filter
            if node:
                results = [r for r in results
                           if r.get("node") == node or r.get("agent") == node]
            # Serialize cleanly
            out = []
            for r in results:
                row = {}
                for k, v in r.items():
                    if k == _EMBED_FIELD:
                        continue
                    if isinstance(v, (list, dict, str, int, float, bool, type(None))):
                        row[k] = v
                    else:
                        row[k] = str(v)
                out.append(row)
            return out
        except Exception as e:
            log.error("[memory_query] query error: %s", e)
            return []

    def upsert(self, body: dict) -> dict:
        """Write or update a memory record. Schema matches mesh_memories table."""
        if self._db is None:
            return {"error": "LanceDB not connected"}
        try:
            import pyarrow as pa

            content   = body.get("content", body.get("text", ""))
            node      = body.get("node", "unknown")
            agent     = body.get("agent", node)
            tags      = body.get("tags", [])
            ts        = int(body.get("ts", body.get("timestamp", time.time())))
            importance = float(body.get("importance", 0.5))
            valence    = float(body.get("valence", 0.0))
            shared     = bool(body.get("shared", False))
            permanent  = bool(body.get("permanent", False))
            mem_id     = body.get("memory_id", body.get("id", f"mem-{ts}"))

            emb = _embed(content) or [0.0] * _VECTOR_DIM

            row = {
                "memory_id":  mem_id,
                "node":       node,
                "agent":      agent,
                "content":    content,
                "embedding":  emb,
                "tags":       tags if isinstance(tags, list) else [tags],
                "importance": importance,
                "ts":         ts,
                "shared":     shared,
                "permanent":  permanent,
                "valence":    valence,
            }

            tbl = self._get_table()
            if tbl is None:
                # Create table matching mesh_memories schema
                schema = pa.schema([
                    pa.field("memory_id",  pa.utf8()),
                    pa.field("node",       pa.utf8()),
                    pa.field("agent",      pa.utf8()),
                    pa.field("content",    pa.utf8()),
                    pa.field("embedding",  pa.list_(pa.float32(), _VECTOR_DIM)),
                    pa.field("tags",       pa.list_(pa.utf8())),
                    pa.field("importance", pa.float32()),
                    pa.field("ts",         pa.int64()),
                    pa.field("shared",     pa.bool_()),
                    pa.field("permanent",  pa.bool_()),
                    pa.field("valence",    pa.float32()),
                ])
                self._tbl = self._db.create_table(_TABLE_NAME, schema=schema)
                tbl = self._tbl
                log.info("[memory_query] Created table '%s'", _TABLE_NAME)

            try:
                tbl.delete(f"memory_id = '{mem_id}'")
            except Exception:
                pass
            tbl.add([row])
            log.info("[memory_query] Upserted memory %s (%s)", mem_id, node)
            return {"status": "ok", "memory_id": mem_id, "node": node}
        except Exception as e:
            log.error("[memory_query] upsert error: %s", e)
            return {"error": str(e)}

    def info(self) -> dict:
        tbl = self._get_table()
        if tbl is None:
            all_tables = self._db.table_names() if self._db else []
            return {"status": "not_found", "table": _TABLE_NAME, "available": all_tables, "db": str(self._db_path)}
        try:
            count = tbl.count_rows()
            nodes = {}
            agents = {}
            for row in tbl.search().limit(1000).to_list():
                n = row.get("node", "unknown")
                a = row.get("agent", "unknown")
                nodes[n]  = nodes.get(n, 0) + 1
                agents[a] = agents.get(a, 0) + 1
            return {
                "status":  "ok",
                "table":   _TABLE_NAME,
                "rows":    count,
                "nodes":   nodes,
                "agents":  agents,
                "db":      str(self._db_path),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

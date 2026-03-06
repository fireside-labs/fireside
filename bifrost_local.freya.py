"""
bifrost_local.py — Freya's node-specific route extensions.
Freya is the memory_master: she hosts the canonical LanceDB and handles
all /memory-sync writes and /memory-query reads for the mesh.

This file is NEVER overwritten by Odin's pushes.
Loaded automatically by _load_local_extensions() at Bifrost startup.
"""

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger("bifrost")
BASE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Bootstrap — add local dir to path so we can import memory_query etc.
# ---------------------------------------------------------------------------
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))


def register_routes(handler_class, config):
    """Called by bifrost._load_local_extensions() at startup."""
    _wire_memory(handler_class)
    log.info("[bifrost_local] Freya extensions registered: /memory-sync /memory-query /memory-info")


def _wire_memory(handler_class):
    """Inject memory routes into BifrostHandler."""
    try:
        from war_room.memory_query import MemoryQueryHandler  # type: ignore
        _mq = MemoryQueryHandler(BASE)
    except Exception as e:
        log.warning("[bifrost_local] MemoryQueryHandler unavailable (%s) — using fallback", e)
        _mq = None

    original_do_get  = handler_class.do_GET
    original_do_post = handler_class.do_POST

    def do_GET_extended(self):
        if self.path.startswith("/memory-query"):
            _handle_memory_query(self, _mq)
        elif self.path.startswith("/memory-info"):
            _handle_memory_info(self, _mq)
        else:
            # Call _do_GET_inner directly so new routes added to bifrost.py
            # are always picked up (not frozen to a captured function reference)
            if hasattr(self, '_do_GET_inner'):
                self._do_GET_inner()
            else:
                original_do_get(self)  # fallback for older bifrost versions

    def do_POST_extended(self):
        if self.path == "/memory-sync":
            _handle_memory_write(self, _mq)
        else:
            original_do_post(self)

    handler_class.do_GET  = do_GET_extended
    handler_class.do_POST = do_POST_extended
    log.info("[bifrost_local] Memory routes injected")


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def _handle_memory_query(handler, mq):
    from urllib.parse import urlparse, parse_qs
    params = parse_qs(urlparse(handler.path).query)

    def p(k, d=None):
        v = params.get(k)
        return v[0] if v else d

    try:
        if mq is None:
            raise RuntimeError("MemoryQueryHandler not loaded")
        results = mq.query(
            q=p("q", ""),
            node=p("node"),
            limit=int(p("limit", 10)),
        )
        _json_respond(handler, 200, {"results": results, "count": len(results)})
    except Exception as e:
        log.error("[bifrost_local] /memory-query error: %s", e)
        _json_respond(handler, 500, {"error": str(e)})


def _handle_memory_info(handler, mq):
    try:
        if mq is None:
            raise RuntimeError("MemoryQueryHandler not loaded")
        info = mq.info()
        _json_respond(handler, 200, info)
    except Exception as e:
        _json_respond(handler, 500, {"error": str(e)})


def _handle_memory_write(handler, mq):
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body   = json.loads(handler.rfile.read(length))
        if mq is None:
            raise RuntimeError("MemoryQueryHandler not loaded")
        result = mq.upsert(body)
        _json_respond(handler, 200, result)
    except Exception as e:
        log.error("[bifrost_local] /memory-sync error: %s", e)
        _json_respond(handler, 500, {"error": str(e)})


def _json_respond(handler, code, data):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(body)

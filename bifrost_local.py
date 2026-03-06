"""
bifrost_local.py — Freya's permanent local route extensions.

This file is NEVER pushed or overwritten by Odin. It registers Freya's
node-specific HTTP routes into BifrostHandler at startup via register_routes().

Routes added:
  GET  /circuit-status     — circuit breaker state for all nodes
  GET  /memory-info        — LanceDB memory system status
  GET  /memory-query       — semantic search: ?q=<text>&limit=10&tags=x,y
  POST /memory-sync        — upsert memories from Thor's sync push
  POST /explain            — explain a workspace file/snippet via Kimi
"""

import logging

log = logging.getLogger("bifrost.local")

# ---------------------------------------------------------------------------
# Module-level flag: did our imports succeed?
# ---------------------------------------------------------------------------

try:
    from war_room import memory_query as _mq
    _MEMORY_OK = True
except ImportError as e:
    _mq = None
    _MEMORY_OK = False
    log.warning("bifrost_local: memory_query unavailable: %s", e)

try:
    from war_room.explain import ExplainHandler as _ExplainHandler
    _EXPLAIN_CLS = _ExplainHandler
    _EXPLAIN_OK = True
except ImportError as e:
    _ExplainHandler = None
    _EXPLAIN_CLS = None
    _EXPLAIN_OK = False
    log.warning("bifrost_local: explain unavailable: %s", e)

try:
    from war_room.circuit import CircuitBreakerRegistry as _CBRegistry
    _CIRCUIT_OK = True
except ImportError as e:
    _CBRegistry = None
    _CIRCUIT_OK = False
    log.warning("bifrost_local: circuit unavailable: %s", e)

try:
    from war_room import pheromone as _pheromone
    _PHEROMONE_OK = True
except ImportError as e:
    _pheromone = None
    _PHEROMONE_OK = False
    log.warning("bifrost_local: pheromone unavailable: %s", e)

try:
    from war_room import mycelium as _mycelium
    _MYCELIUM_OK = True
except ImportError as e:
    _mycelium = None
    _MYCELIUM_OK = False
    log.warning("bifrost_local: mycelium unavailable: %s", e)

try:
    from war_room import metabolic as _metabolic
    _METABOLIC_OK = True
except ImportError as e:
    _metabolic = None
    _METABOLIC_OK = False
    log.warning("bifrost_local: metabolic unavailable: %s", e)

try:
    from war_room import attention as _attention
    _ATTENTION_OK = True
except ImportError as e:
    _attention = None
    _ATTENTION_OK = False
    log.warning("bifrost_local: attention unavailable: %s", e)

try:
    from war_room import dream_journal as _dj
    _DJ_OK = True
except ImportError as e:
    _dj = None
    _DJ_OK = False
    log.warning("bifrost_local: dream_journal unavailable: %s", e)

try:
    from war_room import plasticity as _plasticity
    _PLASTICITY_OK = True
except ImportError as e:
    _plasticity = None
    _PLASTICITY_OK = False
    log.warning("bifrost_local: plasticity unavailable: %s", e)

try:
    from war_room import confidence as _confidence
    _CONFIDENCE_OK = True
except ImportError as e:
    _confidence = None
    _CONFIDENCE_OK = False
    log.warning("bifrost_local: confidence unavailable: %s", e)

try:
    from war_room import skills as _skills
    _SKILLS_OK = True
except ImportError as e:
    _skills = None
    _SKILLS_OK = False
    log.warning("bifrost_local: skills unavailable: %s", e)

# Singletons — set once in register_routes()
_explain = None
_cb = None


# ---------------------------------------------------------------------------
# register_routes — called by Bifrost at startup
# ---------------------------------------------------------------------------

def register_routes(handler_class, config):
    """Inject Freya's local routes into BifrostHandler.

    Called once at startup from _load_local_extensions() in bifrost.py.
    We wrap the existing do_GET and do_POST methods to prepend our routes.
    """
    global _explain, _cb

    nodes = config.get("nodes", {})
    agent_cfg = config.get("agent", {})

    # Instantiate handlers
    if _EXPLAIN_OK:
        try:
            from pathlib import Path
            import os
            _ws = Path(os.environ.get("USERPROFILE", "C:/Users/Jorda")) / ".openclaw" / "workspace"
            _explain = _EXPLAIN_CLS(agent_cfg, _ws)
            log.info("bifrost_local: explain handler ready")
        except Exception as e:
            log.error("bifrost_local: explain init failed: %s", e)

    if _CIRCUIT_OK:
        try:
            _cb = _CBRegistry(nodes)
            log.info("bifrost_local: circuit breaker ready (%d nodes)", len(nodes))
        except Exception as e:
            log.error("bifrost_local: circuit init failed: %s", e)

    if _MEMORY_OK:
        log.info("bifrost_local: memory_query ready")

    # Start mycelium self-healing daemon
    if _MYCELIUM_OK:
        try:
            _mycelium.start(nodes)
        except Exception as e:
            log.error("bifrost_local: mycelium start failed: %s", e)

    # Slime mold: patch the live HookEngine to drop collaboration path pheromones
    # task:complete → reliable pheromone on agent path
    # node:error    → danger pheromone on agent path
    if _PHEROMONE_OK:
        import sys
        _bifrost = sys.modules.get("__main__")
        if _bifrost and hasattr(_bifrost, "_hooks"):
            _orig_emit = _bifrost._hooks.emit
            def _patched_emit(event, payload, source_node=None):
                import threading
                _orig_emit(event, payload, source_node or "")
                # === METABOLIC: count every hook event ===
                if _METABOLIC_OK:
                    _metabolic.record_hook_event()
                    if event == "task:complete":
                        _metabolic.record_task_complete()
                if not _PHEROMONE_OK:
                    return
                def _drop_path():
                    try:
                        node_a = source_node or payload.get("node", "?")
                        node_b = payload.get("to") or payload.get("target") or "mesh"
                        path   = f"{node_a}->{node_b}"
                        if event == "task:complete":
                            detail = payload.get("detail") or payload.get("summary") or ""
                            _pheromone.drop(
                                resource  = path,
                                pheromone_type = "reliable",
                                intensity = 0.6,
                                dropped_by = node_a,
                                reason = f"task:complete — {detail[:80]}"
                            )
                            log.debug("[slime] reliable on %s", path)
                        elif event in ("node:error", "sync:failed", "model:fallback"):
                            error = (payload.get("error") or
                                     payload.get("reason") or event)
                            _pheromone.drop(
                                resource  = path,
                                pheromone_type = "danger",
                                intensity = 0.5,
                                dropped_by = node_a,
                                reason = f"{event} — {str(error)[:80]}"
                            )
                            log.debug("[slime] danger on %s", path)
                        elif event == "ask:success":
                            detail = payload.get("model") or payload.get("detail") or ""
                            _pheromone.drop(
                                resource  = path,
                                pheromone_type = "reliable",
                                intensity = 0.5,
                                dropped_by = node_a,
                                reason = f"ask:success — {str(detail)[:60]}"
                            )
                            log.debug("[slime] reliable on %s (ask)", path)
                        elif event in ("ask:error", "model:error", "inference:failed"):
                            error = payload.get("error") or payload.get("reason") or event
                            _pheromone.drop(
                                resource  = path,
                                pheromone_type = "danger",
                                intensity = 0.7,
                                dropped_by = node_a,
                                reason = f"{event} — {str(error)[:60]}"
                            )
                            log.debug("[slime] danger on %s (ask failure)", path)

                    except Exception as ex:
                        log.debug("[slime] pheromone drop error: %s", ex)
                threading.Thread(target=_drop_path, daemon=True).start()
            _bifrost._hooks.emit = _patched_emit
            log.info("bifrost_local: slime mold HookEngine patch applied")
        else:
            log.info("bifrost_local: _hooks not found — slime mold will activate on next restart")

    # Patch do_GET
    _orig_get = handler_class.do_GET

    def do_GET(self):
        if self.path == "/circuit-status":
            if _cb:
                self._respond(200, {
                    "nodes": _cb.status_all(),
                    "tripped": _cb.tripped_nodes(),
                })
            else:
                self._respond(503, {"error": "circuit breaker not available"})
        elif self.path == "/memory-info" and _MEMORY_OK:
            self._respond(200, _mq.info())
        elif self.path == "/memory-health" and _MEMORY_OK:
            code, data = _mq.handle_health()
            self._respond(code, data)
        elif self.path.startswith("/memory-query") and _MEMORY_OK:
            # Record query for attention gradient BEFORE responding
            if _ATTENTION_OK:
                import urllib.parse as _up
                qs = _up.parse_qs(_up.urlparse(self.path).query)
                q_text = (qs.get("q") or [""])[0]
                _attention.record_query(q_text)
            code, data = _mq.handle_query(self.path)
            self._respond(code, data)
        elif self.path.startswith("/pheromone") and _PHEROMONE_OK:
            code, data = _pheromone.handle_smell(self.path)
            self._respond(code, data)
        elif self.path == "/mycelium" and _MYCELIUM_OK:
            self._respond(200, _mycelium.status())
        elif self.path == "/metabolic-rate" and _METABOLIC_OK:
            self._respond(200, _metabolic.get_rate())
        elif self.path == "/attention" and _ATTENTION_OK:
            self._respond(200, _attention.get_attention())
        elif self.path.startswith("/dream-journal") and _DJ_OK:
            import urllib.parse as _up
            qs  = _up.parse_qs(_up.urlparse(self.path).query)
            lim = int((qs.get("limit") or ["20"])[0])
            ev  = (qs.get("event") or [""])[0]
            self._respond(200, _dj.get_journal(limit=lim, event_filter=ev))
        elif self.path == "/plasticity" and _PLASTICITY_OK:
            self._respond(200, _plasticity.get_plasticity())
        elif self.path == "/confidence" and _CONFIDENCE_OK:
            self._respond(200, _confidence.get_confidence())
        elif self.path.startswith("/skills") and _SKILLS_OK:
            import urllib.parse as _up2
            _cat = _up2.parse_qs(_up2.urlparse(self.path).query).get("category", [""])[0]
            self._respond(200, _skills.get_skills(category=_cat))
        else:
            _orig_get(self)

    handler_class.do_GET = do_GET

    # Patch do_POST — add our routes to the allowlist then handle them
    _orig_post = handler_class.do_POST

    def do_POST(self):
        if self.path in ("/memory-sync", "/explain", "/pheromone"):
            import json
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            except Exception:
                self._respond(400, {"error": "invalid JSON"}); return

            if self.path == "/memory-sync" and _MEMORY_OK:
                code, data = _mq.handle_upsert(body)
                if isinstance(data, dict) and code == 200:
                    written   = data.get("upserted", 0)
                    permanent = data.get("permanent", 0)
                    total     = data.get("total", 0)
                    if _METABOLIC_OK:
                        _metabolic.record_memory_write(written)
                    if _DJ_OK:
                        _dj.record_consolidation(written, permanent, total)
                        # Journal any permanent/high-importance memories individually
                        for mem in body.get("memories", []):
                            imp = float(mem.get("importance", 0))
                            perm = bool(mem.get("permanent", False))
                            if perm or imp >= 0.85:
                                _dj.record_milestone(
                                    content    = mem.get("content", ""),
                                    importance = imp,
                                    permanent  = perm,
                                )
                self._respond(code, data)
            elif self.path == "/explain" and _explain:
                code, data = _explain.handle(body)
                self._respond(code, data)
            elif self.path == "/pheromone" and _PHEROMONE_OK:
                code, data = _pheromone.handle_drop(body)
                self._respond(code, data)
            else:
                self._respond(503, {"error": "module not available"})
        else:
            # Intercept /ask to drop pheromones on success/failure
            if self.path == "/ask" and (_PHEROMONE_OK or _METABOLIC_OK):
                import io as _io, json as _json
                _ask_node  = "?"
                _ask_model = "?"
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body_bytes = self.rfile.read(length) if length else b"{}"
                    # Re-inject so _orig_post can re-read the body
                    self.rfile = _io.BytesIO(body_bytes)
                    try:
                        _ask_body  = _json.loads(body_bytes)
                        _ask_node  = (_ask_body.get("node") or
                                      _ask_body.get("source_node") or
                                      _ask_body.get("from") or "mesh")
                        _ask_model = _ask_body.get("model") or "default"
                    except Exception:
                        pass
                    _orig_post(self)   # runs Bifrost's own /ask handler
                    # ---------- SUCCESS ----------
                    if _METABOLIC_OK:
                        _metabolic.record_ask()
                    if _PHEROMONE_OK:
                        _path = f"{_ask_node}->/ask"
                        _pheromone.drop(
                            resource       = _path,
                            pheromone_type = "reliable",
                            intensity      = 0.5,
                            dropped_by     = _ask_node,
                            reason         = f"ask served ({_ask_model})"
                        )
                        log.debug("[slime] reliable on %s (ask success)", _path)
                except Exception as _ex:
                    # ---------- FAILURE ----------
                    if _PHEROMONE_OK:
                        _path = f"{_ask_node}->/ask"
                        _pheromone.drop(
                            resource       = _path,
                            pheromone_type = "danger",
                            intensity      = 0.7,
                            dropped_by     = _ask_node,
                            reason         = f"ask failed — {str(_ex)[:60]}"
                        )
                        log.debug("[slime] danger on %s (ask failed: %s)", _path, _ex)
            else:
                _orig_post(self)

    handler_class.do_POST = do_POST

    log.info("bifrost_local: routes registered (circuit=%s memory=%s explain=%s pheromone=%s mycelium=%s)",
             _CIRCUIT_OK, _MEMORY_OK, _EXPLAIN_OK, _PHEROMONE_OK, _MYCELIUM_OK)

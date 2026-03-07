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

try:
    from war_room import pheromone_chains as _chains
    _CHAINS_OK = True
except ImportError as e:
    _chains = None
    _CHAINS_OK = False
    log.warning("bifrost_local: pheromone_chains unavailable: %s", e)

try:
    from war_room import shared_state as _ss
    _SS_OK = True
except ImportError as e:
    _ss = None
    _SS_OK = False
    log.warning("bifrost_local: shared_state unavailable: %s", e)

try:
    from war_room import phylactery as _phylactery
    _PHYLACTERY_OK = True
except ImportError as e:
    _phylactery = None
    _PHYLACTERY_OK = False
    log.warning("bifrost_local: phylactery unavailable: %s", e)

try:
    from war_room import save_point as _save_point
    _SAVEPOINT_OK = True
except ImportError as e:
    _save_point = None
    _SAVEPOINT_OK = False
    log.warning("bifrost_local: save_point unavailable: %s", e)

try:
    from war_room import procedures as _procedures
    _PROC_OK = True
except ImportError as e:
    _procedures = None
    _PROC_OK = False
    log.warning("bifrost_local: procedures unavailable: %s", e)

try:
    from war_room import hypotheses as _hyp
    _HYP_OK = True
except ImportError as e:
    _hyp = None
    _HYP_OK = False
    log.warning("bifrost_local: hypotheses unavailable: %s", e)

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

    # Dream daemon removed — dreaming is now explicit via POST /sleep

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
                            # Chain reaction
                            if _CHAINS_OK:
                                _chains.trigger_chain(_pheromone, path, "reliable", 0.6, node_a)
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
                            # Chain reaction
                            if _CHAINS_OK:
                                _chains.trigger_chain(_pheromone, path, "danger", 0.5, node_a)
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
        elif self.path.startswith("/shared-state") and _SS_OK:
            import urllib.parse as _up5
            _sk = _up5.parse_qs(_up5.urlparse(self.path).query).get("key", [""])[0]
            self._respond(200, _ss.get(key=_sk))
        elif self.path == "/phylactery" and _PHYLACTERY_OK:
            self._respond(200, _phylactery.get_soul_vectors())
        elif self.path == "/save-points" and _SAVEPOINT_OK:
            self._respond(200, {"bookmarks": _save_point.list_bookmarks(),
                                "current_seq": _save_point.current_seq()})
        elif self.path.startswith("/procedures") and _PROC_OK:
            import urllib.parse as _up6
            _qs  = _up6.parse_qs(_up6.urlparse(self.path).query)
            _tt  = _qs.get("task_type", [None])[0]
            _q   = _qs.get("q", [""])[0].strip() or None
            _lim = int((_qs.get("limit") or ["5"])[0])
            _lim = max(1, min(_lim, 50))
            _mc  = float((_qs.get("min_confidence") or ["0.0"])[0])
            self._respond(200, _procedures.get_procedures(
                task_type=_tt, q=_q, limit=_lim, min_confidence=_mc))
        elif self.path.startswith("/hypotheses") and _HYP_OK:
            import urllib.parse as _up8
            _hqs  = _up8.parse_qs(_up8.urlparse(self.path).query)
            _hlim = int((_hqs.get("limit") or ["10"])[0])
            _hlim = max(1, min(_hlim, 50))
            _hmc  = float((_hqs.get("min_confidence") or ["0.0"])[0])
            _ht_s = (_hqs.get("tested") or [None])[0]
            _ht   = (True if _ht_s == "true" else (False if _ht_s == "false" else None))
            self._respond(200, _hyp.get_hypotheses(limit=_hlim, min_confidence=_hmc, tested=_ht))
        elif self.path == "/plasticity" and _PLASTICITY_OK:
            self._respond(200, _plasticity.get_plasticity())
        elif self.path == "/confidence" and _CONFIDENCE_OK:
            self._respond(200, _confidence.get_confidence())
        elif self.path.startswith("/skills") and _SKILLS_OK:
            import urllib.parse as _up2
            _cat = _up2.parse_qs(_up2.urlparse(self.path).query).get("category", [""])[0]
            self._respond(200, _skills.get_skills(category=_cat))
        elif self.path == "/agent-docs":
            # Serve this node's own mesh/docs/<node>.md
            import pathlib as _pl, json as _js
            try:
                _cfg = _js.loads((_pl.Path(__file__).parent / "config.json").read_text())
            except Exception:
                _cfg = {}
            _node_name = _cfg.get("name", "freya").lower()
            _doc_path  = _pl.Path(__file__).parent / "mesh" / "docs" / f"{_node_name}.md"
            if _doc_path.exists():
                _md = _doc_path.read_text(encoding="utf-8")
                self._respond(200, {"node": _node_name, "format": "markdown", "content": _md})
            else:
                self._respond(404, {"error": f"No doc found at {_doc_path}"})
        elif self.path.startswith("/mesh-docs"):
            # Fetch another node's /agent-docs: GET /mesh-docs?node=heimdall
            import urllib.parse as _up4, urllib.request as _ur, json as _js, pathlib as _pl
            _peer = _up4.parse_qs(_up4.urlparse(self.path).query).get("node", [""])[0]
            try:
                _cfg = _js.loads((_pl.Path(__file__).parent / "config.json").read_text())
            except Exception:
                _cfg = {}
            _nodes_cfg = _cfg.get("nodes", {})
            _peer_cfg  = _nodes_cfg.get(_peer, {})
            if not _peer_cfg:
                self._respond(404, {"error": f"Unknown peer node: {_peer}"})
            else:
                _peer_url = f"http://{_peer_cfg['ip']}:{_peer_cfg.get('port', 8765)}/agent-docs"
                try:
                    _doc = _js.loads(_ur.urlopen(_peer_url, timeout=10).read())
                    self._respond(200, _doc)
                except Exception as _e:
                    self._respond(503, {"error": f"Could not reach {_peer}: {_e}"})


        elif self.path.startswith("/memory-provenance") and _MEMORY_OK:
            import urllib.parse as _up3
            _mid = _up3.parse_qs(_up3.urlparse(self.path).query).get("id", [""])[0]
            if not _mid:
                self._respond(400, {"error": "id parameter required"})
            else:
                # Search for memories that contain derived_from:<id> or reference it in tags
                _tag = f"derived_from:{_mid}"
                _res = _mq.query_memories(_tag, limit=20)
                _derived = [m for m in _res.get("memories", [])
                            if any(_mid in str(t) for t in (m.get("tags") or []))
                            or _tag in m.get("content", "")]
                self._respond(200, {
                    "source_id":   _mid,
                    "derived":     _derived,
                    "total":       len(_derived),
                })
        else:
            _orig_get(self)

    handler_class.do_GET = do_GET

    # Patch do_POST — add our routes to the allowlist then handle them
    _orig_post = handler_class.do_POST

    def do_POST(self):
        if self.path in ("/memory-sync", "/explain", "/pheromone",
                          "/shared-state-sync", "/save-point", "/rollback",
                          "/procedure", "/procedures",
                          "/hypotheses/generate", "/hypotheses/test",
                          "/sleep"):
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
            elif self.path == "/shared-state-sync" and _SS_OK:
                # Receive Heimdall's broadcast — LWW by ts
                _from = body.get("from", "unknown")
                _key  = body.get("key", "")
                _entry = body.get("entry", {})
                self._respond(200, _ss.receive(_key, _entry, _from))
            elif self.path == "/save-point" and _SAVEPOINT_OK:
                label = body.get("label", "")
                self._respond(200, _save_point.create(label=label))
            elif self.path == "/rollback" and _SAVEPOINT_OK:
                to_seq = int(body.get("to_seq", 0))
                if to_seq <= 0:
                    self._respond(400, {"error": "to_seq must be > 0"})
                else:
                    self._respond(200, _save_point.rollback(to_seq))
            elif self.path == "/procedure" and _PROC_OK:
                result = _procedures.upsert_procedure(
                    task_type  = body.get("task_type", ""),
                    approach   = body.get("approach", ""),
                    outcome    = body.get("outcome", "success"),
                    confidence = float(body.get("confidence", 0.8)),
                    tags       = body.get("tags", []),
                    proc_id    = body.get("id"),
                    permanent  = bool(body.get("permanent", True)),
                )
                code = 200 if result.get("ok") else 400
                self._respond(code, result)
            elif self.path == "/procedures" and _PROC_OK:
                procs = body.get("procedures", [])
                if not isinstance(procs, list):
                    self._respond(400, {"error": "procedures must be a list"})
                else:
                    result = _procedures.upsert_batch(procs)
                    self._respond(200, result)
            elif self.path == "/hypotheses/generate" and _HYP_OK:
                result = _hyp.run_dream_cycle()
                self._respond(200, result)
            elif self.path == "/hypotheses/test" and _HYP_OK:
                hid   = body.get("id", "")
                hres  = body.get("result", "")
                hdelta= float(body.get("confidence_delta", 0.1))
                if not hid or not hres:
                    self._respond(400, {"error": "id and result required"})
                else:
                    result = _hyp.test_hypothesis(hid, hres, hdelta)
                    code = 200 if result.get("ok") else 400
                    self._respond(code, result)
            elif self.path == "/sleep" and _HYP_OK:
                # Support ?seed=... from query string or body
                import urllib.parse
                parsed = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed.query)
                seed = body.get("seed") or (qs.get("seed")[0] if qs.get("seed") else None)
                result = _hyp.sleep(seed=seed)
                self._respond(200, result)
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
            elif self.path == "/war-room/task" and _SAVEPOINT_OK:
                # Intercept to auto-save-point on high_risk=true tasks
                import io as _io2, json as _json2
                try:
                    length2 = int(self.headers.get("Content-Length", 0))
                    body_bytes2 = self.rfile.read(length2) if length2 else b"{}"
                    self.rfile = _io2.BytesIO(body_bytes2)
                    try:
                        _task_body = _json2.loads(body_bytes2)
                        if _task_body.get("high_risk"):
                            _task_title = _task_body.get("title", "high-risk-task")
                            _sp_label = f"before: {_task_title[:40]}"
                            _sp_result = _save_point.create(label=_sp_label)
                            log.info("[save_point] auto-save for high_risk task: %s → seq=%d",
                                     _task_title, _sp_result.get("seq", 0))
                    except Exception:
                        pass
                    _orig_post(self)  # let Bifrost process the task normally
                except Exception:
                    _orig_post(self)
            elif self.path == "/war-room/complete" and _PROC_OK:
                # Intercept to auto-record procedures on task completion
                import io as _io3, json as _json3
                try:
                    length3 = int(self.headers.get("Content-Length", 0))
                    body_bytes3 = self.rfile.read(length3) if length3 else b"{}"
                    self.rfile = _io3.BytesIO(body_bytes3)
                    try:
                        _comp = _json3.loads(body_bytes3)
                        _approach  = (_comp.get("approach") or "").strip()
                        _task_type = (_comp.get("task_type") or "").strip()
                        _outcome   = _comp.get("status", "completed")
                        if _approach and _task_type:
                            _procedures.auto_record(
                                task_type  = _task_type,
                                approach   = _approach,
                                outcome    = "success" if _outcome == "completed" else _outcome,
                                confidence = 0.8,
                                tags       = _comp.get("tags", []),
                            )
                            log.info("[auto_record] procedure captured: %s → %.40s",
                                     _task_type, _approach)
                    except Exception as _ar_ex:
                        log.debug("[auto_record] skip (non-critical): %s", _ar_ex)
                    _orig_post(self)
                except Exception:
                    _orig_post(self)
            else:
                _orig_post(self)

    handler_class.do_POST = do_POST

    # -----------------------------------------------------------------------
    # DELETE /procedure?id=proc_xxx  — remove a bad procedure
    # -----------------------------------------------------------------------
    _orig_delete = getattr(handler_class, "do_DELETE", None)

    def do_DELETE(self):
        if self.path.startswith("/procedure") and _PROC_OK:
            import urllib.parse as _up7
            _pid = _up7.parse_qs(_up7.urlparse(self.path).query).get("id", [None])[0]
            if not _pid:
                self._respond(400, {"error": "id parameter required"})
            else:
                result = _procedures.delete_procedure(_pid)
                code = 200 if result.get("ok") else (404 if "not found" in result.get("error","") else 400)
                self._respond(code, result)
        elif _orig_delete:
            _orig_delete(self)
        else:
            self._respond(405, {"error": "method not allowed"})

    handler_class.do_DELETE = do_DELETE

    log.info("bifrost_local: routes registered (circuit=%s memory=%s explain=%s pheromone=%s mycelium=%s)",
             _CIRCUIT_OK, _MEMORY_OK, _EXPLAIN_OK, _PHEROMONE_OK, _MYCELIUM_OK)

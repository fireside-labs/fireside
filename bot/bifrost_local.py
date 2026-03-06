"""
bifrost_local.py -- Thor's node-specific route extensions.
This file is NEVER overwritten by Odin's pushes.
Loaded automatically by _load_local_extensions() at Bifrost startup.

Routes registered here:
  GET  /event-log       -- Thor's mesh event log (survives all pushes)
  GET  /personality     -- Thor's current personality traits
  GET  /hydra-status    -- Current Hydra absorption state
  POST /route-message   -- Semantic router: embed message, return top-k agent targets
  POST /critique        -- Shadow critic: score ideas 0-1 before they enter the hive mind
  POST /snapshot        -- Generate + push Hydra state snapshot to memory-sync
  POST /absorb          -- Absorb a dead node's role from its saved snapshot
"""

import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

log = logging.getLogger("bifrost")
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

# ---------------------------------------------------------------------------
# Startup: initialise shared resources once
# ---------------------------------------------------------------------------
_router = None   # lazy-init on first /route-message call
_el     = None   # EventLog instance
_personality = None  # loaded once at session start
_hydra = None    # lazy-init: hydra module reference


def register_routes(handler_class, config):
    """Called by bifrost._load_local_extensions() at startup."""
    global _el, _personality
    # Load personality at session start so inference params are set immediately
    try:
        from personality import get_context  # type: ignore
        _personality = get_context()
        p = _personality
        log.info("[bifrost_local] Personality loaded — node=%s role=%s temp=%.2f top_p=%.2f",
                 p['traits']['node'], p['traits']['role'],
                 p['ollama_params']['temperature'], p['ollama_params']['top_p'])
    except Exception as e:
        log.warning("[bifrost_local] personality.py not available: %s", e)
        _personality = None
    _wire_event_log(handler_class, config)
    _wire_personality_route(handler_class, config)
    _wire_route_message(handler_class, config)
    _wire_critique(handler_class, config)
    _wire_hydra(handler_class, config)
    _wire_hardening(handler_class, config)
    _wire_watchdog_shutdown(handler_class, config)
    _wire_security(handler_class, config)
    _wire_agent_docs(handler_class, config)
    _wire_metrics_shared_state(handler_class, config)
    log.info("[bifrost_local] Thor extensions: /event-log, /personality, /route-message, "
             "/critique, /snapshot, /absorb, /hydra-status, /circuit-status, "
             "/reload-personality, /catch-up, /watchdog-status, /shutdown, /rate-limit-status")
    # Pin models in VRAM — runs in background so startup isn't blocked
    import threading
    ollama_base = config.get("ollama_base", "http://127.0.0.1:11434")
    threading.Thread(target=_warmup_models, args=(ollama_base,), daemon=True).start()
    # Start watchdog — auto-absorb dead peers
    _start_watchdog(config)
    # Init rate limiter
    try:
        import rate_limiter as _rl  # type: ignore
        _rl.init(config)
        log.info("[bifrost_local] Rate limiter initialized")
    except Exception as e:
        log.warning("[bifrost_local] Rate limiter unavailable: %s", e)


def _warmup_models(ollama_base: str = "http://127.0.0.1:11434"):
    """
    Keep qwen3.5:35b and nomic-embed-text pinned in VRAM.
    keep_alive=-1 means Ollama never unloads them.
    """
    import time
    time.sleep(5)   # let bifrost finish starting before hammering Ollama
    models = [
        ("qwen3.5:35b",        {"model": "qwen3.5:35b",        "prompt": ".", "keep_alive": -1, "stream": False}),
        ("nomic-embed-text",   {"model": "nomic-embed-text",   "prompt": ".", "keep_alive": -1}),
    ]
    for name, payload in models:
        endpoint = f"{ollama_base}/api/generate" if name != "nomic-embed-text" else f"{ollama_base}/api/embeddings"
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(endpoint, data=data,
                                         headers={"Content-Type": "application/json"},
                                         method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                r.read()
            log.info("[bifrost_local] Model pinned in VRAM: %s (keep_alive=-1)", name)
        except Exception as e:
            log.warning("[bifrost_local] Could not warm up %s: %s", name, e)


# ---------------------------------------------------------------------------
# GET /event-log  -- wired here so Odin's bifrost.py pushes never wipe it
# ---------------------------------------------------------------------------

def _wire_event_log(handler_class, config):
    global _el
    try:
        from event_log import EventLog  # type: ignore
        _el = EventLog(BASE / "mesh_events.db")
        original_do_get = handler_class.do_GET

        def do_GET_extended(self):
            if self.path.startswith("/event-log"):
                _handle_event_log(self, _el)
            elif self.path == "/personality":
                _handle_personality(self)
            else:
                original_do_get(self)

        handler_class.do_GET = do_GET_extended
        log.info("[bifrost_local] /event-log + /personality GET routes injected")
    except ImportError as e:
        log.error("[bifrost_local] Could not import event_log: %s", e)


def _wire_personality_route(handler_class, config):
    """No-op — /personality is already bolted onto do_GET inside _wire_event_log."""
    pass


def _handle_personality(handler):
    """GET /personality — return current traits and derived Ollama params."""
    if _personality:
        _json_respond(handler, 200, _personality)
    else:
        try:
            from personality import get_context  # type: ignore
            _json_respond(handler, 200, get_context())
        except Exception as e:
            _json_respond(handler, 503, {"error": f"personality not loaded: {e}"})


def _handle_event_log(handler, el):
    from urllib.parse import urlparse, parse_qs
    params = parse_qs(urlparse(handler.path).query)

    def p(key, default=None):
        v = params.get(key)
        return v[0] if v else default

    try:
        events = el.query(
            event_type=p("event_type") or p("type"),
            node=p("node"),
            severity=p("severity"),
            since=float(p("since")) if p("since") else None,
            until=float(p("until")) if p("until") else None,
            limit=int(p("limit", 1000)),
        )
        _json_respond(handler, 200, {"events": events, "count": len(events),
                                      "stats": el.stats()})
    except Exception as e:
        log.error("[bifrost_local] /event-log error: %s", e)
        _json_respond(handler, 500, {"error": str(e)})


# ---------------------------------------------------------------------------
# POST /route-message  -- semantic router
# ---------------------------------------------------------------------------

def _wire_route_message(handler_class, config):
    original_do_post = handler_class.do_POST

    def do_POST_extended(self):
        if self.path == "/route-message":
            _handle_route_message(self, config)
        else:
            original_do_post(self)

    handler_class.do_POST = do_POST_extended
    log.info("[bifrost_local] /route-message route injected")


def _get_router(config):
    global _router
    if _router is None:
        try:
            from router import Router  # type: ignore
            ollama_base = config.get("ollama_base", "http://127.0.0.1:11434")
            _router = Router(skills_dir=str(BASE), ollama_base=ollama_base)
            log.info("[bifrost_local] Router initialised with %d profiles",
                     len(_router.available_nodes()))
        except ImportError as e:
            log.error("[bifrost_local] Could not import router: %s", e)
    return _router


def _handle_route_message(handler, config):
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body = json.loads(handler.rfile.read(length)) if length else {}
    except Exception:
        _json_respond(handler, 400, {"error": "invalid JSON"}); return

    message = body.get("message") or body.get("body", "")
    if not message:
        _json_respond(handler, 400, {"error": "message or body field required"}); return

    top_k   = int(body.get("top_k", 2))
    exclude = body.get("exclude", [])

    router = _get_router(config)
    if not router:
        _json_respond(handler, 503, {"error": "router not available"}); return

    try:
        results = router.semantic_route(message, top_k=top_k, exclude=exclude)
        targets = [r["node"] for r in results]
        scores  = [r["similarity"] for r in results]
        _json_respond(handler, 200, {
            "targets":  targets,
            "scores":   scores,
            "details":  results,
            "method":   results[0]["method"] if results else "none",
            "top_k":    top_k,
        })
    except Exception as e:
        log.error("[bifrost_local] /route-message error: %s", e)
        _json_respond(handler, 500, {"error": str(e)})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_respond(handler, code: int, data: dict):
    body = json.dumps(data).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(body)


# ---------------------------------------------------------------------------
# POST /critique  -- Shadow Critic (Recursive Self-Correction)
# ---------------------------------------------------------------------------

# Message types that skip the critic entirely
_SKIP_TYPES = {"status", "note", "tattle", "heartbeat", "update", "info", "praise", "alert"}
_CRITIQUE_TYPES = {"idea", "proposal", "architecture", "design", "plan"}
_CRITIQUE_THRESHOLD = 0.6

# Multi-model critic: try fast model first, fall back to heavy model
_CRITIC_MODEL_FAST = "qwen2.5:7b"    # ~5GB VRAM — critic pass, faster
_CRITIC_MODEL_FULL = "qwen3.5:35b"   # ~26GB VRAM — fallback if 7b unavailable
_MAIN_MODEL        = "qwen3.5:35b"   # main inference model

# SHA256 critique result cache — avoid re-running inference on identical text
# {sha256_hex: {"result": {...}, "ts": float}}
import hashlib as _hashlib
_CRITIQUE_CACHE: dict = {}
_CRITIQUE_CACHE_TTL = 600   # seconds (10 minutes)

# Critique calibration stats
_CRITIQUE_STATS = {"total": 0, "passed": 0, "rejected": 0, "cached": 0,
                   "fast_model": 0, "full_model": 0, "skipped": 0}

_CRITIC_SYSTEM = """You are a ruthless, systematic critic reviewing a technical proposal for a distributed AI agent mesh.
Your job: find every logical flaw, missing edge case, weak assumption, and gap in the proposal.
Be harsh but fair. Do not praise. Do not soften.

You MUST respond in valid JSON with this exact structure:
{
  "score": <float 0.0-1.0>,
  "flaws": ["flaw 1", "flaw 2", ...],
  "verdict": "<one sentence summary of the main problem or 'Approved' if score >= 0.6>"
}

Scoring guide:
  1.0 = flawless, airtight, no gaps
  0.8 = solid with minor issues
  0.6 = passable but needs attention
  0.4 = significant flaws, revise before sharing
  0.2 = fundamentally broken
  0.0 = incoherent or harmful"""


def _wire_critique(handler_class, config):
    """Inject POST /critique into BifrostHandler."""
    # Chain on top of whatever do_POST already is (may already be extended)
    prev_post = handler_class.do_POST

    def do_POST_with_critique(self):
        if self.path == "/critique":
            _handle_critique(self, config)
        else:
            prev_post(self)

    handler_class.do_POST = do_POST_with_critique
    log.info("[bifrost_local] /critique route injected")


def _ollama_generate(model: str, system: str, prompt: str,
                     ollama_base: str = "http://127.0.0.1:11434",
                     extra_params: dict = None) -> str:
    """Single Ollama generation call. Returns raw response text."""
    body = {
        "model":  model,
        "system": system,
        "prompt": prompt,
        "stream": False,
    }
    if extra_params:
        body.update(extra_params)   # inject temperature, top_p from personality
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{ollama_base}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read()).get("response", "")


def _parse_critic_json(raw: str) -> dict:
    """Extract and parse the JSON block from the critic response."""
    import re
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    # Find outermost JSON object
    start = raw.find("{")
    end   = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in critic response: {raw[:200]}")
    return json.loads(raw[start:end + 1])


def _handle_critique(handler, config):
    """POST /critique — shadow critic endpoint."""
    import threading
    import urllib.request as _req
    _t0 = time.time()
    _err = False
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body   = json.loads(handler.rfile.read(length)) if length else {}
    except Exception:
        _json_respond(handler, 400, {"error": "invalid JSON"}); return

    text      = body.get("text", "").strip()
    msg_type  = body.get("type", "note").lower()
    sender    = body.get("from", "unknown")
    ollama    = config.get("ollama_base", "http://127.0.0.1:11434")

    # Optional: prompt_score from Heimdall's prompt_guard (0.0–1.0, higher = more dangerous)
    prompt_score = body.get("prompt_score")   # None if not provided

    if not text:
        _json_respond(handler, 400, {"error": "text field required"}); return

    # --- Type gate: skip critic for routine messages ---
    if msg_type in _SKIP_TYPES and msg_type not in _CRITIQUE_TYPES:
        _CRITIQUE_STATS["skipped"] += 1
        _json_respond(handler, 200, {
            "pass":    True,
            "score":   1.0,
            "flaws":   [],
            "verdict": "Skipped — routine message type",
            "type":    msg_type,
            "skipped": True,
        })
        return

    # --- prompt_score fast-path: if Heimdall's guard already blocked it, skip inference ---
    if prompt_score is not None:
        ps = float(prompt_score)
        if ps >= 0.8:
            # Guard already blocked — no need to run Ollama
            _CRITIQUE_STATS["skipped"] += 1
            log.warning("[critique] Skipped inference — prompt_guard blocked (score=%.2f) from %s",
                        ps, sender)
            _json_respond(handler, 200, {
                "pass":         False,
                "score":        0.0,
                "flaws":        ["Blocked by prompt guard before critique"],
                "verdict":      "Rejected by Heimdall prompt guard",
                "type":         msg_type,
                "prompt_score": ps,
                "guard_blocked": True,
                "threshold":    _CRITIQUE_THRESHOLD,
            })
            return
        elif ps >= 0.5:
            # Guard warned — run critic but flag the result
            log.info("[critique] prompt_guard warning (score=%.2f) on msg from %s — proceeding",
                     ps, sender)

    # --- SHA256 cache check — skip inference on duplicate text ---
    cache_key = _hashlib.sha256(text.encode()).hexdigest()
    cached = _CRITIQUE_CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _CRITIQUE_CACHE_TTL:
        _CRITIQUE_STATS["cached"] += 1
        res = cached["result"]
        log.info("[critique] Cache hit for %s/%s (age=%.0fs)",
                 msg_type, sender, time.time() - cached["ts"])
        _json_respond(handler, 200, {**res, "cached": True})
        return

    # --- Build critic system prompt + personality preamble ---
    personality_preamble = ""
    ollama_params = {}
    if _personality:
        personality_preamble = _personality.get("system_prompt", "")
        ollama_params = _personality.get("ollama_params", {})

    critic_system = _CRITIC_SYSTEM + personality_preamble

    # --- Run critic pass: try fast model first, fall back to full ---
    prompt = f"[TYPE: {msg_type}] [FROM: {sender}]\n\n{text}"
    raw_response = None
    model_used   = None

    for model in [_CRITIC_MODEL_FAST, _CRITIC_MODEL_FULL]:
        try:
            raw_response = _ollama_generate(model, critic_system, prompt,
                                            ollama, extra_params=ollama_params)
            model_used = model
            if model == _CRITIC_MODEL_FAST:
                _CRITIQUE_STATS["fast_model"] += 1
            else:
                _CRITIQUE_STATS["full_model"] += 1
            break
        except Exception as e:
            log.warning("[critique] Model %s failed: %s", model, e)

    if raw_response is None:
        _json_respond(handler, 503, {"error": "Ollama unavailable — both models failed"})
        return

    # --- Parse JSON response ---
    try:
        result = _parse_critic_json(raw_response)
        score  = float(result.get("score", 0.0))
        flaws  = result.get("flaws", [])
        verdict = result.get("verdict", "")
    except Exception as e:
        log.warning("[critique] JSON parse failed: %s — raw: %s", e, raw_response[:300])
        # Fallback: treat as pass with a warning
        _json_respond(handler, 200, {
            "pass":    True,
            "score":   0.5,
            "flaws":   ["Critic parse error — manual review recommended"],
            "verdict": "Parse error",
            "model":   model_used,
            "raw":     raw_response[:500],
        })
        return

    passed = score >= _CRITIQUE_THRESHOLD
    _CRITIQUE_STATS["total"] += 1
    if passed:
        _CRITIQUE_STATS["passed"] += 1
    else:
        _CRITIQUE_STATS["rejected"] += 1

    # Store in cache
    result_obj = {
        "pass":      passed,
        "score":     round(score, 3),
        "flaws":     flaws,
        "verdict":   verdict,
        "type":      msg_type,
        "model":     model_used,
        "threshold": _CRITIQUE_THRESHOLD,
    }
    _CRITIQUE_CACHE[cache_key] = {"result": result_obj, "ts": time.time()}
    # Prune stale cache entries (keep it bounded)
    if len(_CRITIQUE_CACHE) > 500:
        oldest = sorted(_CRITIQUE_CACHE.items(), key=lambda x: x[1]["ts"])[:100]
        for k, _ in oldest:
            _CRITIQUE_CACHE.pop(k, None)

    log.info("[critique] %s/%s from=%s score=%.2f pass=%s flaws=%d model=%s",
             msg_type, model_used, sender, score, passed, len(flaws), model_used)

    _json_respond(handler, 200, result_obj)


# ---------------------------------------------------------------------------
# Hydra State Snapshots -- POST /snapshot, POST /absorb, GET /hydra-status
# ---------------------------------------------------------------------------

def _get_hydra():
    global _hydra
    if _hydra is None:
        try:
            import hydra as _h  # type: ignore
            _hydra = _h
        except ImportError as e:
            log.error("[bifrost_local] hydra.py not available: %s", e)
    return _hydra


def _wire_hydra(handler_class, config):
    """Inject Hydra routes into BifrostHandler (both GET and POST)."""
    ollama_base = config.get("ollama_base", "http://127.0.0.1:11434")
    freya_base  = "http://100.102.105.3:8765"
    if "nodes" in config and "freya" in config["nodes"]:
        n = config["nodes"]["freya"]
        freya_base = f"http://{n['ip']}:{n.get('port', 8765)}"

    # -- GET /hydra-status: chain onto existing do_GET --
    prev_get = handler_class.do_GET

    def do_GET_with_hydra(self):
        if self.path == "/hydra-status":
            h = _get_hydra()
            if h:
                _json_respond(self, 200, h.status_report())
            else:
                _json_respond(self, 503, {"error": "hydra module unavailable"})
        else:
            prev_get(self)

    handler_class.do_GET = do_GET_with_hydra

    # -- POST /snapshot & /absorb: chain onto existing do_POST --
    prev_post = handler_class.do_POST

    def do_POST_with_hydra(self):
        if self.path == "/snapshot":
            _handle_snapshot(self, config, ollama_base)
        elif self.path == "/absorb":
            _handle_absorb(self, config, freya_base, ollama_base)
        elif self.path == "/absorb/release":
            _handle_release(self)
        else:
            prev_post(self)

    handler_class.do_POST = do_POST_with_hydra
    log.info("[bifrost_local] Hydra routes injected: /snapshot, /absorb, /hydra-status")


def _handle_snapshot(handler, config, ollama_base: str):
    """POST /snapshot — generate and push a full state snapshot."""
    h = _get_hydra()
    if not h:
        _json_respond(handler, 503, {"error": "hydra module unavailable"}); return

    try:
        length = int(handler.headers.get("Content-Length", 0))
        body = json.loads(handler.rfile.read(length)) if length else {}
    except Exception:
        body = {}

    node = body.get("node")  # optional override; defaults to hostname
    memory_url = body.get("memory_sync_url", "http://127.0.0.1:8765/memory-sync")

    try:
        import threading
        result = {}

        def run():
            result["snapshot"] = h.generate_snapshot(
                node=node,
                memory_sync_url=memory_url,
                ollama_base=ollama_base,
            )

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=60)

        snap = result.get("snapshot", {})
        _json_respond(handler, 200, {
            "status":   "pushed",
            "node":     snap.get("node"),
            "content":  snap.get("content", "")[:200],
            "tags":     snap.get("tags", []),
            "ts":       snap.get("ts"),
        })
    except Exception as e:
        log.error("[hydra] /snapshot error: %s", e)
        _json_respond(handler, 500, {"error": str(e)})


def _handle_absorb(handler, config, freya_base: str, ollama_base: str):
    """POST /absorb — load a dead node's snapshot and take on their role."""
    h = _get_hydra()
    if not h:
        _json_respond(handler, 503, {"error": "hydra module unavailable"}); return

    try:
        length = int(handler.headers.get("Content-Length", 0))
        body = json.loads(handler.rfile.read(length)) if length else {}
    except Exception:
        _json_respond(handler, 400, {"error": "invalid JSON"}); return

    dead_node = body.get("dead_node", "").strip()
    if not dead_node:
        _json_respond(handler, 400, {"error": "dead_node required"}); return

    try:
        ctx = h.absorb_node(
            dead_node=dead_node,
            memory_query_base=freya_base,
        )
        # Audit log
        _audit("hydra:absorb", dead_node, "warning", {
            "absorbed_by":      "thor",
            "snapshot_age_s":   round(ctx.get("snapshot_age") or 0),
            "absorption_status": ctx.get("status"),
            "trigger":          "manual",
        })
        # Drop danger pheromone on the dead node's /health resource
        try:
            import watchdog as _wd  # type: ignore
            _wd._drop_pheromone(
                freya_base, dead_node, "danger", 0.75,
                f"manual absorb: {dead_node} unreachable"
            )
        except Exception:
            pass
        _json_respond(handler, 200, {
            "status":            "absorbing",
            "dead_node":         dead_node,
            "snapshot_age_s":    round(ctx.get("snapshot_age") or 0),
            "absorption_status": ctx.get("status"),
            "roles":             h.status_report()["roles"],
            "system_prompt":     ctx.get("system_prompt_injection", "")[:200],
        })
    except Exception as e:
        log.error("[hydra] /absorb error: %s", e)
        _json_respond(handler, 500, {"error": str(e)})


def _handle_release(handler):
    """POST /absorb/release — stop proxying an absorbed role."""
    h = _get_hydra()
    if not h:
        _json_respond(handler, 503, {"error": "hydra module unavailable"}); return

    try:
        length = int(handler.headers.get("Content-Length", 0))
        body = json.loads(handler.rfile.read(length)) if length else {}
    except Exception:
        _json_respond(handler, 400, {"error": "invalid JSON"}); return

    node = body.get("node", "").strip()
    if not node:
        _json_respond(handler, 400, {"error": "node required"}); return

    h.release_role(node)
    # Audit log + reliable pheromone on release
    _audit("hydra:release", node, "info", {
        "released_by": "thor", "trigger": "manual",
    })
    try:
        import watchdog as _wd  # type: ignore
        _wd._drop_pheromone(freya_base, node, "reliable", 0.6, f"role released: {node}")
    except Exception:
        pass
    _json_respond(handler, 200, {
        "status": "released",
        "node":   node,
        "roles":  h.status_report()["roles"],
    })


# ---------------------------------------------------------------------------
# GET /circuit-status — Expose all circuit breaker states
# POST /reload-personality — Hot-reload personality.json without restart
# GET  /catch-up?since=<ts> — Re-sync endpoint for nodes returning from offline
# ---------------------------------------------------------------------------

def _wire_hardening(handler_class, config):
    """Inject hardening utility routes."""
    prev_get  = handler_class.do_GET
    prev_post = handler_class.do_POST

    def do_GET_hardening(self):
        if self.path == "/circuit-status":
            _handle_circuit_status(self)
        elif self.path == "/critique-stats":
            _json_respond(self, 200, {
                **_CRITIQUE_STATS,
                "cache_size":   len(_CRITIQUE_CACHE),
                "cache_ttl_s":  _CRITIQUE_CACHE_TTL,
                "threshold":    _CRITIQUE_THRESHOLD,
                "fast_model":   _CRITIC_MODEL_FAST,
                "full_model":   _CRITIC_MODEL_FULL,
                "pass_rate":    round(
                    _CRITIQUE_STATS["passed"] / max(1, _CRITIQUE_STATS["total"]), 3),
            })
        elif self.path.startswith("/catch-up"):
            _handle_catch_up(self)
        else:
            prev_get(self)

    def do_POST_hardening(self):
        if self.path == "/reload-personality":
            _handle_reload_personality(self)
        else:
            prev_post(self)

    handler_class.do_GET  = do_GET_hardening
    handler_class.do_POST = do_POST_hardening
    log.info("[bifrost_local] Hardening routes: /circuit-status, /critique-stats, /reload-personality, /catch-up")


def _handle_circuit_status(handler):
    """GET /circuit-status — all circuit breaker states."""
    try:
        from circuit_breaker import all_states  # type: ignore
        _json_respond(handler, 200, {"breakers": all_states()})
    except ImportError:
        _json_respond(handler, 503, {"error": "circuit_breaker module not available"})


def _handle_reload_personality(handler):
    """POST /reload-personality — hot-reload personality.json into memory cache."""
    global _personality
    try:
        from personality import reload as p_reload, get_context  # type: ignore
        p_reload()   # clears cache + re-reads disk
        new_ctx = get_context()
        _personality = new_ctx
        p = new_ctx
        log.info("[bifrost_local] Personality reloaded — temp=%.2f top_p=%.2f",
                 p['ollama_params']['temperature'], p['ollama_params']['top_p'])
        _json_respond(handler, 200, {
            "status":        "reloaded",
            "traits":        p['traits'],
            "ollama_params": p['ollama_params'],
        })
    except Exception as e:
        log.error("[bifrost_local] /reload-personality error: %s", e)
        _json_respond(handler, 500, {"error": str(e)})


def _handle_catch_up(handler):
    """
    GET /catch-up?since=<unix_ts>
    Returns everything significant that happened since ts:
      - recent event-log entries
      - current personality
      - hydra status
      - circuit breaker states
    For nodes returning after downtime — one call to re-sync.
    """
    from urllib.parse import urlparse, parse_qs
    params = parse_qs(urlparse(handler.path).query)
    since  = float(params.get("since", ["0"])[0])

    # Event log since ts
    events = []
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:8765/event-log?limit=100", timeout=5
        ) as r:
            data = json.loads(r.read())
            events = [e for e in data.get("events", []) if e.get("ts", 0) >= since]
    except Exception:
        pass

    # Current personality
    personality = _personality or {}

    # Hydra status
    hydra_status = {}
    try:
        from hydra import status_report  # type: ignore
        hydra_status = status_report()
    except Exception:
        pass

    # Circuit breaker states
    cb_states = {}
    try:
        from circuit_breaker import all_states  # type: ignore
        cb_states = all_states()
    except Exception:
        pass

    _json_respond(handler, 200, {
        "since":         since,
        "event_count":   len(events),
        "events":        events[:50],
        "personality":   personality,
        "hydra":         hydra_status,
        "circuit_breakers": cb_states,
        "node":          "thor",
        "ts":            time.time(),
    })


# ---------------------------------------------------------------------------
# Sprint 5: Auto-Hydra Watchdog + Graceful Shutdown
# GET  /watchdog-status -- node health poll states
# POST /watchdog        -- {"action": "enable"|"disable"|"reset"}
# POST /shutdown        -- graceful: snapshot + clean exit
# ---------------------------------------------------------------------------

def _get_event_log_instance():
    """Return the EventLog singleton (set by _wire_event_log)."""
    return getattr(_get_event_log_instance, "_instance", None)


def _start_watchdog(config: dict):
    """Start watchdog after bifrost is mostly up (delayed 30s to let server bind)."""
    import threading
    def _delayed_start():
        import time as _t
        _t.sleep(30)   # let bifrost fully bind before we start polling peers
        try:
            import watchdog as wd  # type: ignore

            def _absorb(node):
                h = _get_hydra()
                if h:
                    h.absorb_node(node)
                    # Audit log
                    _audit("hydra:auto_absorb", node, "warning",
                           {"trigger": "watchdog", "failures": wd.FAILURE_THRESHOLD})

            def _release(node):
                h = _get_hydra()
                if h:
                    h.release_role(node)
                    _audit("hydra:release", node, "info", {"trigger": "watchdog", "reason": "node_recovered"})

            def _log_evt(event_type, payload):
                _audit(event_type, payload.get("node", "unknown"), "info", payload)

            wd.start(config, absorb_fn=_absorb, release_fn=_release, log_event_fn=_log_evt)
            log.info("[bifrost_local] Watchdog started")
        except Exception as e:
            log.error("[bifrost_local] Watchdog failed to start: %s", e)

    threading.Thread(target=_delayed_start, daemon=True, name="watchdog-init").start()


def _audit(event_type: str, node: str, severity: str = "info", payload: dict = None):
    """Write an event to the local event log (best-effort)."""
    try:
        import urllib.request as _ur, json as _json
        body = _json.dumps({
            "event_type": event_type,
            "node":       node,
            "payload":    payload or {},
            "severity":   severity,
        }).encode()
        req = _ur.Request(
            "http://127.0.0.1:8765/event-log",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        _ur.urlopen(req, timeout=3)
    except Exception:
        pass  # audit is best-effort, never block the call path


def _wire_watchdog_shutdown(handler_class, config):
    """Inject /watchdog-status, POST /watchdog, POST /shutdown routes."""
    prev_get  = handler_class.do_GET
    prev_post = handler_class.do_POST

    def do_GET_wd(self):
        if self.path == "/watchdog-status":
            try:
                import watchdog as wd  # type: ignore
                _json_respond(self, 200, wd.status())
            except ImportError:
                _json_respond(self, 503, {"error": "watchdog module not loaded"})
        else:
            prev_get(self)

    def do_POST_wd(self):
        if self.path == "/watchdog":
            _handle_watchdog_control(self)
        elif self.path == "/shutdown":
            _handle_shutdown(self, config)
        else:
            prev_post(self)

    handler_class.do_GET  = do_GET_wd
    handler_class.do_POST = do_POST_wd
    log.info("[bifrost_local] watchdog/shutdown routes wired")


def _handle_watchdog_control(handler):
    """POST /watchdog {\"action\": \"enable\"|\"disable\"|\"reset\"}."""
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body   = json.loads(handler.rfile.read(length)) if length else {}
    except Exception:
        _json_respond(handler, 400, {"error": "invalid JSON"}); return

    action = body.get("action", "").lower()
    try:
        import watchdog as wd  # type: ignore
        if action == "enable":
            wd.set_enabled(True)
        elif action == "disable":
            wd.set_enabled(False)
        elif action == "reset":
            with wd._lock:
                for rec in wd._nodes.values():
                    rec["failures"] = 0
        else:
            _json_respond(handler, 400, {"error": f"unknown action: {action}"}); return
        _json_respond(handler, 200, {"status": "ok", "action": action, **wd.status()})
    except ImportError:
        _json_respond(handler, 503, {"error": "watchdog module not loaded"})


def _handle_shutdown(handler, config):
    """
    POST /shutdown
    Graceful exit:
      1. Respond immediately with {status: "shutting_down"}
      2. Push a final Hydra snapshot
      3. Write shutdown event to audit log
      4. os._exit(0) after 3 seconds
    """
    node = config.get("node_name", "thor")
    _json_respond(handler, 200, {"status": "shutting_down", "node": node})
    _audit("node:shutdown", node, "warning", {"initiated_by": "POST /shutdown"})

    import threading
    def _deferred_shutdown():
        import time as _t
        # Push final snapshot
        try:
            h = _get_hydra()
            if h:
                h.generate_snapshot(node)
                log.info("[shutdown] Final snapshot pushed")
        except Exception as e:
            log.warning("[shutdown] Snapshot failed: %s", e)
        _t.sleep(2)
        log.info("[shutdown] Exiting")
        import os
        os._exit(0)

    threading.Thread(target=_deferred_shutdown, daemon=True, name="shutdown").start()


# ---------------------------------------------------------------------------
# Sprint 6: Rate Limiting + HMAC Signing
# GET  /rate-limit-status  -- bucket states for all active IPs
# POST routes wrapped with token bucket (per source IP) and HMAC soft-verify
# ---------------------------------------------------------------------------

# Routes that get rate-limited and their RPM caps (from rate_limiter defaults)
_RATE_LIMITED_POSTS = {"/critique", "/route-message", "/snapshot", "/absorb"}
# Routes that get HMAC soft-verified (log warning but allow if no sig present)
_SIGNED_POSTS = {"/absorb", "/absorb/release", "/shutdown", "/snapshot"}


def _wire_security(handler_class, config):
    """Layer rate limiting and HMAC verification over the existing POST handler."""
    prev_get  = handler_class.do_GET
    prev_post = handler_class.do_POST

    def do_GET_sec(self):
        if self.path == "/rate-limit-status":
            try:
                import rate_limiter as _rl  # type: ignore
                rl = _rl.get()
                _json_respond(self, 200, rl.status() if rl else {"error": "not initialized"})
            except ImportError:
                _json_respond(self, 503, {"error": "rate_limiter not available"})
        else:
            prev_get(self)

    def do_POST_sec(self):
        # Derive client IP
        client_ip = (getattr(self, "client_address", ("unknown",))[0])
        path      = self.path.split("?")[0]

        # --- Rate limiting ---
        if path in _RATE_LIMITED_POSTS:
            try:
                import rate_limiter as _rl  # type: ignore
                rl = _rl.get()
                if rl:
                    allowed, info = rl.check(path, client_ip)
                    if not allowed:
                        _json_respond(self, 429, {
                            "error":         "rate limit exceeded",
                            "retry_after_s": info.get("retry_after_s", 60),
                            "route":         path,
                            "limit_rpm":     info.get("capacity"),
                        })
                        return
            except Exception as e:
                log.debug("[security] Rate limiter check failed: %s", e)

        # --- HMAC soft-verify (log warning, don't block yet) ---
        if path in _SIGNED_POSTS:
            try:
                # Peek at body without consuming it from the stream
                length = int(self.headers.get("Content-Length", 0))
                if length > 0:
                    body = self.rfile.read(length)
                    # Re-inject body so downstream handler can read it
                    import io
                    self.rfile = io.BytesIO(body)
                    from signing import verify_or_log  # type: ignore
                    sender = verify_or_log(self, body, config)
                    log.debug("[security] %s from %s (sig=%s)",
                              path, sender,
                              "present" if self.headers.get("X-Bifrost-Sig") else "absent")
            except Exception as e:
                log.debug("[security] Signing check error: %s", e)

        prev_post(self)

    handler_class.do_GET  = do_GET_sec
    handler_class.do_POST = do_POST_sec
    log.info("[bifrost_local] Security: rate limiting on %s, HMAC soft-verify on %s",
             sorted(_RATE_LIMITED_POSTS), sorted(_SIGNED_POSTS))


# ---------------------------------------------------------------------------
# GET /agent-docs — serve mesh/docs/thor.md (Freya's shared doc layer)
# ---------------------------------------------------------------------------

_AGENT_DOC_PATH = Path(__file__).parent / "mesh" / "docs" / "thor.md"


def _wire_agent_docs(handler_class, config):
    """Inject GET /agent-docs to serve thor.md over HTTP."""
    prev_get = handler_class.do_GET

    def do_GET_agentdocs(self):
        if self.path == "/agent-docs":
            try:
                content = _AGENT_DOC_PATH.read_text(encoding="utf-8")
                encoded = content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
            except Exception as e:
                _json_respond(self, 500, {"error": f"Could not read agent doc: {e}"})
        else:
            prev_get(self)

    handler_class.do_GET = do_GET_agentdocs
    log.info("[bifrost_local] /agent-docs wired -> %s", _AGENT_DOC_PATH)


# ---------------------------------------------------------------------------
# Sprint 8: Performance Metrics + Distributed Shared State
# GET  /metrics             -- p50/p95/p99 latency + GPU stats
# POST /shared-state        -- set key/value, broadcast to peers
# GET  /shared-state        -- read key(s)
# POST /shared-state-sync   -- receive peer broadcast (Heimdall compatible)
# ---------------------------------------------------------------------------

_INSTRUMENTED_POSTS = {"/critique", "/route-message", "/snapshot", "/absorb"}


def _wire_metrics_shared_state(handler_class, config):
    """Add metrics + shared state routes, instrument POST latency."""
    prev_get  = handler_class.do_GET
    prev_post = handler_class.do_POST

    # Build peer URL list from config
    this_node  = config.get("node_name", "thor")
    peer_urls  = []
    for name, ncfg in config.get("nodes", {}).items():
        if name != this_node and ncfg.get("ip"):
            peer_urls.append(f"http://{ncfg['ip']}:{ncfg.get('port', 8765)}")

    def do_GET_ms(self):
        if self.path == "/metrics":
            try:
                import metrics as _m  # type: ignore
                _json_respond(self, 200, _m.snapshot())
            except ImportError:
                _json_respond(self, 503, {"error": "metrics module not loaded"})
        elif self.path.startswith("/shared-state"):
            try:
                import shared_state as _ss  # type: ignore
                from urllib.parse import urlparse, parse_qs
                qs  = parse_qs(urlparse(self.path).query)
                key = qs.get("key", [None])[0]
                _json_respond(self, 200, {"state": _ss.get(key), "key": key})
            except ImportError:
                _json_respond(self, 503, {"error": "shared_state module not loaded"})
        else:
            prev_get(self)

    def do_POST_ms(self):
        path = self.path.split("?")[0]

        if path == "/shared-state":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length)) if length else {}
                key    = body.get("key", "")
                value  = body.get("value")
                ttl    = body.get("ttl")
                if not key:
                    _json_respond(self, 400, {"error": "key required"}); return
                import shared_state as _ss  # type: ignore
                _ss.set_local(key, value, ttl=ttl, source="self")
                _ss.broadcast(key, value, ttl=ttl,
                              peer_urls=peer_urls, config=config)
                _json_respond(self, 200, {"status": "ok", "key": key,
                                          "peers_notified": len(peer_urls)})
            except Exception as e:
                _json_respond(self, 500, {"error": str(e)})

        elif path == "/shared-state-sync":
            # Receive peer broadcast (Heimdall compatible)
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length)) if length else {}
                key    = body.get("key", "")
                value  = body.get("value")
                ttl    = body.get("ttl")
                source = body.get("from", "unknown")
                if not key:
                    _json_respond(self, 400, {"error": "key required"}); return
                import shared_state as _ss  # type: ignore
                _ss.set_local(key, value, ttl=ttl, source=source)
                log.info("[shared_state] sync received: %s from %s", key, source)
                _json_respond(self, 200, {"status": "accepted", "key": key})
            except Exception as e:
                _json_respond(self, 500, {"error": str(e)})

        else:
            # Instrument latency on key routes
            if path in _INSTRUMENTED_POSTS:
                import time as _time
                t0 = _time.monotonic()
                try:
                    prev_post(self)
                finally:
                    try:
                        import metrics as _m  # type: ignore
                        _m.record(path, _time.monotonic() - t0)
                    except Exception:
                        pass
            else:
                prev_post(self)

    handler_class.do_GET  = do_GET_ms
    handler_class.do_POST = do_POST_ms
    log.info("[bifrost_local] metrics + shared_state routes wired (%d peers)", len(peer_urls))

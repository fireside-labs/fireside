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
    log.info("[bifrost_local] Thor extensions: /event-log, /personality, /route-message, /critique, /snapshot, /absorb, /hydra-status")
    # Pin models in VRAM — runs in background so startup isn't blocked
    import threading
    ollama_base = config.get("ollama_base", "http://127.0.0.1:11434")
    threading.Thread(target=_warmup_models, args=(ollama_base,), daemon=True).start()


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
_CRITIC_MODEL = "qwen3.5:35b"   # Thor's only LLM — used for critic pass
_MAIN_MODEL   = "qwen3.5:35b"   # same model, same hardware, 5090 handles it

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

    try:
        length = int(handler.headers.get("Content-Length", 0))
        body   = json.loads(handler.rfile.read(length)) if length else {}
    except Exception:
        _json_respond(handler, 400, {"error": "invalid JSON"}); return

    text      = body.get("text", "").strip()
    msg_type  = body.get("type", "note").lower()
    sender    = body.get("from", "unknown")
    ollama    = config.get("ollama_base", "http://127.0.0.1:11434")

    if not text:
        _json_respond(handler, 400, {"error": "text field required"}); return

    # --- Type gate: skip critic for routine messages ---
    if msg_type in _SKIP_TYPES and msg_type not in _CRITIQUE_TYPES:
        _json_respond(handler, 200, {
            "pass":    True,
            "score":   1.0,
            "flaws":   [],
            "verdict": "Skipped — routine message type",
            "type":    msg_type,
            "skipped": True,
        })
        return

    # --- Build critic system prompt + personality preamble ---
    personality_preamble = ""
    ollama_params = {}
    if _personality:
        personality_preamble = _personality.get("system_prompt", "")
        ollama_params = _personality.get("ollama_params", {})

    critic_system = _CRITIC_SYSTEM + personality_preamble

    # --- Run critic pass ---
    prompt = f"[TYPE: {msg_type}] [FROM: {sender}]\n\n{text}"
    raw_response = None
    model_used   = None

    for model in [_CRITIC_MODEL, _MAIN_MODEL]:
        try:
            raw_response = _ollama_generate(model, critic_system, prompt,
                                            ollama, extra_params=ollama_params)
            model_used   = model
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

    log.info("[critique] %s/%s from=%s score=%.2f pass=%s flaws=%d",
             msg_type, model_used, sender, score, passed, len(flaws))

    _json_respond(handler, 200, {
        "pass":    passed,
        "score":   round(score, 3),
        "flaws":   flaws,
        "verdict": verdict,
        "type":    msg_type,
        "model":   model_used,
        "threshold": _CRITIQUE_THRESHOLD,
    })


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
        _json_respond(handler, 200, {
            "status":         "absorbing",
            "dead_node":      dead_node,
            "snapshot_age_s": round(ctx.get("snapshot_age") or 0),
            "absorption_status": ctx.get("status"),
            "roles":          h.status_report()["roles"],
            "system_prompt":  ctx.get("system_prompt_injection", "")[:200],
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
    _json_respond(handler, 200, {
        "status": "released",
        "node":   node,
        "roles":  h.status_report()["roles"],
    })

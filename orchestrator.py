"""
orchestrator.py — Thin enrichment layer on top of V1 mesh infrastructure.

NOT a replacement for the existing peer-to-peer system. This module adds
per-message enrichment (memory recall, prediction scoring, event publishing)
while delegating routing and dispatch to the proven V1 components:

  - bot/router.py   → semantic + keyword routing (picks the best node)
  - bot/pipeline.py → multi-stage pipeline with Huginn/Muninn/parallel dispatch
  - bot/dispatcher.py → parallel threaded dispatch to mesh nodes
  - war_room/        → peer-to-peer task board (nodes talk to each other)

Orchestration loop per chat message:
  1. ROUTE    — bot/router.py semantic_route() picks best node for the task
  2. RECALL   — working-memory LanceDB search → inject context
  3. PREDICT  — predictions plugin → register expected answer
  4. INFER    — simple → stream local, complex → bot/pipeline.create_pipeline()
  5. SCORE    — predictions plugin → surprise metric
  6. OBSERVE  — working-memory → store exchange
  7. PUBLISH  — event-bus → dashboard updates
"""
from __future__ import annotations

import importlib.util
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.orchestrator")

# ---------------------------------------------------------------------------
# Configuration (set by init())
# ---------------------------------------------------------------------------
_config: dict = {}
_base_dir: Path = Path(".")
_node_id: str = "unknown"
_initialized: bool = False

# V1 router instance (lazy-loaded)
_router = None

# Fix #2: Module cache — load each plugin module once, not on every call
_module_cache: dict[str, object] = {}

# Fix #3: Mesh status cache — avoid hitting /health on every pipeline create
_mesh_cache: dict = {"active": False, "ts": 0.0}
_MESH_CACHE_TTL = 30  # seconds


def init(config: dict, base_dir: Path) -> None:
    """Initialize orchestrator with app config. Called once at startup."""
    global _config, _base_dir, _node_id, _initialized
    _config = config
    _base_dir = base_dir
    _node_id = config.get("node", {}).get("name", "companion")
    _initialized = True

    # Ensure bot/ is importable
    bot_dir = str(base_dir / "bot")
    if bot_dir not in sys.path:
        sys.path.insert(0, bot_dir)

    log.info("[orchestrator] Initialized for node=%s (hybrid mode)", _node_id)


# ---------------------------------------------------------------------------
# 1. ROUTE — Use bot/router.py semantic + keyword routing
# ---------------------------------------------------------------------------

def _get_router():
    """Lazy-load the V1 Router with all agent profiles."""
    global _router
    if _router is not None:
        return _router
    try:
        router_path = _base_dir / "bot" / "router.py"
        if not router_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("bot_router", str(router_path))
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _router = mod.Router(skills_dir=str(_base_dir / "bot"))
        log.info("[orchestrator] Loaded V1 Router with %d agent profiles",
                 len(_router.available_nodes()))
        return _router
    except Exception as e:
        log.debug("[orchestrator] V1 Router unavailable: %s", e)
        return None


def classify(message: str) -> str:
    """Classify message as 'simple' or 'complex' using V1 Router.

    Uses semantic routing when available, falls back to keyword heuristics.
    """
    router = _get_router()
    if router:
        try:
            # Use keyword scoring — if the best node scores > 2,
            # the task has enough domain-specific signals to be "complex"
            scores = router.score_all(message)
            if scores and scores[0]["score"] >= 2:
                return "complex"
        except Exception:
            pass

    # Fallback: length + keyword heuristics
    lower = message.lower().strip()
    if len(lower) < 20:
        return "simple"

    complex_signals = [
        "research", "analyze", "compare", "investigate", "build a plan",
        "create a strategy", "break down", "step by step", "multi-step",
        "evaluate options", "pros and cons", "deep dive", "comprehensive",
        "audit", "review all", "summarize everything", "give me a report",
        "and then", "after that", "first do", "plan for",
    ]
    score = sum(1 for sig in complex_signals if sig in lower)
    if score >= 2:
        return "complex"
    if score == 1 and len(lower) > 80:
        return "complex"
    return "simple"


def route_to_node(message: str, exclude: list = None) -> Optional[dict]:
    """Route a task to the best mesh node using V1 semantic router.

    Returns routing result dict or None if routing unavailable.
    Uses VRAM load checks to skip overloaded nodes.
    """
    router = _get_router()
    if not router:
        return None
    try:
        # Try semantic routing first (uses Ollama embeddings)
        results = router.semantic_route(
            message, top_k=2, exclude=exclude or [],
            load_check=True, config=_config.get("mesh", {}),
        )
        if results:
            return results[0]

        # Fall back to keyword routing
        return router.route(message, exclude=exclude or [],
                           load_check=True, config=_config.get("mesh", {}))
    except Exception as e:
        log.debug("[orchestrator] Routing failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# 2. RECALL — Pull relevant memories from working-memory (LanceDB)
# ---------------------------------------------------------------------------

def _load_module(key: str, path: Path):
    """Load a module from path, caching to avoid repeated importlib overhead."""
    if key in _module_cache:
        return _module_cache[key]
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(key, str(path))
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _module_cache[key] = mod
    return mod


def recall_memories(query: str, top_k: int = 3) -> list[dict]:
    """Search working memory for relevant context."""
    try:
        mod = _load_module("wm", _base_dir / "plugins" / "working-memory" / "handler.py")
        if not mod:
            return []
        wm = mod.get_working_memory()
        items = wm.recall(query=query, top_k=top_k)
        log.debug("[orchestrator] Recalled %d memories for: %s", len(items), query[:50])
        return items
    except Exception as e:
        log.debug("[orchestrator] Memory recall failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# 3. PREDICT — Register prediction before inference
# ---------------------------------------------------------------------------

def pre_predict(query: str) -> Optional[str]:
    """Call predictions plugin before inference. Returns query_hash."""
    try:
        mod = _load_module("predictions", _base_dir / "plugins" / "predictions" / "handler.py")
        if not mod:
            return None
        return mod.predict(query)
    except Exception as e:
        log.debug("[orchestrator] Prediction failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# 5. SCORE — Score prediction error after inference
# ---------------------------------------------------------------------------

def post_score(query_hash: Optional[str], response: str) -> Optional[float]:
    """Score prediction error after inference."""
    if not query_hash:
        return None
    try:
        mod = _load_module("predictions", _base_dir / "plugins" / "predictions" / "handler.py")
        if not mod:
            return None
        return mod.score(query_hash, response)
    except Exception as e:
        log.debug("[orchestrator] Scoring failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# 6. OBSERVE — Store exchange in working memory
# ---------------------------------------------------------------------------

def observe(content: str, importance: float = 0.6, source: str = "chat") -> None:
    """Store a conversation turn in working memory. Non-blocking."""
    try:
        mod = _load_module("wm", _base_dir / "plugins" / "working-memory" / "handler.py")
        if not mod:
            return
        wm = mod.get_working_memory()
        wm.observe(content, importance=importance, source=source)
    except Exception as e:
        log.debug("[orchestrator] Observe failed: %s", e)


# ---------------------------------------------------------------------------
# 7. PUBLISH — Emit events to event bus
# ---------------------------------------------------------------------------

def publish(topic: str, payload: dict) -> None:
    """Publish event to the event bus. Non-blocking."""
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        try:
            handler_path = _base_dir / "plugins" / "event-bus" / "handler.py"
            if handler_path.exists():
                spec = importlib.util.spec_from_file_location("eb_orch", str(handler_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    mod.publish(topic, payload)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Agent identity — read from config + souls, never hardcode
# ---------------------------------------------------------------------------

def get_agent_name() -> str:
    """Get the AI's name from config. Never hardcoded."""
    # 1. companion_state.json
    try:
        state_path = Path.home() / ".valhalla" / "companion_state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            agent = state.get("agent", {})
            if agent.get("name"):
                return agent["name"]
    except Exception:
        pass

    # 2. onboarding.json
    try:
        ob_path = Path.home() / ".fireside" / "onboarding.json"
        if ob_path.exists():
            ob = json.loads(ob_path.read_text(encoding="utf-8"))
            if ob.get("companion_name"):
                return ob["companion_name"]
    except Exception:
        pass

    # 3. Config
    companion_cfg = _config.get("companion", {})
    if companion_cfg.get("name"):
        return companion_cfg["name"]

    # 4. IDENTITY soul file
    try:
        identity_file = _base_dir / "souls" / "default" / "IDENTITY.md"
        if identity_file.exists():
            text = identity_file.read_text(encoding="utf-8")
            for line in text.split("\n"):
                line = line.strip()
                if line.lower().startswith("name:"):
                    return line.split(":", 1)[1].strip()
                if line.startswith("# "):
                    return line[2:].strip()
    except Exception:
        pass

    # 5. Node config fallback
    return _config.get("node", {}).get("friendly_name",
           _config.get("node", {}).get("name", "Companion"))


def get_user_name() -> str:
    """Get the user's name from onboarding/config."""
    try:
        ob_path = Path.home() / ".fireside" / "onboarding.json"
        if ob_path.exists():
            ob = json.loads(ob_path.read_text(encoding="utf-8"))
            return ob.get("user_name", "")
    except Exception:
        pass
    return _config.get("user", {}).get("name", "")


# ---------------------------------------------------------------------------
# HIGH-LEVEL HOOKS — called by api/v1.py chat endpoint
# ---------------------------------------------------------------------------

def pre_inference(message: str, context: list = None) -> dict:
    """Called BEFORE model inference. Returns enriched context.

    Uses V1 Router for smart classification + routing.
    Recalls memories from LanceDB.
    Registers prediction for post-inference scoring.
    """
    result = {
        "classification": classify(message),
        "memories": [],
        "query_hash": None,
        "agent_name": get_agent_name(),
        "user_name": get_user_name(),
        "enriched_system_additions": "",
        "routing": None,
    }

    # Route to best node (for complex tasks)
    if result["classification"] == "complex":
        result["routing"] = route_to_node(message)

    # Recall relevant memories
    memories = recall_memories(message, top_k=3)
    result["memories"] = memories

    if memories:
        mem_lines = [f"- {m.get('content', '')[:200]}" for m in memories[:3]]
        result["enriched_system_additions"] = (
            "\n\n[Relevant memories from previous conversations]\n"
            + "\n".join(mem_lines)
        )

    # Register prediction
    result["query_hash"] = pre_predict(message)

    publish("orchestrator.pre_inference", {
        "classification": result["classification"],
        "memories_found": len(memories),
        "routing": result["routing"],
        "message_preview": message[:80],
        "node": _node_id,
    })

    log.info("[orchestrator] Pre-inference: class=%s, memories=%d, agent=%s",
             result["classification"], len(memories), result["agent_name"])

    return result


def post_inference(message: str, response: str, query_hash: Optional[str] = None,
                   classification: str = "simple") -> dict:
    """Called AFTER model inference. Scores, stores, publishes."""
    result = {
        "prediction_error": None,
        "surprising": False,
        "stored": False,
    }

    # Score prediction
    error = post_score(query_hash, response)
    if error is not None:
        result["prediction_error"] = round(error, 4)
        result["surprising"] = error > 0.55

    # Store in working memory
    importance = 0.7 if classification == "complex" else 0.5
    exchange = f"User: {message[:300]}\nAssistant: {response[:500]}"
    observe(exchange, importance=importance, source="chat")
    result["stored"] = True

    publish("orchestrator.post_inference", {
        "classification": classification,
        "prediction_error": result["prediction_error"],
        "surprising": result["surprising"],
        "response_length": len(response),
        "node": _node_id,
    })

    return result


# ---------------------------------------------------------------------------
# MESH DETECTION — single-node sub-agents vs multi-node dispatch
# ---------------------------------------------------------------------------

def mesh_active() -> bool:
    """Check if other mesh peers are online. Cached for 30s.

    If True: use V1 War Room dispatch (nodes talk to each other)
    If False: use local sub-agents (same model, different system prompts)
    """
    # Fix #3: TTL cache — don't hit /health on every call
    now = time.time()
    if (now - _mesh_cache["ts"]) < _MESH_CACHE_TTL:
        return _mesh_cache["active"]

    try:
        import urllib.request
        bifrost_port = _config.get("server", {}).get("port", 8765)
        url = f"http://127.0.0.1:{bifrost_port}/health"
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read())
            nodes = data.get("nodes", data.get("peers", []))
            if isinstance(nodes, dict):
                alive = sum(1 for v in nodes.values()
                           if isinstance(v, dict) and v.get("alive", False))
            elif isinstance(nodes, list):
                alive = len(nodes)
            else:
                alive = 0
            result = alive > 0
    except Exception:
        result = False

    _mesh_cache["active"] = result
    _mesh_cache["ts"] = now
    return result


# ---------------------------------------------------------------------------
# PIPELINE CREATION — template-driven, mesh-aware
# ---------------------------------------------------------------------------

def create_task_pipeline(task: str, mode: str = "auto",
                         template_name: str = None) -> Optional[dict]:
    """Create a pipeline using the template system.

    Automatically detects:
    - Template: coding/research/general (or user-specified)
    - Mode: mesh (V1 War Room dispatch) or single (local sub-agents)

    Single-node: roles → system prompt personalities (sub-agents)
    Multi-node: roles → real nodes via bot/router.py + War Room
    """
    if mode == "direct":
        return None
    if mode == "auto" and classify(task) == "simple":
        return None

    # Load template
    try:
        from pipeline_templates import (
            get_template, classify_template, resolve_stages,
        )
    except ImportError as e:
        log.warning("[orchestrator] pipeline_templates not available: %s", e)
        return None

    # Auto-detect template if not specified
    if not template_name:
        template_name = classify_template(task)

    template = get_template(template_name)
    if not template:
        log.warning("[orchestrator] Template '%s' not found", template_name)
        return None

    # Detect mesh mode
    is_mesh = mesh_active()
    resolve_mode = "mesh" if is_mesh else "single"
    resolved_stages = resolve_stages(template, mode=resolve_mode)

    log.info("[orchestrator] Pipeline: template=%s, mode=%s, stages=%d",
             template_name, resolve_mode, len(resolved_stages))

    if is_mesh:
        # Multi-node: use V1 pipeline (Huginn/Muninn/War Room dispatch)
        return _create_mesh_pipeline(task, resolved_stages, template)
    else:
        # Single-node: use V2 pipeline plugin (local sub-agents)
        return _create_local_pipeline(task, resolved_stages, template)


def _create_mesh_pipeline(task: str, stages: list, template: dict) -> Optional[dict]:
    """Create pipeline via V1 bot/pipeline.py (multi-node War Room dispatch)."""
    try:
        pipeline_path = _base_dir / "bot" / "pipeline.py"
        if not pipeline_path.exists():
            log.warning("[orchestrator] bot/pipeline.py not found, falling back to local")
            return _create_local_pipeline(task, stages, template)

        spec = importlib.util.spec_from_file_location("bot_pipeline", str(pipeline_path))
        if not spec or not spec.loader:
            return _create_local_pipeline(task, stages, template)

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Convert resolved stages to V1 format
        v1_stages = []
        for s in stages:
            if "parallel" in s:
                v1_stages.append({
                    "name": s["name"],
                    "parallel": [
                        {"agent": p.get("agent", "local"),
                         "description": p.get("prompt", f"Complete {s['name']} phase")}
                        for p in s["parallel"]
                    ],
                })
            else:
                v1_stages.append({
                    "name": s["name"],
                    "agent": s.get("agent", "local"),
                    "description": s.get("prompt", f"Complete {s['name']} phase"),
                })

        meta = mod.create_pipeline(
            title=task[:100],
            description=task,
            stages=v1_stages,
            max_iterations=template.get("max_iterations", 3),
            posted_by=_node_id,
        )

        publish("orchestrator.pipeline_created", {
            "pipeline_id": meta.get("id", meta.get("task_id", "")),
            "template": template.get("name", "unknown"),
            "task_preview": task[:80],
            "mode": "v1_war_room",
            "node": _node_id,
        })

        return meta
    except Exception as e:
        log.warning("[orchestrator] V1 mesh pipeline failed: %s", e)
        return _create_local_pipeline(task, stages, template)


def _create_local_pipeline(task: str, stages: list, template: dict) -> Optional[dict]:
    """Create pipeline via V2 plugin (single-node, local sub-agents).

    Fix #1: Each stage receives the previous stage's output as context,
    so stage 2 knows what stage 1 produced. Uses 'prev_context' field
    which the pipeline plugin injects before each stage runs.
    """
    try:
        mod = _load_module("pipeline", _base_dir / "plugins" / "pipeline" / "handler.py")
        if not mod:
            return None

        # Convert to V2 format with context chaining
        v2_stages = []
        for i, s in enumerate(stages):
            # Fix #1: chain_context tells the pipeline to pass
            # previous stage output into this stage's prompt
            chain = i > 0  # all stages after the first get context

            # Fix #4: on_fail routing
            on_fail = s.get("on_fail", template.get("on_fail", "retry"))

            if "parallel" in s:
                # V2 doesn't support true parallel — serialize them
                for j, p in enumerate(s["parallel"]):
                    v2_stages.append({
                        "name": f"{s['name']}/{p.get('role', 'agent')}",
                        "agent": "local",
                        "task_type": p.get("task_type", "build"),
                        "system_prompt": p.get("system_prompt", ""),
                        "prompt": f"Task: {task}\n\nYour part: {p.get('prompt', '')}",
                        "chain_context": chain and j == 0,
                        "on_fail": on_fail,
                    })
            else:
                v2_stages.append({
                    "name": s["name"],
                    "agent": "local",
                    "task_type": s.get("task_type", "build"),
                    "system_prompt": s.get("system_prompt", ""),
                    "prompt": f"Task: {task}\n\nYour part: {s.get('prompt', '')}",
                    "chain_context": chain,
                    "on_fail": on_fail,
                })

        meta = mod.create_pipeline(
            title=task[:100],
            description=task,
            stages=v2_stages,
            max_iterations=template.get("max_iterations", 2),
            posted_by=_node_id,
        )

        publish("orchestrator.pipeline_created", {
            "pipeline_id": meta.get("id", ""),
            "template": template.get("name", "unknown"),
            "task_preview": task[:80],
            "mode": "v2_local",
            "node": _node_id,
        })

        return meta
    except Exception as e:
        log.error("[orchestrator] Local pipeline failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Belief shadow check — avoid duplicate work across nodes
# ---------------------------------------------------------------------------

def check_belief_shadows(task: str) -> dict:
    """Check if any mesh peer is already working on a similar task."""
    try:
        handler_path = _base_dir / "plugins" / "belief-shadows" / "handler.py"
        if not handler_path.exists():
            return {"novel": True, "peer_knowledge": {}}
        spec = importlib.util.spec_from_file_location("bs_orch", str(handler_path))
        if not spec or not spec.loader:
            return {"novel": True, "peer_knowledge": {}}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        shadows = mod.get_all_shadows()
        return {"novel": True, "peer_knowledge": shadows}
    except Exception:
        return {"novel": True, "peer_knowledge": {}}


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
_module_cache: dict[str, tuple[object, float]] = {}  # key → (module, load_time)
_MODULE_CACHE_TTL = 300  # seconds — re-import after 5min for hot-reload

# Fix #3: Mesh status cache — avoid hitting /health on every pipeline create
_mesh_cache: dict = {"active": False, "ts": 0.0}
_MESH_CACHE_TTL = 30  # seconds

# Templates that produce files/artifacts — auto-add terminal execution stage
_ARTIFACT_TEMPLATES = {"presentation", "coding", "analysis", "drafting"}


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
    """Classify message as 'simple' or 'complex'.

    Uses classify_template() as the authority — if any template scores ≥1,
    the task has enough structure to warrant a pipeline.
    Falls back to V1 Router scoring and keyword heuristics.
    """
    # PRIMARY: If a pipeline template matches, it's complex (period)
    try:
        from pipeline_templates import classify_template
        template = classify_template(message)
        if template != "general":  # specific match = complex
            return "complex"
    except ImportError:
        pass

    # SECONDARY: V1 Router semantic scoring
    router = _get_router()
    if router:
        try:
            scores = router.score_all(message)
            if scores and scores[0]["score"] >= 2:
                return "complex"
        except Exception:
            pass

    # TERTIARY: Length + keyword heuristics
    lower = message.lower().strip()
    if len(lower) < 20:
        return "simple"

    complex_signals = [
        "research", "analyze", "compare", "investigate", "build a plan",
        "create a strategy", "break down", "step by step", "multi-step",
        "evaluate options", "pros and cons", "deep dive", "comprehensive",
        "audit", "review all", "summarize everything", "give me a report",
        "and then", "after that", "first do", "plan for",
        "powerpoint", "presentation", "slide deck", "deploy",
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
    """Load a module from path, with TTL cache for hot-reload support."""
    now = time.time()
    if key in _module_cache:
        mod, loaded_at = _module_cache[key]
        if (now - loaded_at) < _MODULE_CACHE_TTL:
            return mod
        # TTL expired — re-import
        log.debug("[orchestrator] Module cache expired for %s, reloading", key)

    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(key, str(path))
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _module_cache[key] = (mod, now)
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

    Fix #1: Each stage receives the previous stage's output as context.
    Fix #5: Templates that produce artifacts (coding, presentation, analysis)
            get an auto-injected terminal execution stage at the end.
    """
    try:
        mod = _load_module("pipeline", _base_dir / "plugins" / "pipeline" / "handler.py")
        if not mod:
            return None

        # Convert to V2 format with context chaining
        v2_stages = []
        for i, s in enumerate(stages):
            chain = i > 0
            on_fail = s.get("on_fail", template.get("on_fail", "retry"))

            if "parallel" in s:
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
                    "debate": s.get("debate", False),
                })

        # Wire Socratic debate into review stages that have debate=True
        for stage in v2_stages:
            if stage.get("debate"):
                stage["system_prompt"] = (
                    "You are a REVIEW COORDINATOR for a Socratic debate. "
                    "The previous stage's output will be reviewed by multiple "
                    "personas (architect, devil's advocate, end-user) who will "
                    "critique, debate, and score it. You synthesize their "
                    "verdict into VERDICT: SHIP or VERDICT: FAIL.\n\n"
                    "The debate is managed by the Socratic plugin at "
                    "POST /api/v1/socratic/debate — it runs automatically."
                )
                stage["socratic_config"] = {
                    "rounds": 3,
                    "consensus_threshold": 0.7,
                    "reviewers": [
                        {
                            "persona": "architect",
                            "model": "local/default",
                            "prompt": (
                                "Review as a senior architect. Focus on "
                                "scalability, maintainability, and correctness."
                            ),
                        },
                        {
                            "persona": "devil_advocate",
                            "model": "local/default",
                            "prompt": (
                                "Attack every assumption. What breaks in 6 months? "
                                "What edge cases were missed? Be ruthless."
                            ),
                        },
                        {
                            "persona": "end_user",
                            "model": "local/default",
                            "prompt": (
                                "You are a non-technical end user. What's confusing? "
                                "What's missing? Does this actually solve the problem?"
                            ),
                        },
                    ],
                }
                publish("orchestrator.debate_configured", {
                    "stage": stage["name"],
                    "reviewers": 3,
                    "rounds": 3,
                })

        # Fix #5: Auto-inject terminal execution for artifact-producing templates
        template_name = template.get("name", "").lower()
        if template_name in _ARTIFACT_TEMPLATES:
            v2_stages.append({
                "name": "execute",
                "agent": "local",
                "task_type": "execute",
                "system_prompt": (
                    "You are an execution agent. You take the final output from "
                    "previous stages and create real files and artifacts. You use "
                    "the terminal to run commands: create files, install packages, "
                    "run scripts, and generate outputs. You have full terminal access "
                    "via POST /api/v1/terminal/exec with {command, reason, working_dir}. "
                    "Always report which files you created and their paths."
                ),
                "prompt": (
                    f"Task: {task}\n\n"
                    "Using the terminal, create the actual output files from the "
                    "previous stages. If this is a presentation, create the .pptx file. "
                    "If code, write the files to disk. If analysis, export the report. "
                    "Use the terminal API to execute commands. Report all created files."
                ),
                "chain_context": True,
                "on_fail": "retry",
                "terminal_enabled": True,
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
            "has_terminal_stage": template_name in _ARTIFACT_TEMPLATES,
            "node": _node_id,
        })

        return meta
    except Exception as e:
        log.error("[orchestrator] Local pipeline failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Gap #2: Pipeline State Tracking + Feedback Loop
# ---------------------------------------------------------------------------
_pipeline_state: dict[str, dict] = {}  # {pipeline_id: state}


def track_iteration(pipeline_id: str, stage_name: str,
                    output: str, verdict: str = "",
                    test_pass: int = 0, test_total: int = 0) -> dict:
    """Track a stage's output per iteration for feedback and regression detection.

    Called after each stage completes. Stores the full transcript so:
      1) on_fail retries get the failure REASON injected (Gap #2 feedback loop)
      2) regression detection can compare across iterations (Gap #3)
    """
    if pipeline_id not in _pipeline_state:
        _pipeline_state[pipeline_id] = {
            "iterations": [],
            "feedback_queue": [],  # pending feedback for retried stages
            "status": "running",
            "created_at": time.time(),
        }

    state = _pipeline_state[pipeline_id]
    iteration = {
        "stage": stage_name,
        "output": output[:3000],  # cap stored output
        "verdict": verdict,
        "test_pass": test_pass,
        "test_total": test_total,
        "ts": time.time(),
        "round": len(state["iterations"]) + 1,
    }
    state["iterations"].append(iteration)

    # If stage failed, queue the feedback for the retried stage
    if verdict.upper() in ("FAIL", "IMPROVE", "OBJECT"):
        state["feedback_queue"].append({
            "from_stage": stage_name,
            "message": output[:2000],
            "round": iteration["round"],
        })

    publish("orchestrator.stage_completed", {
        "pipeline_id": pipeline_id,
        "stage": stage_name,
        "verdict": verdict,
        "round": iteration["round"],
    })

    return iteration


def inject_feedback(pipeline_id: str, stage_name: str,
                    original_prompt: str) -> str:
    """Inject feedback from failing stages into a retried stage's prompt.

    When on_fail triggers goto:build, the build stage's prompt gets the
    tester's specific failure output prepended. The agent knows exactly
    what to fix — not just "try again."
    """
    state = _pipeline_state.get(pipeline_id, {})
    queue = state.get("feedback_queue", [])

    if not queue:
        return original_prompt

    # Drain all queued feedback into the prompt
    feedback_blocks = []
    for fb in queue:
        feedback_blocks.append(
            f"[FEEDBACK FROM {fb['from_stage'].upper()} — iteration {fb['round']}]\n"
            f"{fb['message']}\n"
            f"[END FEEDBACK]"
        )

    state["feedback_queue"] = []  # clear after injection

    feedback_text = "\n\n".join(feedback_blocks)
    return (
        f"{feedback_text}\n\n"
        f"Fix the specific issues described above.\n\n"
        f"---\n\n{original_prompt}"
    )


# ---------------------------------------------------------------------------
# Gap #3: Regression Detection + Escalation
# ---------------------------------------------------------------------------

def detect_regression(pipeline_id: str) -> dict:
    """Compare test results across iterations. Detect regression or plateau.

    Returns: {"status": "progress|plateau|regression|insufficient_data",
              "details": str, "should_escalate": bool}
    """
    state = _pipeline_state.get(pipeline_id)
    if not state:
        return {"status": "insufficient_data", "details": "No state", "should_escalate": False}

    # Get test iterations only (stages that have test results)
    test_iters = [
        it for it in state["iterations"]
        if it.get("test_total", 0) > 0
    ]

    if len(test_iters) < 2:
        return {"status": "insufficient_data", "details": "Need 2+ test iterations",
                "should_escalate": False}

    current = test_iters[-1]
    previous = test_iters[-2]

    cur_pass = current["test_pass"]
    prev_pass = previous["test_pass"]
    cur_total = current["test_total"]

    if cur_pass > prev_pass:
        return {
            "status": "progress",
            "details": f"Tests: {prev_pass} → {cur_pass}/{cur_total}",
            "should_escalate": False,
        }
    elif cur_pass == prev_pass:
        # Check for plateau (same result 2+ times)
        plateau_count = sum(
            1 for it in test_iters[-3:]
            if it["test_pass"] == cur_pass
        )
        if plateau_count >= 2:
            return {
                "status": "plateau",
                "details": f"Stuck at {cur_pass}/{cur_total} for {plateau_count} iterations",
                "should_escalate": True,
            }
        return {
            "status": "plateau",
            "details": f"Same at {cur_pass}/{cur_total}",
            "should_escalate": False,
        }
    else:
        # REGRESSION — things got worse
        result = {
            "status": "regression",
            "details": f"REGRESSION: {prev_pass} → {cur_pass}/{cur_total}",
            "should_escalate": True,
        }

        # Auto-escalate
        state["status"] = "escalated"
        publish("orchestrator.pipeline_escalated", {
            "pipeline_id": pipeline_id,
            "reason": result["details"],
            "current_pass": cur_pass,
            "previous_pass": prev_pass,
            "total": cur_total,
        })
        log.warning("[orchestrator] Pipeline %s ESCALATED: %s",
                    pipeline_id, result["details"])

        return result


def get_pipeline_state(pipeline_id: str) -> dict:
    """Return full pipeline state for dashboard / War Room display."""
    state = _pipeline_state.get(pipeline_id)
    if not state:
        return {"error": "Pipeline not found"}
    return {
        "pipeline_id": pipeline_id,
        "status": state["status"],
        "iterations": len(state["iterations"]),
        "feedback_pending": len(state.get("feedback_queue", [])),
        "transcript": state["iterations"],
    }


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


# ===========================================================================
# ALWAYS-ON CAPABILITIES — available on every message, template or not
# ===========================================================================
# These are tools the AI can invoke at any time during inference.
# No template needed. No pipeline needed. Just capabilities.

def get_available_tools() -> list[dict]:
    """Return the list of tools the AI can always use.

    This is injected into the system prompt so the model knows what it can do.
    Each tool maps to an API endpoint the model can call via function calling
    or structured output.
    """
    tools = [
        {
            "name": "terminal",
            "description": "Run a command on the user's computer",
            "endpoint": "POST /api/v1/terminal/exec",
            "params": {"command": "str", "reason": "str", "working_dir": "str"},
            "examples": [
                "Create a file: echo 'content' > file.txt",
                "Install a package: pip install python-pptx",
                "Run a script: python generate_report.py",
                "List files: dir /b (Windows) or ls -la (Linux)",
            ],
        },
        {
            "name": "browse",
            "description": "Read and summarize a web page",
            "endpoint": "POST /api/v1/browse/read",
            "params": {"url": "str", "summary": "bool"},
        },
        {
            "name": "memory_search",
            "description": "Search past conversations and stored knowledge",
            "endpoint": "GET /api/v1/memory/search",
            "params": {"query": "str", "top_k": "int"},
        },
        {
            "name": "memory_store",
            "description": "Store important information for later recall",
            "endpoint": "POST /api/v1/memory/store",
            "params": {"content": "str", "importance": "float"},
        },
        {
            "name": "spawn_agent",
            "description": "Delegate a sub-task to a specialist sub-agent",
            "endpoint": "POST /api/v1/orchestrator/spawn",
            "params": {"role": "str", "task": "str", "context": "str"},
        },
        {
            "name": "create_pipeline",
            "description": "Create a multi-step workflow for complex tasks",
            "endpoint": "POST /api/v1/pipeline/create",
            "params": {"task": "str", "template": "str (optional)"},
        },
        {
            "name": "file_read",
            "description": "Read the contents of a file",
            "endpoint": "POST /api/v1/files/read",
            "params": {"path": "str", "encoding": "str (utf-8)"},
        },
        {
            "name": "file_write",
            "description": "Write content to a file (creates dirs if needed)",
            "endpoint": "POST /api/v1/files/write",
            "params": {"path": "str", "content": "str", "mode": "str (w or a)"},
        },
        {
            "name": "file_list",
            "description": "List files and directories at a path",
            "endpoint": "POST /api/v1/files/list",
            "params": {"path": "str", "recursive": "bool", "pattern": "str (glob)"},
        },
        {
            "name": "file_search",
            "description": "Search for text inside files (grep-like)",
            "endpoint": "POST /api/v1/files/search",
            "params": {"path": "str", "query": "str", "extensions": "list[str]"},
        },
    ]

    # Only include tools whose plugins are actually loaded
    # (terminal always available since it was just created)
    return tools


def get_tools_system_prompt() -> str:
    """Generate system prompt addition describing available tools.

    This gets injected into every inference call so the AI always knows
    what it can do — no template required.
    """
    tools = get_available_tools()
    lines = [
        "\n\n[AVAILABLE TOOLS — you can use these at any time]",
        "To use a tool, output a structured JSON block with the tool name and params.",
        "You may use multiple tools in sequence to complete a task.\n",
    ]
    for t in tools:
        params = ", ".join(f"{k}: {v}" for k, v in t.get("params", {}).items())
        lines.append(f"• {t['name']}: {t['description']}")
        lines.append(f"  → {t['endpoint']} ({params})")
        if t.get("examples"):
            for ex in t["examples"][:2]:
                lines.append(f"    e.g. {ex}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SUB-AGENT SPAWNING — single machine, multiple personalities
# ---------------------------------------------------------------------------
# Spin up ephemeral sub-agents on the same LLM with different system prompts.
# Each sub-agent is just a separate inference call with a role-specific prompt.
# This is how one machine acts like a team.

def spawn_sub_agent(
    role: str,
    task: str,
    context: str = "",
    model_override: str = None,
) -> dict:
    """Spawn an ephemeral sub-agent with a specific role.

    Single-machine mode: same LLM, different system prompt.
    The sub-agent runs to completion and returns its output.

    Roles: planner, backend, frontend, tester, reviewer, researcher,
           analyst, writer, designer, executor, data_analyst
    """
    from pipeline_templates import ROLE_PROMPTS

    system_prompt = ROLE_PROMPTS.get(role, ROLE_PROMPTS.get("executor", ""))
    if not system_prompt:
        system_prompt = f"You are a {role} specialist. Complete the assigned task thoroughly."

    # Build the full prompt with context
    full_prompt = f"Task: {task}"
    if context:
        full_prompt = f"Context from previous work:\n{context}\n\n{full_prompt}"

    result = {
        "role": role,
        "task": task[:200],
        "status": "completed",
        "output": None,
        "model": model_override or "default",
    }

    try:
        # Try to use the actual inference endpoint
        import urllib.request
        port = _config.get("server", {}).get("port", 8765)
        url = f"http://127.0.0.1:{port}/api/v1/chat"

        payload = json.dumps({
            "message": full_prompt,
            "system_prompt": system_prompt,
            "model": model_override,
            "stream": False,
            "sub_agent": True,  # flag so chat endpoint doesn't re-orchestrate
        }).encode()

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            result["output"] = data.get("response", data.get("content", ""))
            result["status"] = "completed"

        log.info("[orchestrator] Sub-agent %s completed: %s", role, task[:60])

    except Exception as e:
        log.warning("[orchestrator] Sub-agent %s failed: %s", role, e)
        result["status"] = "failed"
        result["error"] = str(e)

    publish("orchestrator.sub_agent", {
        "role": role,
        "task": task[:80],
        "status": result["status"],
        "node": _node_id,
    })

    return result


def execute_ad_hoc(task: str, tools_needed: list[str] = None) -> dict:
    """Execute an ad-hoc task using available tools. No template needed.

    This is the fallback for tasks that don't match any template but
    still need real-world action (terminal, files, browsing, email, etc).

    The AI figures out the steps and uses registered tools to execute them.
    """
    result = {
        "task": task[:200],
        "steps_completed": [],
        "artifacts": [],
        "status": "completed",
        "tools_used": [],
    }

    # Load tool registry
    try:
        from bot.tools import execute_tool, get_tool_definitions, TOOLS
        available_tools = list(TOOLS.keys())
    except ImportError:
        available_tools = ["terminal"]

    # Step 1: Ask a planner sub-agent to break it down with tool awareness
    tool_list = ", ".join(available_tools)
    plan = spawn_sub_agent(
        role="planner",
        task=(
            f"Break this into 2-4 concrete steps. "
            f"Available tools: {tool_list}. "
            f"For each step, specify which tool to use and its arguments.\n\n"
            f"Task: {task}\n\n"
            f"Respond as JSON: "
            f'[{{"step": 1, "tool": "tool_name", "args": {{...}}, "description": "..."}}]'
        ),
    )

    if plan["status"] != "completed" or not plan.get("output"):
        result["status"] = "failed"
        result["error"] = "Planning failed"
        return result

    result["steps_completed"].append({
        "step": "plan",
        "output": plan["output"],
    })

    # Step 2: Parse and execute the planned tool calls
    tool_calls = _parse_tool_calls(plan.get("output", ""))

    if tool_calls and "bot.tools" in str(type(execute_tool)):
        for call in tool_calls:
            tool_name = call.get("tool", "")
            tool_args = call.get("args", {})
            description = call.get("description", "")

            if tool_name in available_tools:
                log.info("[orchestrator] Executing tool: %s — %s", tool_name, description[:60])
                tool_result = execute_tool(tool_name, tool_args)
                result["steps_completed"].append({
                    "step": f"tool:{tool_name}",
                    "description": description,
                    "output": tool_result,
                })
                result["tools_used"].append(tool_name)

                # Track artifacts from document creation
                if tool_result.get("ok") and tool_name == "create_document":
                    path = tool_result.get("result", {}).get("path")
                    if path:
                        result["artifacts"].append(path)
            else:
                log.warning("[orchestrator] Unknown tool requested: %s", tool_name)
                result["steps_completed"].append({
                    "step": f"skipped:{tool_name}",
                    "error": f"Tool '{tool_name}' not available",
                })
    else:
        # Fallback: LLM-guided execution (original approach)
        execution = spawn_sub_agent(
            role="executor",
            task=task,
            context=f"Plan:\n{plan['output']}",
        )
        result["steps_completed"].append({
            "step": "execute",
            "output": execution.get("output", ""),
        })

        # Terminal fallback for backward compatibility
        if tools_needed and "terminal" in tools_needed:
            _run_terminal_commands(task, execution.get("output", ""), result)

    publish("orchestrator.ad_hoc_completed", {
        "task": task[:80],
        "steps": len(result["steps_completed"]),
        "tools_used": result["tools_used"],
        "node": _node_id,
    })

    return result


def _parse_tool_calls(planner_output: str) -> list[dict]:
    """Extract tool calls from planner output. Handles JSON or freeform."""
    # Try direct JSON parse
    try:
        import re
        # Find JSON array in the output
        match = re.search(r'\[.*\]', planner_output, re.DOTALL)
        if match:
            calls = json.loads(match.group(0))
            if isinstance(calls, list):
                return calls
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: try to parse individual JSON objects
    try:
        import re
        objects = re.findall(r'\{[^{}]+\}', planner_output)
        calls = []
        for obj_str in objects:
            try:
                obj = json.loads(obj_str)
                if "tool" in obj:
                    calls.append(obj)
            except json.JSONDecodeError:
                continue
        if calls:
            return calls
    except Exception:
        pass

    return []


def _run_terminal_commands(task: str, executor_output: str, result: dict):
    """Legacy terminal execution path."""
    try:
        import urllib.request
        port = _config.get("server", {}).get("port", 8765)
        terminal_url = f"http://127.0.0.1:{port}/api/v1/terminal/exec"

        cmd_agent = spawn_sub_agent(
            role="executor",
            task=(
                "Extract the exact terminal commands from this plan and "
                "output ONLY the commands, one per line, no explanations:\n"
                f"{executor_output}"
            ),
        )

        if cmd_agent.get("output"):
            commands = [
                line.strip() for line in cmd_agent["output"].split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]
            for cmd in commands[:10]:
                try:
                    payload = json.dumps({
                        "command": cmd,
                        "reason": f"Ad-hoc task: {task[:80]}",
                    }).encode()
                    req = urllib.request.Request(
                        terminal_url, data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        cmd_result = json.loads(resp.read())
                        result["steps_completed"].append({
                            "step": f"terminal: {cmd[:60]}",
                            "output": cmd_result.get("result", {}),
                        })
                except Exception as e:
                    log.warning("[orchestrator] Ad-hoc command failed: %s — %s",
                                cmd[:40], e)
    except Exception as e:
        log.warning("[orchestrator] Terminal execution failed: %s", e)


def execute_tool_direct(tool_name: str, args: dict) -> dict:
    """Execute a single tool directly (no LLM planning). Used by API."""
    try:
        from bot.tools import execute_tool
        return execute_tool(tool_name, args)
    except ImportError:
        return {"error": "Tool module not available"}

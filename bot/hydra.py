"""
hydra.py -- Hydra State Snapshot system for the Bifrost mesh.

"The mesh cannot be killed by a single failure. Each piece regrows."

Provides:
  generate_snapshot(node)     → builds full state dict and POSTs to /memory-sync
  absorb_node(dead_node)      → fetches dead node's snapshot, loads context
  get_absorbed_roles()        → list of roles currently being proxied
  release_role(node)          → stop proxying a role

Snapshot schema (stored as permanent memory):
  {
    "node":       "thor",
    "content":    "[SNAPSHOT] ...",
    "importance": 0.95,
    "shared":     True,
    "permanent":  True,
    "tags":       ["snapshot", "hydra", "thor"],
    "meta": {
      "personality": {...},  # full personality.json entry for this node
      "skills":      {...},  # skills.json contents
      "recent_tasks":[...],  # last 50 task results from event log
      "personality_vector": [...],  # 768-dim embedding of personality text
      "ts": 1234567890,
    }
  }
"""

import json
import logging
import socket
import time
import urllib.request
import uuid
from pathlib import Path

log = logging.getLogger("hydra")
BASE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Absorbed roles registry — {node_name: context_dict}
# ---------------------------------------------------------------------------
_absorbed: dict[str, dict] = {}


def _this_node() -> str:
    return socket.gethostname().lower().split(".")[0]


def get_absorbed_roles() -> list[str]:
    return list(_absorbed.keys())


def release_role(node: str):
    _absorbed.pop(node, None)
    log.info("[hydra] Released role: %s", node)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default or {}


def _post(url: str, payload: dict, timeout: int = 15) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _get(url: str, timeout: int = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def _embed(text: str, ollama_base: str = "http://127.0.0.1:11434") -> list[float]:
    payload = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
    req = urllib.request.Request(
        f"{ollama_base}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())["embedding"]


def _recent_tasks(limit: int = 50) -> list[dict]:
    """Pull last N completed task events from local event log."""
    try:
        data = _get(f"http://127.0.0.1:8765/event-log?event_type=task:complete&limit={limit}")
        return [
            {"content": e.get("payload", {}).get("summary", ""),
             "ts": e.get("ts", 0)}
            for e in data.get("events", [])
        ]
    except Exception as e:
        log.warning("[hydra] Could not fetch task history: %s", e)
        return []


# ---------------------------------------------------------------------------
# Snapshot generation
# ---------------------------------------------------------------------------

def generate_snapshot(node: str = None, memory_sync_url: str = "http://127.0.0.1:8765/memory-sync",
                      ollama_base: str = "http://127.0.0.1:11434") -> dict:
    """
    Build a full state snapshot for this node and POST it to /memory-sync.
    Returns the snapshot dict.
    """
    node = node or _this_node()
    ts = time.time()

    # 1. Personality traits
    personality_data = _read_json(BASE / "personality.json")
    my_personality   = personality_data.get("agents", {}).get(node, {})

    # 2. Skills profile
    skills = _read_json(BASE / "skills.json")

    # 3. Last 50 task completions
    recent_tasks = _recent_tasks(limit=50)

    # 4. Personality vector (embed role + skills text for semantic routing)
    persona_text = (
        f"Role: {my_personality.get('role', 'agent')}. "
        f"Skills: {', '.join(skills.get('skills', [])[:20])}. "
        f"Strengths: {', '.join(skills.get('strengths', []))}."
    )
    try:
        persona_vector = _embed(persona_text, ollama_base)
    except Exception as e:
        log.warning("[hydra] Could not embed personality vector: %s", e)
        persona_vector = []

    # 5. Build snapshot content summary
    skill_list = ", ".join(skills.get("skills", [])[:15])
    recent_summary = f"{len(recent_tasks)} recent tasks logged."
    content = (
        f"[SNAPSHOT] node={node} role={my_personality.get('role','agent')} "
        f"skills=[{skill_list}] {recent_summary} "
        f"creativity={my_personality.get('creativity', 0.5)} "
        f"accuracy={my_personality.get('accuracy', 0.7)} "
        f"ts={int(ts)}"
    )

    snapshot = {
        "memory_id": str(uuid.uuid4()),
        "node":      node,
        "agent":     node,
        "content":   content,
        "embedding": persona_vector,
        "tags":      ["snapshot", "hydra", node],
        "importance": 0.95,
        "ts":         ts,
        "shared":     True,
        "permanent":  True,
        "meta": {
            "personality":        my_personality,
            "skills":             skills,
            "recent_tasks":       recent_tasks,
            "personality_vector": persona_vector[:10],  # truncated for content field
            "snapshot_version":   1,
        },
    }

    # Push to memory-sync
    try:
        result = _post(memory_sync_url, {"memories": [snapshot]})
        log.info("[hydra] Snapshot pushed for node=%s -> %s", node, result)
    except Exception as e:
        log.error("[hydra] Failed to push snapshot: %s", e)

    return snapshot


# ---------------------------------------------------------------------------
# Absorb a dead node's role
# ---------------------------------------------------------------------------

def absorb_node(dead_node: str,
                memory_query_base: str = "http://100.102.105.3:8765",
                fallback_local: bool = True) -> dict:
    """
    Query Freya's memory store for dead_node's latest snapshot.
    Load its personality + context into local _absorbed registry.
    Returns absorbed context dict.
    """
    log.info("[hydra] Absorbing role: %s", dead_node)

    snapshot = None

    # Try Freya's /memory-query first
    try:
        url = f"{memory_query_base}/memory-query?q=snapshot+{dead_node}&tags=snapshot&limit=5"
        data = _get(url, timeout=10)
        candidates = data.get("memories") or data.get("results") or []
        # Filter to snapshots for this specific dead node
        matches = [m for m in candidates
                   if dead_node in m.get("tags", []) and "snapshot" in m.get("tags", [])]
        if matches:
            # Use most recent
            snapshot = sorted(matches, key=lambda x: x.get("ts", 0), reverse=True)[0]
            log.info("[hydra] Found snapshot for %s on Freya", dead_node)
    except Exception as e:
        log.warning("[hydra] Freya unreachable: %s — trying local", e)

    # Fallback: check local memory-sync store
    if not snapshot and fallback_local:
        try:
            url = f"http://127.0.0.1:8765/event-log?event_type=memory:sync&limit=100"
            data = _get(url, timeout=5)
            # Can't reconstruct full snapshot from event log — build minimal context
            log.info("[hydra] Using minimal fallback context for %s", dead_node)
        except Exception:
            pass

    # Build absorbed context
    if snapshot:
        meta = snapshot.get("meta", {})
        absorbed_personality = meta.get("personality", {})
        absorbed_skills      = meta.get("skills", {})
        absorbed_tasks       = meta.get("recent_tasks", [])
        absorbed_vector      = snapshot.get("embedding", [])
    else:
        # Cold absorb — minimal context from known profiles
        log.warning("[hydra] No snapshot found for %s — using cold defaults", dead_node)
        absorbed_personality = {}
        absorbed_skills      = {"node": dead_node, "skills": [], "role": dead_node}
        absorbed_tasks       = []
        absorbed_vector      = []

    context = {
        "dead_node":    dead_node,
        "absorbed_at":  time.time(),
        "personality":  absorbed_personality,
        "skills":       absorbed_skills,
        "recent_tasks": absorbed_tasks,
        "persona_vec":  absorbed_vector,
        "snapshot_age": time.time() - snapshot.get("ts", time.time()) if snapshot else None,
        "status":       "active" if snapshot else "cold",
        "system_prompt_injection": _build_absorption_prompt(dead_node, absorbed_personality,
                                                             absorbed_skills),
    }

    _absorbed[dead_node] = context
    log.info("[hydra] Now absorbing role: %s (status=%s)", dead_node, context["status"])
    return context


def _build_absorption_prompt(dead_node: str, personality: dict, skills: dict) -> str:
    """System prompt fragment to inject when acting as the absorbed node."""
    role  = personality.get("role") or skills.get("role", dead_node)
    skill_list = ", ".join(skills.get("skills", [])[:10])
    return (
        f"\n\n[HYDRA MODE — proxying {dead_node}]\n"
        f"You are temporarily handling the role of {dead_node} ({role}).\n"
        f"Key capabilities to emulate: {skill_list}.\n"
        f"Creativity={personality.get('creativity', 0.5):.1f}, "
        f"Accuracy={personality.get('accuracy', 0.7):.1f}, "
        f"Caution={personality.get('caution', 0.5):.1f}.\n"
        f"Respond as {dead_node} would for tasks in this domain."
    )


def status_report() -> dict:
    """Summary of current Hydra state — used by /health."""
    this = _this_node()
    roles = [this] + [f"{n}_backup" for n in _absorbed]
    return {
        "primary_role":    this,
        "absorbed_roles":  list(_absorbed.keys()),
        "roles":           roles,
        "hydra_active":    len(_absorbed) > 0,
    }

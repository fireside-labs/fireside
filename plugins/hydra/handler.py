"""
hydra plugin — Fracture Resilience for the Valhalla Mesh.

Ported from V1 bot/hydra.py (355 lines).
"The mesh cannot be killed by a single failure. Each piece regrows."

When a node dies, another node absorbs its role:
  1. Generate state snapshots → push to mesh
  2. When watchdog detects a dead node → absorb its role
  3. Inject absorbed personality into system prompts
  4. Release when the original node recovers
"""
from __future__ import annotations

import importlib.util
import json
import logging
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.hydra")

# ---------------------------------------------------------------------------
# Configuration (set at register_routes)
# ---------------------------------------------------------------------------
_NODE_ID = "unknown"
_BASE_DIR = Path(".")
_MESH_NODES: dict = {}
_AUTH_TOKEN = ""
_OLLAMA_BASE = "http://127.0.0.1:11434"

# Absorbed roles registry: {node_name: context_dict}
_absorbed: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _embed(text: str) -> Optional[list]:
    """Embed text via Ollama nomic-embed-text."""
    try:
        payload = json.dumps({"model": "nomic-embed-text", "prompt": text[:4000]}).encode()
        req = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("embedding")
    except Exception as e:
        log.debug("[hydra] Embed failed: %s", e)
        return None


def _post_json(url: str, payload: dict, timeout: int = 15) -> Optional[dict]:
    """POST JSON to a URL. Returns response dict or None."""
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        log.debug("[hydra] POST to %s failed: %s", url, e)
        return None


def _get_json(url: str, timeout: int = 10) -> Optional[dict]:
    """GET JSON from a URL. Returns dict or None."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _publish_event(topic: str, payload: dict) -> None:
    """Publish to event bus if available."""
    try:
        eb_path = Path(__file__).parent.parent / "event-bus" / "handler.py"
        if eb_path.exists():
            spec = importlib.util.spec_from_file_location("eb_h", str(eb_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.publish(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Snapshot generation
# ---------------------------------------------------------------------------

def generate_snapshot() -> dict:
    """Build a full state snapshot for this node.

    Captures: soul files, current model, plugin list, recent events.
    Pushes to all mesh peers for storage.
    """
    ts = int(time.time())

    # 1. Read soul files
    soul_content = {}
    soul_dir = _BASE_DIR / "mesh" / "souls"
    if soul_dir.exists():
        for prefix in ("IDENTITY", "SOUL", "USER"):
            path = soul_dir / f"{prefix}.{_NODE_ID}.md"
            if path.exists():
                soul_content[prefix] = path.read_text(encoding="utf-8")[:2000]

    # 2. Current status
    status = _get_json(f"http://127.0.0.1:8765/api/v1/status") or {}

    # 3. Plugin list
    plugins = _get_json(f"http://127.0.0.1:8765/api/v1/plugins") or {}

    # 4. Recent events (last 20)
    events = []
    try:
        eb_path = Path(__file__).parent.parent / "event-bus" / "handler.py"
        if eb_path.exists():
            spec = importlib.util.spec_from_file_location("eb_h", str(eb_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                events = mod.get_log(limit=20)
    except Exception:
        pass

    # 5. Personality vector (embed soul text for semantic routing)
    persona_text = soul_content.get("IDENTITY", "")[:500]
    persona_vector = _embed(persona_text) if persona_text else None

    # 6. Build snapshot
    snapshot = {
        "snapshot_id": f"snap_{uuid.uuid4().hex[:12]}",
        "node": _NODE_ID,
        "ts": ts,
        "soul": soul_content,
        "status": {
            "role": status.get("role", "unknown"),
            "model": status.get("model", "unknown"),
            "uptime_seconds": status.get("uptime_seconds", 0),
            "plugins_loaded": status.get("plugins_loaded", 0),
        },
        "plugins": [p.get("name", "") for p in plugins.get("plugins", [])],
        "recent_events": len(events),
        "persona_vector_len": len(persona_vector) if persona_vector else 0,
    }

    # 7. Push to mesh peers
    pushed_to = []
    for name, info in _MESH_NODES.items():
        if name == _NODE_ID:
            continue
        ip = info.get("ip", "")
        port = info.get("port", 8765)
        if ip:
            result = _post_json(
                f"http://{ip}:{port}/api/v1/hydra/receive-snapshot",
                {"snapshot": snapshot, "auth_token": _AUTH_TOKEN},
                timeout=10,
            )
            if result:
                pushed_to.append(name)

    snapshot["pushed_to"] = pushed_to

    # 8. Save locally
    snapshot_dir = _BASE_DIR / "war_room_data" / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshot_dir / f"{_NODE_ID}_latest.json"
    snapshot_file.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    # 9. Emit event
    _publish_event("hydra.snapshot", {
        "node": _NODE_ID,
        "snapshot_id": snapshot["snapshot_id"],
        "pushed_to": pushed_to,
    })

    log.info("[hydra] Snapshot generated: %s (pushed to %d peers)",
             snapshot["snapshot_id"], len(pushed_to))

    return snapshot


# ---------------------------------------------------------------------------
# Role absorption
# ---------------------------------------------------------------------------

def absorb_node(dead_node: str) -> dict:
    """Absorb a dead node's role.

    1. Check for stored snapshot of the dead node
    2. Load its soul files and context
    3. Build system prompt injection
    4. Register in absorbed roles
    """
    log.info("[hydra] Absorbing role: %s", dead_node)

    # 1. Check for stored snapshot
    snapshot = None
    snapshot_dir = _BASE_DIR / "war_room_data" / "snapshots"
    snapshot_file = snapshot_dir / f"{dead_node}_latest.json"

    if snapshot_file.exists():
        try:
            snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
            log.info("[hydra] Found stored snapshot for %s", dead_node)
        except Exception:
            pass

    # 2. Try fetching from other mesh peers
    if not snapshot:
        for name, info in _MESH_NODES.items():
            if name == _NODE_ID or name == dead_node:
                continue
            ip = info.get("ip", "")
            port = info.get("port", 8765)
            if ip:
                data = _get_json(
                    f"http://{ip}:{port}/api/v1/hydra/get-snapshot/{dead_node}",
                )
                if data and data.get("snapshot"):
                    snapshot = data["snapshot"]
                    log.info("[hydra] Retrieved snapshot for %s from %s", dead_node, name)
                    break

    # 3. Build absorbed context
    soul_content = {}
    if snapshot:
        soul_content = snapshot.get("soul", {})

    # Build system prompt injection
    prompt_injection = _build_absorption_prompt(
        dead_node,
        soul_content,
        snapshot.get("status", {}) if snapshot else {},
    )

    context = {
        "dead_node": dead_node,
        "absorbed_at": time.time(),
        "status": "active" if snapshot else "cold",
        "snapshot_age": time.time() - snapshot.get("ts", time.time()) if snapshot else None,
        "soul": soul_content,
        "system_prompt_injection": prompt_injection,
        "plugins": snapshot.get("plugins", []) if snapshot else [],
    }

    _absorbed[dead_node] = context

    # 4. Emit event
    _publish_event("hydra.absorbed", {
        "absorber": _NODE_ID,
        "dead_node": dead_node,
        "status": context["status"],
    })

    log.info("[hydra] Now absorbing role: %s (status=%s)", dead_node, context["status"])
    return context


def release_role(node: str) -> dict:
    """Stop proxying a node's role."""
    if node not in _absorbed:
        return {"ok": False, "reason": f"{node} is not being absorbed"}

    context = _absorbed.pop(node)

    _publish_event("hydra.released", {
        "absorber": _NODE_ID,
        "released_node": node,
        "absorbed_for_seconds": time.time() - context.get("absorbed_at", time.time()),
    })

    log.info("[hydra] Released role: %s", node)
    return {"ok": True, "released": node}


def _build_absorption_prompt(dead_node: str, soul: dict, status: dict) -> str:
    """System prompt fragment for acting as the dead node."""
    role = status.get("role", dead_node)
    model = status.get("model", "unknown")

    identity = soul.get("IDENTITY", "")
    personality = soul.get("SOUL", "")

    # Extract key traits from SOUL file
    traits = ""
    if personality:
        # Look for ## Core Traits section
        import re
        match = re.search(r"## Core Traits\n(.+?)(?=\n## |\Z)", personality, re.DOTALL)
        if match:
            traits = match.group(1).strip()[:500]

    prompt = (
        f"\n\n[HYDRA MODE — proxying {dead_node}]\n"
        f"You are temporarily handling the role of {dead_node} ({role}).\n"
    )
    if identity:
        prompt += f"Their identity:\n{identity[:300]}\n"
    if traits:
        prompt += f"Their core traits:\n{traits}\n"
    prompt += f"Respond as {dead_node} would for tasks in this domain.\n"

    return prompt


def get_status() -> dict:
    """Current Hydra state."""
    return {
        "node": _NODE_ID,
        "absorbed_roles": list(_absorbed.keys()),
        "hydra_active": len(_absorbed) > 0,
        "absorbed_details": {
            name: {
                "status": ctx.get("status", "unknown"),
                "absorbed_at": ctx.get("absorbed_at"),
                "age_s": round(time.time() - ctx.get("absorbed_at", time.time()), 1),
            }
            for name, ctx in _absorbed.items()
        },
    }


def get_system_prompt_injection() -> str:
    """Return combined prompt injection for all absorbed roles."""
    if not _absorbed:
        return ""
    parts = []
    for name, ctx in _absorbed.items():
        injection = ctx.get("system_prompt_injection", "")
        if injection:
            parts.append(injection)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Stored snapshots from peers
# ---------------------------------------------------------------------------
_received_snapshots: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AbsorbRequest(BaseModel):
    dead_node: str


class ReleaseRequest(BaseModel):
    node: str


class SnapshotReceivePayload(BaseModel):
    snapshot: dict
    auth_token: str = ""


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    """Called by plugin_loader."""
    global _NODE_ID, _BASE_DIR, _MESH_NODES, _AUTH_TOKEN, _OLLAMA_BASE

    _NODE_ID = config.get("node", {}).get("name", "unknown")
    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MESH_NODES = config.get("mesh", {}).get("nodes", {})
    _AUTH_TOKEN = config.get("mesh", {}).get("auth_token", "")

    models = config.get("models", {})
    providers = models.get("providers", {})
    if "llama" in providers:
        url = providers["llama"].get("url", _OLLAMA_BASE)
        if "/v1" in url:
            url = url.replace("/v1", "")
        _OLLAMA_BASE = url

    router = APIRouter(tags=["hydra"])

    @router.post("/api/v1/hydra/snapshot")
    async def create_snapshot():
        """Generate a state snapshot and push to mesh."""
        return generate_snapshot()

    @router.post("/api/v1/hydra/absorb")
    async def absorb(req: AbsorbRequest):
        """Absorb a dead node's role."""
        return absorb_node(req.dead_node)

    @router.get("/api/v1/hydra/status")
    async def hydra_status():
        """Current Hydra state (absorbed roles)."""
        return get_status()

    @router.post("/api/v1/hydra/release")
    async def release(req: ReleaseRequest):
        """Stop proxying a node's role."""
        return release_role(req.node)

    @router.post("/api/v1/hydra/receive-snapshot")
    async def receive_snapshot(payload: SnapshotReceivePayload):
        """Receive a snapshot from a peer node."""
        import hmac as _hmac
        if _AUTH_TOKEN and not _hmac.compare_digest(payload.auth_token, _AUTH_TOKEN):
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid auth token")

        snapshot = payload.snapshot
        node = snapshot.get("node", "unknown")

        # Store it
        snapshot_dir = _BASE_DIR / "war_room_data" / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / f"{node}_latest.json").write_text(
            json.dumps(snapshot, indent=2, default=str), encoding="utf-8"
        )

        _received_snapshots[node] = snapshot
        log.info("[hydra] Received snapshot from %s", node)

        return {"ok": True, "stored": node}

    @router.get("/api/v1/hydra/get-snapshot/{node_name}")
    async def get_snapshot(node_name: str):
        """Get stored snapshot for a node."""
        if node_name in _received_snapshots:
            return {"snapshot": _received_snapshots[node_name]}

        # Check filesystem
        snapshot_file = _BASE_DIR / "war_room_data" / "snapshots" / f"{node_name}_latest.json"
        if snapshot_file.exists():
            try:
                data = json.loads(snapshot_file.read_text(encoding="utf-8"))
                return {"snapshot": data}
            except Exception:
                pass

        return {"snapshot": None}

    app.include_router(router)
    log.info("[hydra] Plugin loaded for node=%s, mesh_peers=%d",
             _NODE_ID, len(_MESH_NODES))

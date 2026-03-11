"""
belief-shadows plugin — Theory of Mind / Peer Belief Modeling.

Ported from V1 bot/war_room/belief_shadow.py (319 lines).

Tracks what each peer node believes (hypotheses they've shared/confirmed)
to detect belief-reality gaps and avoid sharing redundant info.
"""
from __future__ import annotations

import json
import logging
import time
from collections import deque
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.belief-shadows")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_BASE_DIR = Path(".")
_MESH_NODES: dict = {}

# Shadows: {node_id: {confirmed: [...], shared: [...], refuted: [...], last_updated: ts}}
_shadows: dict[str, dict] = {}
_MAX_ITEMS = 200


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


def _shadow_file() -> Path:
    return _BASE_DIR / "war_room_data" / "peer_shadows.json"


def _get_shadow(node_id: str) -> dict:
    """Get or create a shadow for a node."""
    if node_id not in _shadows:
        _shadows[node_id] = {
            "confirmed": [],
            "shared": [],
            "refuted": [],
            "last_updated": 0,
        }
    return _shadows[node_id]


def _save_shadows() -> None:
    """Persist shadows to JSON."""
    try:
        out = _shadow_file()
        out.parent.mkdir(parents=True, exist_ok=True)
        # Convert deques to lists for JSON
        data = {}
        for nid, shadow in _shadows.items():
            data[nid] = {
                "confirmed": list(shadow.get("confirmed", []))[-_MAX_ITEMS:],
                "shared": list(shadow.get("shared", []))[-_MAX_ITEMS:],
                "refuted": list(shadow.get("refuted", []))[-_MAX_ITEMS:],
                "last_updated": shadow.get("last_updated", 0),
            }
        out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        log.debug("[belief-shadows] Save failed: %s", e)


def _load_shadows() -> None:
    """Load shadows from JSON."""
    global _shadows
    path = _shadow_file()
    if path.exists():
        try:
            _shadows = json.loads(path.read_text(encoding="utf-8"))
            log.info("[belief-shadows] Loaded %d peer shadows", len(_shadows))
        except Exception:
            _shadows = {}


# ---------------------------------------------------------------------------
# Shadow update API
# ---------------------------------------------------------------------------

def record_confirmed(node_id: str, hyp_id: str, text: str, confidence: float) -> None:
    """Record a belief a peer has confirmed."""
    shadow = _get_shadow(node_id)
    shadow["confirmed"].append({
        "id": hyp_id, "text": text[:300], "confidence": confidence,
        "ts": int(time.time()),
    })
    # Keep bounded
    if len(shadow["confirmed"]) > _MAX_ITEMS:
        shadow["confirmed"] = shadow["confirmed"][-_MAX_ITEMS:]
    shadow["last_updated"] = int(time.time())
    _save_shadows()
    _publish("belief.updated", {"node": node_id, "action": "confirmed", "hyp_id": hyp_id})


def record_shared(sender: str, hyp_id: str, text: str) -> None:
    """Record a hypothesis received from a peer."""
    shadow = _get_shadow(sender)
    shadow["shared"].append({
        "id": hyp_id, "text": text[:300], "ts": int(time.time()),
    })
    if len(shadow["shared"]) > _MAX_ITEMS:
        shadow["shared"] = shadow["shared"][-_MAX_ITEMS:]
    shadow["last_updated"] = int(time.time())
    _save_shadows()


def record_refuted(node_id: str, hyp_id: str, text: str) -> None:
    """Record a belief a peer has refuted."""
    shadow = _get_shadow(node_id)
    shadow["refuted"].append({
        "id": hyp_id, "text": text[:300], "ts": int(time.time()),
    })
    if len(shadow["refuted"]) > _MAX_ITEMS:
        shadow["refuted"] = shadow["refuted"][-_MAX_ITEMS:]
    shadow["last_updated"] = int(time.time())
    _save_shadows()


def novelty_score(hyp_id: str, hyp_text: str, peer_node: str) -> float:
    """Return 0-1 novelty score for a hypothesis relative to a peer."""
    shadow = _get_shadow(peer_node)

    # Check if already shared or confirmed
    known_ids = set()
    for item in shadow.get("confirmed", []):
        known_ids.add(item.get("id", ""))
    for item in shadow.get("shared", []):
        known_ids.add(item.get("id", ""))

    if hyp_id in known_ids:
        return 0.0

    # Check refuted — sharing something they refuted is low-value
    for item in shadow.get("refuted", []):
        if item.get("id") == hyp_id:
            return 0.1

    return 1.0


def get_shadow_summary(node_id: str) -> dict:
    """Return shadow summary for a node."""
    shadow = _get_shadow(node_id)
    return {
        "node": node_id,
        "confirmed_count": len(shadow.get("confirmed", [])),
        "shared_count": len(shadow.get("shared", [])),
        "refuted_count": len(shadow.get("refuted", [])),
        "last_updated": shadow.get("last_updated", 0),
        "recent_confirmed": shadow.get("confirmed", [])[-5:],
        "recent_refuted": shadow.get("refuted", [])[-5:],
    }


def get_all_shadows() -> dict:
    """Summary of all tracked peer shadows."""
    return {
        "peers": {
            nid: {
                "confirmed": len(s.get("confirmed", [])),
                "shared": len(s.get("shared", [])),
                "refuted": len(s.get("refuted", [])),
                "last_updated": s.get("last_updated", 0),
            }
            for nid, s in _shadows.items()
        },
        "total_peers": len(_shadows),
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class UpdateRequest(BaseModel):
    node_id: str
    hyp_id: str
    text: str
    action: str = "confirmed"  # confirmed / shared / refuted
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _MESH_NODES

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MESH_NODES = config.get("mesh", {}).get("nodes", {})

    _load_shadows()

    router = APIRouter(tags=["belief-shadows"])

    @router.get("/api/v1/belief-shadows")
    async def api_all():
        return get_all_shadows()

    @router.get("/api/v1/belief-shadows/{node_id}")
    async def api_node(node_id: str):
        return get_shadow_summary(node_id)

    @router.post("/api/v1/belief-shadows/update")
    async def api_update(req: UpdateRequest):
        if req.action == "confirmed":
            record_confirmed(req.node_id, req.hyp_id, req.text, req.confidence)
        elif req.action == "shared":
            record_shared(req.node_id, req.hyp_id, req.text)
        elif req.action == "refuted":
            record_refuted(req.node_id, req.hyp_id, req.text)
        return {"ok": True}

    app.include_router(router)
    log.info("[belief-shadows] Plugin loaded. %d peer shadows.", len(_shadows))

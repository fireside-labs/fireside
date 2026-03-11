"""
marketplace/handler.py — Agent Marketplace API routes.

Endpoints:
  POST /api/v1/agents/export       — Package agent as .valhalla zip
  GET  /api/v1/agents/export/{name} — Download .valhalla package
  POST /api/v1/agents/import       — Upload and install .valhalla package
  GET  /api/v1/agents              — List installed agents
  GET  /api/v1/marketplace         — Browse available agents (registry)
  GET  /api/v1/marketplace/{id}    — Agent detail
  POST /api/v1/marketplace/publish — Submit agent to registry
  POST /api/v1/marketplace/{id}/review — Leave a review
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

log = logging.getLogger("valhalla.marketplace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_BASE_DIR = Path(".")
_SOUL_CONFIG: dict = {}
_EXPORT_DIR = Path(".")
_REGISTRY_PATH = Path(".")


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Registry (local JSON for now — later: hosted API)
# ---------------------------------------------------------------------------

def _registry_file() -> Path:
    return _REGISTRY_PATH / "marketplace_registry.json"


def _load_registry() -> list:
    f = _registry_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_registry(entries: list) -> None:
    f = _registry_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    agent_name: str
    version: str = "1.0.0"
    description: str = ""
    price: float = 0.0
    min_confidence: float = 0.7


class PublishRequest(BaseModel):
    agent_name: str
    description: str
    category: str = "general"
    price: float = 0.0
    tags: list = []


class ReviewRequest(BaseModel):
    rating: int  # 1-5 stars
    text: str = ""
    reviewer: str = "anonymous"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _SOUL_CONFIG, _EXPORT_DIR, _REGISTRY_PATH

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _SOUL_CONFIG = config.get("soul", {})

    mkt_cfg = config.get("marketplace", {})
    _EXPORT_DIR = _BASE_DIR / mkt_cfg.get("export_dir", "marketplace_exports")
    _REGISTRY_PATH = _BASE_DIR / mkt_cfg.get("registry_path", "war_room_data")

    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    router = APIRouter(tags=["marketplace"])

    # --- Agent Export ---

    @router.post("/api/v1/agents/export")
    async def api_export(req: ExportRequest):
        """Package agent as .valhalla zip."""
        from plugins.marketplace.exporter import export_agent

        zip_bytes = export_agent(
            agent_name=req.agent_name,
            base_dir=_BASE_DIR,
            soul_config=_SOUL_CONFIG,
            version=req.version,
            description=req.description,
            price=req.price,
            min_confidence=req.min_confidence,
        )

        if not zip_bytes:
            raise HTTPException(status_code=500, detail="Export failed")

        # Save to disk
        filename = f"{req.agent_name}-v{req.version}.valhalla"
        out = _EXPORT_DIR / filename
        out.write_bytes(zip_bytes)

        sha256 = hashlib.sha256(zip_bytes).hexdigest()

        _publish("agent.exported", {
            "name": req.agent_name, "version": req.version,
            "size": len(zip_bytes), "sha256": sha256,
        })

        return {
            "ok": True,
            "filename": filename,
            "size_bytes": len(zip_bytes),
            "sha256": sha256,
            "download_url": f"/api/v1/agents/export/{req.agent_name}",
        }

    @router.get("/api/v1/agents/export/{name}")
    async def api_download(name: str):
        """Download .valhalla package."""
        # Find the latest version
        matches = sorted(_EXPORT_DIR.glob(f"{name}*.valhalla"), reverse=True)
        if not matches:
            raise HTTPException(status_code=404, detail=f"No export found for '{name}'")

        data = matches[0].read_bytes()
        return Response(
            content=data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{matches[0].name}"',
                "X-SHA256": hashlib.sha256(data).hexdigest(),
            },
        )

    # --- Agent Import ---

    @router.post("/api/v1/agents/import")
    async def api_import(file: UploadFile = File(...)):
        """Upload and install .valhalla package."""
        from plugins.marketplace.importer import import_agent

        contents = await file.read()
        result = import_agent(contents, _BASE_DIR)

        if result.get("ok"):
            _publish("agent.imported", {
                "name": result.get("agent_name", ""),
                "version": result.get("version", ""),
                "files": result.get("files_installed", 0),
            })

        return result

    @router.get("/api/v1/agents")
    async def api_list_agents():
        """List installed agents."""
        from plugins.marketplace.importer import list_agents
        agents = list_agents(_BASE_DIR)
        return {"agents": agents, "count": len(agents)}

    # --- Marketplace (Registry) ---

    @router.get("/api/v1/marketplace")
    async def api_marketplace(category: Optional[str] = None):
        """Browse available agents."""
        registry = _load_registry()
        if category:
            registry = [
                a for a in registry
                if a.get("category", "general") == category
            ]
        return {"agents": registry, "count": len(registry)}

    @router.get("/api/v1/marketplace/{agent_id}")
    async def api_agent_detail(agent_id: str):
        """Get agent details from registry."""
        registry = _load_registry()
        for agent in registry:
            if agent.get("id") == agent_id or agent.get("name") == agent_id:
                return agent
        raise HTTPException(status_code=404, detail="Agent not found in marketplace")

    @router.post("/api/v1/marketplace/publish")
    async def api_publish(req: PublishRequest):
        """Submit agent to registry."""
        # Check export exists
        exports = list(_EXPORT_DIR.glob(f"{req.agent_name}*.valhalla"))
        if not exports:
            raise HTTPException(status_code=400, detail="Export the agent first")

        latest = exports[-1]
        sha256 = hashlib.sha256(latest.read_bytes()).hexdigest()

        entry = {
            "id": f"{req.agent_name}-{sha256[:8]}",
            "name": req.agent_name,
            "description": req.description,
            "category": req.category,
            "price": req.price,
            "tags": req.tags,
            "size_bytes": latest.stat().st_size,
            "sha256": sha256,
            "published_at": int(time.time()),
            "reviews": [],
            "avg_rating": 0.0,
        }

        registry = _load_registry()
        # Replace if already published
        registry = [a for a in registry if a.get("name") != req.agent_name]
        registry.append(entry)
        _save_registry(registry)

        _publish("agent.published", {
            "name": req.agent_name, "category": req.category,
        })

        return {"ok": True, "id": entry["id"]}

    @router.post("/api/v1/marketplace/{agent_id}/review")
    async def api_review(agent_id: str, req: ReviewRequest):
        """Leave a review for an agent."""
        if req.rating < 1 or req.rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be 1-5")

        registry = _load_registry()
        for agent in registry:
            if agent.get("id") == agent_id or agent.get("name") == agent_id:
                review = {
                    "rating": req.rating,
                    "text": req.text[:500],
                    "reviewer": req.reviewer[:50],
                    "ts": int(time.time()),
                }
                if "reviews" not in agent:
                    agent["reviews"] = []
                agent["reviews"].append(review)

                # Recalculate average
                ratings = [r["rating"] for r in agent["reviews"]]
                agent["avg_rating"] = round(sum(ratings) / len(ratings), 1)

                _save_registry(registry)

                _publish("agent.reviewed", {
                    "agent": agent_id, "rating": req.rating,
                })

                return {"ok": True, "avg_rating": agent["avg_rating"]}

        raise HTTPException(status_code=404, detail="Agent not found")

    app.include_router(router)
    log.info("[marketplace] Plugin loaded. Exports: %s", _EXPORT_DIR)

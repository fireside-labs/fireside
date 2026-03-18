"""
model-switch plugin — Switch LLM models via API or chat alias.

Ported from V1 bifrost_local.py (lines 1130-1205).
Aliases are now read from valhalla.yaml instead of hardcoded.
"""
from __future__ import annotations

import logging
import subprocess
import threading
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

log = logging.getLogger("valhalla.plugin.model-switch")

router = APIRouter(tags=["model-switch"])

# Will be populated from config at registration time
_aliases: dict[str, str] = {}
_current_model: str = ""


class SwitchRequest(BaseModel):
    alias: Optional[str] = None
    model: Optional[str] = None


class SwitchResponse(BaseModel):
    ok: bool = True
    switching_to: str
    previous: str


# Rebuild models to resolve forward references from `from __future__ import annotations`
SwitchRequest.model_rebuild()
SwitchResponse.model_rebuild()


def _do_switch(model_id: str) -> None:
    """Background: switch model via brain_manager (replaces OpenClaw gateway)."""
    from pathlib import Path

    try:
        from bot.brain_manager import switch_model, get_status

        # Resolve model_id to a GGUF path
        # Check common locations for a matching .gguf file
        model_path = None
        search_dirs = [
            Path.home() / ".fireside" / "models",
            Path(".") / "models",
        ]
        for d in search_dirs:
            if d.exists():
                for f in d.glob("*.gguf"):
                    if model_id.replace("/", "_") in f.stem.lower() or \
                       model_id.split("/")[-1].lower() in f.stem.lower():
                        model_path = f
                        break
            if model_path:
                break

        if model_path:
            switch_model(model_path)
            log.info("[model-switch] Switched to %s via brain_manager", model_path.name)
        else:
            log.warning("[model-switch] No GGUF found for model_id '%s' — "
                        "download it from the Brain Lab first", model_id)

    except ImportError:
        log.error("[model-switch] brain_manager not available")
    except Exception as e:
        log.error("[model-switch] switch failed: %s", e)



def get_current_model() -> str:
    """Return the currently active model identifier."""
    return _current_model


def get_aliases() -> dict[str, str]:
    """Return the alias → model mapping."""
    return dict(_aliases)


def register_routes(app, config: dict) -> None:
    """Called by plugin_loader at startup."""
    global _aliases, _current_model

    models_cfg = config.get("models", {})
    _aliases.update(models_cfg.get("aliases", {}))
    _current_model = models_cfg.get("default", "")

    @router.post("/model-switch", response_model=SwitchResponse)
    async def switch_model(req: SwitchRequest):
        global _current_model

        alias = (req.alias or "").lower().strip()
        model_id = req.model or _aliases.get(alias)

        if not model_id:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown alias '{alias}'. Valid: {list(_aliases.keys())}",
            )

        previous = _current_model
        _current_model = model_id

        # Fire-and-forget background switch
        threading.Thread(
            target=_do_switch, args=(model_id,),
            daemon=True, name="model-switch",
        ).start()

        log.info("[model-switch] %s → %s (alias: %s)", previous, model_id, alias)
        return SwitchResponse(switching_to=model_id, previous=previous)

    app.include_router(router)
    log.info("[model-switch] Registered (aliases: %s)", list(_aliases.keys()))

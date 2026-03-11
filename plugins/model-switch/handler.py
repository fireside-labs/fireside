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


def _do_switch(model_id: str) -> None:
    """Background: set openclaw config + restart gateway."""
    try:
        subprocess.run(
            ["openclaw", "config", "set",
             "agents.defaults.model.primary", model_id],
            check=True, capture_output=True, timeout=10,
        )
        log.info("[model-switch] Config set → %s", model_id)
    except Exception as e:
        log.error("[model-switch] config set failed: %s", e)
        return

    time.sleep(1)
    try:
        subprocess.run(["pkill", "-f", "openclaw-gateway"], capture_output=True)
        time.sleep(2)
        subprocess.Popen(
            ["nohup", "openclaw", "gateway", "run"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log.info("[model-switch] Gateway restarted with model: %s", model_id)
    except Exception as e:
        log.error("[model-switch] Gateway restart failed: %s", e)


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

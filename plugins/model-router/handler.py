"""
model-router plugin — Smart routing for task-specific model selection.

NEW in V2 (no V1 source — replaces hardcoded CLOUD_MODELS dict from pipeline.py).

Routes tasks to the best model based on config:
  spec     → cloud/glm-5        (structured specs)
  review   → cloud/glm-5        (quality analysis)
  build    → local/default      (bulk iteration — free)
  test     → local/default      (testing — free)
  memory   → cloud/kimi-k2.5    (128K context)
  fallback → local/default

Tracks token spend per model for cost visibility.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.model-router")

# Heimdall security: redact API keys from dashboard-facing endpoints
try:
    from middleware.pipeline_guard import redact_api_keys
except ImportError:
    redact_api_keys = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_ROUTING: dict = {}
_FALLBACK = "local/default"
_COST_TRACKING = True
_MODEL_PROVIDERS: dict = {}
_MODEL_ALIASES: dict = {}

# Token spend tracking: {model_ref: {"tokens_in": N, "tokens_out": N, "calls": N}}
_spend: dict[str, dict] = {}
_spend_lock = threading.Lock()


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Core routing
# ---------------------------------------------------------------------------

def route(task_type: str) -> dict:
    """Given a task type, return the best model config."""
    model_ref = _ROUTING.get(task_type, _ROUTING.get("fallback", _FALLBACK))

    # Parse: "cloud/glm-5" → provider="cloud", model="glm-5"
    if "/" in model_ref:
        provider_key, model_name = model_ref.split("/", 1)
    else:
        provider_key = "llama"
        model_name = model_ref or "default"

    # Resolve "default" from aliases
    if model_name == "default":
        for alias, ref in _MODEL_ALIASES.items():
            if ref:
                model_name = ref.split("/", 1)[-1] if "/" in ref else ref
                break

    provider = _MODEL_PROVIDERS.get(provider_key, {})
    url = provider.get("url", "")
    is_local = provider_key in ("llama", "local") or provider.get("key") == "local"

    result = {
        "task_type": task_type,
        "model_ref": model_ref,
        "provider": provider_key,
        "model": model_name,
        "url": url,
        "is_local": is_local,
        "cost": "free" if is_local else "paid",
    }

    _publish("model.routed", {"task_type": task_type, "model": model_ref})
    return result


def record_usage(model_ref: str, tokens_in: int = 0, tokens_out: int = 0) -> None:
    """Record token usage for a model call."""
    if not _COST_TRACKING:
        return
    with _spend_lock:
        if model_ref not in _spend:
            _spend[model_ref] = {"tokens_in": 0, "tokens_out": 0, "calls": 0}
        _spend[model_ref]["tokens_in"] += tokens_in
        _spend[model_ref]["tokens_out"] += tokens_out
        _spend[model_ref]["calls"] += 1


def get_stats() -> dict:
    """Return token spend per model."""
    with _spend_lock:
        stats = {}
        total_local = 0
        total_cloud = 0

        for ref, usage in _spend.items():
            is_local = ref.startswith("local/") or ref.startswith("llama/")
            total = usage["tokens_in"] + usage["tokens_out"]
            stats[ref] = {
                **usage,
                "total_tokens": total,
                "is_local": is_local,
            }
            if is_local:
                total_local += total
            else:
                total_cloud += total

        return {
            "models": stats,
            "summary": {
                "total_local_tokens": total_local,
                "total_cloud_tokens": total_cloud,
                "local_cost": "free",
                "total_calls": sum(u["calls"] for u in _spend.values()),
            },
            "routing": _ROUTING,
        }


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    task_type: str


class RecordUsageRequest(BaseModel):
    model_ref: str
    tokens_in: int = 0
    tokens_out: int = 0


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _ROUTING, _FALLBACK, _COST_TRACKING, _MODEL_PROVIDERS, _MODEL_ALIASES

    router_cfg = config.get("model_router", {})
    _ROUTING = router_cfg.get("routing", {
        "spec": "cloud/glm-5",
        "review": "cloud/glm-5",
        "regression": "cloud/deepseek",
        "memory": "cloud/kimi-k2.5",
        "build": "local/default",
        "test": "local/default",
        "fallback": "local/default",
    })
    _FALLBACK = router_cfg.get("fallback", "local/default")
    _COST_TRACKING = router_cfg.get("cost_tracking", True)
    _MODEL_PROVIDERS = config.get("models", {}).get("providers", {})
    _MODEL_ALIASES = config.get("models", {}).get("aliases", {})

    _config_ref = config  # keep ref for redaction

    router = APIRouter(tags=["model-router"])

    @router.get("/api/v1/model-router/stats")
    async def api_stats():
        stats = get_stats()
        # Redact any API keys before sending to dashboard
        if redact_api_keys and _config_ref:
            stats["providers"] = redact_api_keys(_config_ref).get("models", {}).get("providers", {})
        return stats

    @router.post("/api/v1/model-router/route")
    async def api_route(req: RouteRequest):
        return route(req.task_type)

    @router.post("/api/v1/model-router/record")
    async def api_record(req: RecordUsageRequest):
        record_usage(req.model_ref, req.tokens_in, req.tokens_out)
        return {"ok": True}

    app.include_router(router)
    log.info("[model-router] Plugin loaded. %d routing rules. Key redaction: %s",
             len(_ROUTING), "active" if redact_api_keys else "unavailable")

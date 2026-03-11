"""
self-model plugin — Default Mode Network / Self-Awareness.

Ported from V1 bot/war_room/self_model.py (305 lines).
During idle time or on POST /reflect, gathers signals about behavior,
generates a self-assessment via LLM, and injects it into system prompts.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

log = logging.getLogger("valhalla.self_model")

# ---------------------------------------------------------------------------
# Configuration (overridden at register_routes)
# ---------------------------------------------------------------------------
_OLLAMA_BASE = "http://127.0.0.1:11434"
_REFLECT_MODEL = "qwen2.5-coder:32b"
_NODE_ID = "unknown"
_BASE_DIR = Path(".")

_SELF_MODEL_FILE = "self_model_{node}.md"
_COOLDOWN_SECONDS = 300   # min time between reflections
_last_reflect_ts: float = 0.0


# ---------------------------------------------------------------------------
# Signal gathering
# ---------------------------------------------------------------------------

def _gather_signals() -> dict:
    """Pull together all available self-knowledge signals.

    Each section is best-effort — missing plugins are silently skipped.
    """
    signals = {}

    # Hypothesis stats
    try:
        import importlib.util
        hp = Path(__file__).parent.parent / "hypotheses" / "handler.py"
        if hp.exists():
            spec = importlib.util.spec_from_file_location("hyp_h", str(hp))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                hyps = mod.get_hypotheses(limit=5, min_confidence=0.5)
                signals["top_hypotheses"] = [
                    h.get("text", "")[:100] for h in hyps
                ] if isinstance(hyps, list) else []
    except Exception:
        pass

    # Prediction stats
    try:
        import importlib.util
        pp = Path(__file__).parent.parent / "predictions" / "handler.py"
        if pp.exists():
            spec = importlib.util.spec_from_file_location("pred_h", str(pp))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                signals["prediction_stats"] = mod.get_stats()
    except Exception:
        pass

    # Working memory status
    try:
        import importlib.util
        wmp = Path(__file__).parent.parent / "working-memory" / "handler.py"
        if wmp.exists():
            spec = importlib.util.spec_from_file_location("wm_h", str(wmp))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                signals["working_memory"] = mod.get_working_memory().status()
    except Exception:
        pass

    # Event bus recent activity
    try:
        import importlib.util
        ebp = Path(__file__).parent.parent / "event-bus" / "handler.py"
        if ebp.exists():
            spec = importlib.util.spec_from_file_location("eb_h", str(ebp))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                recent = mod.get_log(limit=10)
                signals["recent_events"] = [
                    {"topic": e["topic"], "ts": e["ts"]} for e in recent
                ]
    except Exception:
        pass

    signals["node_id"] = _NODE_ID
    signals["ts"] = int(time.time())

    return signals


# ---------------------------------------------------------------------------
# Self-model generation
# ---------------------------------------------------------------------------

def _build_prompt(signals: dict) -> str:
    """Build the LLM prompt for self-reflection."""
    sections = []

    sections.append(f"You are {_NODE_ID}, a node in the Valhalla Mesh.")
    sections.append("Analyze the following signals about your recent behavior "
                    "and generate a concise self-assessment.\n")

    if signals.get("top_hypotheses"):
        sections.append("## Recent Hypotheses (beliefs formed during dream cycles)")
        for h in signals["top_hypotheses"]:
            sections.append(f"  - {h}")

    if signals.get("prediction_stats"):
        ps = signals["prediction_stats"]
        sections.append(f"\n## Prediction Accuracy")
        sections.append(f"  Total: {ps.get('total', 0)}, "
                        f"Avg Error: {ps.get('avg_error', 0):.3f}, "
                        f"Surprise Rate: {ps.get('surprise_rate', 0):.1%}")

    if signals.get("working_memory"):
        wm = signals["working_memory"]
        sections.append(f"\n## Working Memory")
        sections.append(f"  Items: {wm.get('items', 0)}/{wm.get('capacity', 10)}, "
                        f"Hit Rate: {wm.get('hit_rate', 0):.1%}")

    if signals.get("recent_events"):
        sections.append(f"\n## Recent Events")
        for e in signals["recent_events"][:5]:
            sections.append(f"  - {e['topic']}")

    sections.append("\n## Output Format")
    sections.append("Respond with a JSON object:")
    sections.append('{"strengths": [...], "weaknesses": [...], '
                    '"confidence": 0.0-1.0, "summary": "..."}')
    sections.append("Be honest and specific. No generic platitudes.")

    return "\n".join(sections)


def _call_ollama(prompt: str) -> Optional[str]:
    """Call Ollama to generate the self-assessment text."""
    try:
        req = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/generate",
            data=json.dumps({
                "model": _REFLECT_MODEL,
                "prompt": prompt,
                "stream": False,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data.get("response", "")
    except Exception as e:
        log.error("[self-model] Ollama call failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reflect() -> dict:
    """Run a full reflection cycle.

    Gather signals → build prompt → LLM → write self_model_<node>.md
    → publish self_model.updated event.

    Returns a summary dict. Safe to call from a background thread.
    """
    global _last_reflect_ts

    # Cooldown check
    elapsed = time.time() - _last_reflect_ts
    if elapsed < _COOLDOWN_SECONDS:
        return {
            "ok": False,
            "reason": f"Cooldown: {int(_COOLDOWN_SECONDS - elapsed)}s remaining",
        }

    _last_reflect_ts = time.time()

    # Phase 1: Gather signals
    signals = _gather_signals()

    # Phase 2: Build prompt
    prompt = _build_prompt(signals)

    # Phase 3: Call LLM
    raw_response = _call_ollama(prompt)
    if not raw_response:
        return {"ok": False, "reason": "LLM call failed"}

    # Phase 4: Write self-model file
    model_file = _BASE_DIR / "war_room_data" / _SELF_MODEL_FILE.format(node=_NODE_ID)
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_text(raw_response, encoding="utf-8")

    # Phase 5: Parse response
    assessment = {"raw": raw_response}
    try:
        # Try to extract JSON from the response
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start >= 0 and end > start:
            assessment = json.loads(raw_response[start:end])
            assessment["raw"] = raw_response
    except json.JSONDecodeError:
        pass

    # Phase 6: Publish event
    try:
        import importlib.util
        ebp = Path(__file__).parent.parent / "event-bus" / "handler.py"
        if ebp.exists():
            spec = importlib.util.spec_from_file_location("eb_h", str(ebp))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.publish("self_model.updated", {
                    "node": _NODE_ID,
                    "path": str(model_file),
                    "ts": int(time.time()),
                })
    except Exception:
        pass

    log.info("[self-model] Reflection complete for %s", _NODE_ID)

    return {
        "ok": True,
        "node": _NODE_ID,
        "strengths": assessment.get("strengths", []),
        "weaknesses": assessment.get("weaknesses", []),
        "confidence": assessment.get("confidence", 0.0),
        "summary": assessment.get("summary", raw_response[:200]),
    }


def get_current() -> dict:
    """Return current self-model content + metadata."""
    model_file = _BASE_DIR / "war_room_data" / _SELF_MODEL_FILE.format(node=_NODE_ID)

    if not model_file.exists():
        return {
            "exists": False,
            "node": _NODE_ID,
            "message": "No self-model yet. Trigger POST /api/v1/reflect to generate one.",
        }

    content = model_file.read_text(encoding="utf-8")

    # Try to parse as JSON
    assessment = {"raw": content}
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            assessment = json.loads(content[start:end])
            assessment["raw"] = content
    except json.JSONDecodeError:
        pass

    return {
        "exists": True,
        "node": _NODE_ID,
        "strengths": assessment.get("strengths", []),
        "weaknesses": assessment.get("weaknesses", []),
        "confidence": assessment.get("confidence", 0.0),
        "summary": assessment.get("summary", content[:200]),
        "last_updated": model_file.stat().st_mtime,
    }


def get_system_prompt_injection() -> str:
    """Return a compact version of the self-model for system prompt prepending.

    Empty string if no self-model exists yet.
    """
    model_file = _BASE_DIR / "war_room_data" / _SELF_MODEL_FILE.format(node=_NODE_ID)

    if not model_file.exists():
        return ""

    content = model_file.read_text(encoding="utf-8")

    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            strengths = ", ".join(data.get("strengths", [])[:3])
            weaknesses = ", ".join(data.get("weaknesses", [])[:3])
            return (
                f"[SELF-MODEL] Strengths: {strengths}. "
                f"Weaknesses: {weaknesses}. "
                f"Confidence: {data.get('confidence', '?')}"
            )
    except Exception:
        pass

    return f"[SELF-MODEL] {content[:150]}"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ReflectRequest(BaseModel):
    force: bool = False   # bypass cooldown


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    """Called by plugin_loader."""
    global _OLLAMA_BASE, _REFLECT_MODEL, _NODE_ID, _BASE_DIR

    _NODE_ID = config.get("node", {}).get("name", "unknown")
    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))

    # Inference config
    models = config.get("models", {})
    providers = models.get("providers", {})
    if "llama" in providers:
        url = providers["llama"].get("url", _OLLAMA_BASE)
        if "/v1" in url:
            url = url.replace("/v1", "")
        _OLLAMA_BASE = url

    _REFLECT_MODEL = models.get("default", _REFLECT_MODEL)

    router = APIRouter(tags=["self-model"])

    @router.get("/api/v1/self-model")
    async def get_self_model():
        """Current self-assessment (strengths, weaknesses, confidence)."""
        return get_current()

    @router.post("/api/v1/reflect")
    async def trigger_reflect(req: ReflectRequest = ReflectRequest()):
        """Trigger a reflection cycle."""
        global _last_reflect_ts
        if req.force:
            _last_reflect_ts = 0.0

        result = reflect()
        return result

    app.include_router(router)
    log.info("[self-model] Plugin loaded for node=%s", _NODE_ID)

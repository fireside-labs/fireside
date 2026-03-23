"""
brain-installer/handler.py — One-click brain installation API.

Routes:
  GET  /api/v1/brains/available       — Models compatible with this hardware
  GET  /api/v1/brains/installed       — Currently installed brains
  POST /api/v1/brains/install         — One-click install (detect → download → start)
  POST /api/v1/brains/custom          — Register a local GGUF file as a custom model
  DELETE /api/v1/brains/custom/{id}   — Remove a custom model
  GET  /api/v1/brains/categories      — List models by category
  POST /api/v1/brains/restart         — Restart inference server
  POST /api/v1/brains/stop            — Stop inference
  POST /api/v1/brains/cloud/setup     — Save + validate cloud API key
"""
from __future__ import annotations

import json
import logging
import platform
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("valhalla.brain-installer")

_BASE_DIR = Path(".")
_MODELS_CONFIG: dict = {}


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class InstallRequest(BaseModel):
    model_id: str
    port: int = 8080


class CloudSetupRequest(BaseModel):
    api_key: str
    provider: str = ""  # auto-detected from key prefix if empty


class CustomModelRequest(BaseModel):
    name: str
    gguf_path: str
    context: int = 4096
    description: str = ""


# ---------------------------------------------------------------------------
# Helper: detect best runtime for this hardware
# ---------------------------------------------------------------------------

def _detect_runtime() -> str:
    """Pick the best runtime for this machine."""
    try:
        from plugins.brain_installer.installers import omlx
        if omlx.is_available():
            return "omlx"
    except Exception:
        pass

    try:
        from plugins.brain_installer.installers import llamacpp
        if llamacpp.is_available():
            return "llamacpp"
    except Exception:
        pass

    return "cloud"


def _get_vram() -> float:
    """Get available VRAM."""
    try:
        # Reuse consumer-api's detection
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "consumer_handler",
            str(_BASE_DIR / "plugins" / "consumer-api" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod._detect_vram_gb()
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------

_installed_brains: list = []
_active_brain: dict | None = None


def _load_state():
    """Load installed brains from disk."""
    global _installed_brains, _active_brain
    state_file = Path.home() / ".fireside" / "brains_state.json"
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            _installed_brains = data.get("installed", [])
            _active_brain = data.get("active")
        except Exception:
            pass


def _save_state():
    """Save installed brains to disk."""
    state_file = Path.home() / ".fireside" / "brains_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "installed": _installed_brains,
        "active": _active_brain,
    }, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _MODELS_CONFIG

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MODELS_CONFIG = config.get("models", {})
    _load_state()

    router = APIRouter(tags=["brain-installer"])

    @router.get("/api/v1/brains/available")
    async def api_available():
        """Models compatible with this hardware."""
        from plugins.brain_installer.registry import get_available
        vram = _get_vram()
        runtime = _detect_runtime()
        models = get_available(vram)
        return {
            "models": models,
            "count": len(models),
            "detected_runtime": runtime,
            "vram_gb": vram,
        }

    @router.get("/api/v1/brains/status")
    async def api_brain_status():
        """Current brain status — merges live process info with install state.

        Returns both the BrainControlPanel fields (running, model, pid, port)
        AND the installer fields (installed, active, count).
        """
        runtime = _detect_runtime()

        # Get live process info from brain_manager
        live = {}
        try:
            from bot.brain_manager import get_status
            live = get_status()
        except Exception:
            live = {"running": False, "model": None, "pid": None, "port": 8080}

        return {
            # Fields expected by BrainControlPanel
            "running": live.get("running", False),
            "model": live.get("model"),
            "model_path": live.get("model_path"),
            "pid": live.get("pid"),
            "port": live.get("port", 8080),
            "started_at": live.get("started_at"),
            "error": live.get("error"),
            "gpu_layers": live.get("gpu_layers", 0),
            # Installer fields
            "installed": _installed_brains,
            "active": _active_brain,
            "count": len(_installed_brains),
            "runtime": runtime,
            "vram_gb": _get_vram(),
        }

    @router.get("/api/v1/brains/installed")
    async def api_installed():
        """Currently installed brains."""
        return {
            "brains": _installed_brains,
            "active": _active_brain,
            "count": len(_installed_brains),
        }

    @router.post("/api/v1/brains/install")
    async def api_install(req: InstallRequest):
        """One-click install: detect → download → configure → start."""
        global _active_brain

        from plugins.brain_installer.registry import get_model

        model = get_model(req.model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Unknown model: {req.model_id}")

        # Cloud models — just need API key
        if model.get("provider"):
            from plugins.brain_installer.installers.cloud import has_api_key
            if not has_api_key():
                raise HTTPException(
                    status_code=400,
                    detail="Cloud model requires API key. Use POST /api/v1/brains/cloud/setup first."
                )
            brain = {
                "id": model["id"],
                "name": model["name"],
                "runtime": "cloud",
                "model_id": model.get("model_id"),
                "port": None,
            }
            _installed_brains = [b for b in _installed_brains if b["id"] != model["id"]]
            _installed_brains.append(brain)
            _active_brain = brain
            _save_state()
            _publish("brain.installed", brain)
            return {"ok": True, "brain": brain}

        # Local models — pick runtime and install
        runtime = _detect_runtime()

        if runtime == "omlx":
            from plugins.brain_installer.installers.omlx import (
                install_runtime, download_model, start_server,
            )
            omlx_id = model.get("omlx_id", "")
            if not omlx_id:
                raise HTTPException(status_code=400, detail="No oMLX ID for this model")

            r = install_runtime()
            if not r.get("ok"):
                raise HTTPException(status_code=500, detail=r.get("error"))

            r = download_model(omlx_id)
            if not r.get("ok"):
                raise HTTPException(status_code=500, detail=r.get("error"))

            r = start_server(omlx_id, port=req.port)
            if not r.get("ok"):
                raise HTTPException(status_code=500, detail=r.get("error"))

            brain = {
                "id": model["id"],
                "name": model["name"],
                "runtime": "omlx",
                "omlx_id": omlx_id,
                "port": req.port,
                "pid": r.get("pid"),
            }

        elif runtime == "llamacpp":
            from plugins.brain_installer.installers.llamacpp import (
                install_runtime, download_model, start_server,
            )
            gguf_url = model.get("gguf_url", "")
            if not gguf_url:
                raise HTTPException(status_code=400, detail="No GGUF URL for this model")

            r = install_runtime()
            if not r.get("ok"):
                raise HTTPException(status_code=500, detail=r.get("error"))

            r = download_model(model["id"], gguf_url)
            if not r.get("ok"):
                raise HTTPException(status_code=500, detail=r.get("error"))

            r = start_server(r["path"], port=req.port, context=model.get("context", 32768))
            if not r.get("ok"):
                raise HTTPException(status_code=500, detail=r.get("error"))

            brain = {
                "id": model["id"],
                "name": model["name"],
                "runtime": "llamacpp",
                "port": req.port,
                "pid": r.get("pid"),
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="No local runtime available. Use a cloud model or install manually."
            )

        _installed_brains.append(brain)
        _active_brain = brain
        _save_state()

        _publish("brain.installed", brain)
        _publish("brain.started", {"id": model["id"], "port": req.port})

        return {"ok": True, "brain": brain}

    @router.post("/api/v1/brains/restart")
    async def api_restart():
        """Restart the active inference server."""
        from plugins.brain_installer.process_manager import start_service
        result = start_service()
        if result.get("ok"):
            _publish("brain.started", {"active": _active_brain})
        return result

    @router.post("/api/v1/brains/stop")
    async def api_stop():
        """Stop the inference server."""
        from plugins.brain_installer.process_manager import stop_service
        result = stop_service()
        if result.get("ok"):
            _publish("brain.stopped", {})
        return result

    @router.post("/api/v1/brains/cloud/setup")
    async def api_cloud_setup(req: CloudSetupRequest):
        """Save and validate cloud API key."""
        from plugins.brain_installer.installers.cloud import (
            validate_api_key, save_api_key, detect_provider,
        )

        # Auto-detect provider from key prefix if not specified
        provider = req.provider or detect_provider(req.api_key)

        validation = validate_api_key(req.api_key, provider=provider)
        if not validation.get("ok"):
            raise HTTPException(status_code=400, detail=validation.get("error"))

        save_result = save_api_key(req.api_key, provider=provider)
        return {
            "ok": True,
            "provider": provider,
            "validation": validation.get("message"),
            "stored": save_result.get("ok"),
        }

    @router.post("/api/v1/brains/custom")
    async def api_add_custom(req: CustomModelRequest):
        """Register a local GGUF file as a custom model."""
        from plugins.brain_installer.registry import add_custom_model
        result = add_custom_model(
            name=req.name,
            gguf_path=req.gguf_path,
            context=req.context,
            description=req.description,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    @router.delete("/api/v1/brains/custom/{model_id}")
    async def api_remove_custom(model_id: str):
        """Remove a custom model."""
        from plugins.brain_installer.registry import remove_custom_model
        result = remove_custom_model(model_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result

    @router.get("/api/v1/brains/categories")
    async def api_categories(category: str = "", family: str = ""):
        """Browse models by category or family."""
        from plugins.brain_installer.registry import get_by_category, get_by_family, get_all_models
        if category:
            models = get_by_category(category)
        elif family:
            models = get_by_family(family)
        else:
            models = get_all_models()
        return {
            "models": models,
            "count": len(models),
            "categories": ["general", "coding", "reasoning", "custom"],
            "families": ["Llama", "Qwen", "DeepSeek", "Gemma", "Mistral", "Phi", "Moonshot", "Zhipu"],
        }

    @router.post("/api/v1/brains/onboard")
    async def api_onboard(req: InstallRequest):
        """Full installer onboarding sequence (idempotent).

        Steps:
          1. Detect GPU / VRAM
          2. Install runtime binary (llama.cpp or oMLX)
          3. Download selected model (GGUF from HuggingFace)
          4. Install LanceDB (pip install lancedb)
          5. Install voice dependencies (kokoro, faster-whisper)
          6. Start inference server
          7. Health check on inference port

        Each step is idempotent — skips if already done.
        Returns step-by-step results with status for each step.
        """
        import subprocess
        import sys
        import urllib.request

        from plugins.brain_installer.registry import get_model

        model = get_model(req.model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Unknown model: {req.model_id}")

        steps = []

        # --- Step 1: Detect GPU ---
        vram = _get_vram()
        runtime = _detect_runtime()
        steps.append({
            "step": 1,
            "name": "detect_gpu",
            "status": "done",
            "vram_gb": vram,
            "runtime": runtime,
        })

        # --- Step 2: Install runtime ---
        step2 = {"step": 2, "name": "install_runtime", "status": "skipped"}
        if model.get("provider"):
            step2["status"] = "skipped"
            step2["detail"] = "Cloud model — no local runtime needed"
        elif runtime in ("llamacpp", "omlx"):
            try:
                if runtime == "llamacpp":
                    from plugins.brain_installer.installers.llamacpp import (
                        install_runtime, is_installed,
                    )
                else:
                    from plugins.brain_installer.installers.omlx import (
                        install_runtime, is_installed,
                    )
                if is_installed():
                    step2["status"] = "already_installed"
                else:
                    r = install_runtime()
                    step2["status"] = "done" if r.get("ok") else "error"
                    if not r.get("ok"):
                        step2["error"] = r.get("error")
            except Exception as e:
                step2["status"] = "error"
                step2["error"] = str(e)
        else:
            step2["status"] = "error"
            step2["error"] = "No compatible runtime found. Use a cloud model."
        steps.append(step2)

        # --- Step 3: Download model ---
        step3 = {"step": 3, "name": "download_model", "status": "skipped"}
        if model.get("provider"):
            step3["detail"] = "Cloud model — no download needed"
        elif model.get("gguf_url"):
            try:
                from plugins.brain_installer.installers.llamacpp import download_model
                r = download_model(model["id"], model["gguf_url"])
                step3["status"] = "done" if r.get("ok") else "error"
                step3["path"] = r.get("path", "")
                if r.get("message") == "Already downloaded":
                    step3["status"] = "already_installed"
                if not r.get("ok"):
                    step3["error"] = r.get("error")
            except Exception as e:
                step3["status"] = "error"
                step3["error"] = str(e)
        steps.append(step3)

        # --- Step 4: Install LanceDB ---
        step4 = {"step": 4, "name": "install_lancedb", "status": "skipped"}
        try:
            import lancedb  # noqa: F401
            step4["status"] = "already_installed"
        except ImportError:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "lancedb", "-q"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=300,
                )
                step4["status"] = "done"
            except Exception as e:
                step4["status"] = "error"
                step4["error"] = str(e)
        steps.append(step4)

        # --- Step 5: Install voice deps ---
        step5 = {"step": 5, "name": "install_voice_deps", "status": "skipped"}
        voice_pkgs = []
        try:
            import kokoro  # noqa: F401
        except ImportError:
            voice_pkgs.extend(["kokoro", "soundfile"])
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            voice_pkgs.append("faster-whisper")

        if not voice_pkgs:
            step5["status"] = "already_installed"
        else:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install"] + voice_pkgs + ["-q"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=300,
                )
                step5["status"] = "done"
                step5["installed"] = voice_pkgs
            except Exception as e:
                step5["status"] = "error"
                step5["error"] = str(e)
        steps.append(step5)

        # --- Step 6: Start server ---
        step6 = {"step": 6, "name": "start_server", "status": "skipped"}
        if model.get("provider"):
            step6["detail"] = "Cloud model — no local server"
        elif step3.get("path"):
            try:
                from plugins.brain_installer.installers.llamacpp import start_server
                r = start_server(
                    step3["path"],
                    port=req.port,
                    context=model.get("context", 32768),
                )
                step6["status"] = "done" if r.get("ok") else "error"
                step6["port"] = req.port
                step6["pid"] = r.get("pid")
                if not r.get("ok"):
                    step6["error"] = r.get("error")
            except Exception as e:
                step6["status"] = "error"
                step6["error"] = str(e)
        steps.append(step6)

        # --- Step 7: Health check ---
        step7 = {"step": 7, "name": "health_check", "status": "skipped"}
        if model.get("provider"):
            step7["status"] = "done"
            step7["detail"] = "Cloud model — always healthy"
        elif step6.get("status") == "done":
            import time as _time
            healthy = False
            for attempt in range(10):
                try:
                    url = f"http://127.0.0.1:{req.port}/health"
                    with urllib.request.urlopen(url, timeout=3) as resp:
                        if resp.status == 200:
                            healthy = True
                            break
                except Exception:
                    _time.sleep(1)
            step7["status"] = "done" if healthy else "error"
            step7["attempts"] = attempt + 1
            if not healthy:
                step7["error"] = f"Server not responding on port {req.port} after 10 attempts"
        steps.append(step7)

        # --- Summary ---
        all_ok = all(
            s["status"] in ("done", "already_installed", "skipped")
            for s in steps
        )

        _publish("brain.onboarded", {
            "model_id": req.model_id,
            "success": all_ok,
            "steps": len(steps),
        })

        return {
            "ok": all_ok,
            "model_id": req.model_id,
            "runtime": runtime,
            "steps": steps,
        }

    app.include_router(router)
    log.info("[brain-installer] Plugin loaded. Runtime: %s, Installed: %d",
             _detect_runtime(), len(_installed_brains))



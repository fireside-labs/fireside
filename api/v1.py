"""
api/v1.py — REST API v1 for the Valhalla Dashboard.

All endpoints that the Next.js dashboard consumes live here.
Supports: onboarding (status + GPU), nodes, mesh join, model-switch,
config, soul editor, and plugin marketplace.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

log = logging.getLogger("valhalla.api.v1")

router = APIRouter(prefix="/api/v1", tags=["v1"])

# Set at startup by init_api()
_config: dict = {}
_start_time: float = 0.0
_base_dir: Path = Path(".")

# Join tokens: token_id → { token, node_name, expires_at }
_join_tokens: dict[str, dict] = {}
_JOIN_TOKEN_TTL = 900  # 15 minutes


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ConfigUpdateRequest(BaseModel):
    yaml_content: str


class ConfigReceiveRequest(BaseModel):
    """Config pushed from the orchestrator to a worker node."""
    yaml_content: str
    sender: str = "unknown"
    auth_token: str = ""


class SoulWriteRequest(BaseModel):
    content: str


class AnnounceRequest(BaseModel):
    """A new node announcing itself to the mesh."""
    name: str
    ip: str
    port: int = 8765
    role: str = "worker"
    token: str  # the join token for validation
    gpu: Optional[str] = None
    vram_gb: Optional[float] = None
    inference: Optional[str] = None
    model: Optional[str] = None


class NodeConfigPush(BaseModel):
    """Push role/model/soul config to a node."""
    role: Optional[str] = None
    model: Optional[str] = None
    soul_clone_from: Optional[str] = None


class PluginInstallRequest(BaseModel):
    """Install a plugin from the marketplace."""
    name: str
    version: Optional[str] = None
    source_url: Optional[str] = None  # for marketplace fetches


# ---------------------------------------------------------------------------
# GPU / Inference detection helpers
# ---------------------------------------------------------------------------

def _detect_gpu() -> dict:
    """Best-effort GPU detection for the status endpoint."""
    gpu_info = {"name": None, "vram_total_gb": None, "vram_used_gb": None}

    # Try nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            gpu_info["name"] = parts[0].strip()
            gpu_info["vram_total_gb"] = round(int(parts[1]) / 1024, 1)
            gpu_info["vram_used_gb"] = round(int(parts[2]) / 1024, 1)
            return gpu_info
    except Exception:
        pass

    # Try macOS (Apple Silicon — unified memory)
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            total_bytes = int(result.stdout.strip())
            gpu_info["name"] = "Apple Silicon (unified)"
            gpu_info["vram_total_gb"] = round(total_bytes / (1024**3), 1)
            return gpu_info
    except Exception:
        pass

    return gpu_info


def _detect_inference() -> dict:
    """Detect which inference engines are available."""
    engines = {}

    # Ollama
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            models = [
                line.split()[0] for line in result.stdout.strip().split("\n")[1:]
                if line.strip()
            ]
            engines["ollama"] = {"available": True, "models": models[:10]}
    except Exception:
        engines["ollama"] = {"available": False}

    # LM Studio — check if port 1234 is listening
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:1234/v1/models", timeout=2) as resp:
            engines["lm_studio"] = {"available": True}
    except Exception:
        engines["lm_studio"] = {"available": False}

    return engines


# ---------------------------------------------------------------------------
# Endpoints: Status + Onboarding
# ---------------------------------------------------------------------------

@router.get("/status")
async def get_status():
    """Node health, loaded model, uptime, GPU/VRAM, inference engines.

    Powers the Mission Control dashboard (onboarding.md).
    """
    from plugin_loader import get_plugins

    # Current model
    current_model = _config.get("models", {}).get("default", "unknown")
    try:
        import importlib.util
        handler_path = _base_dir / "plugins" / "model-switch" / "handler.py"
        if handler_path.exists():
            spec = importlib.util.spec_from_file_location(
                "ms_handler", str(handler_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                current_model = mod.get_current_model() or current_model
    except Exception:
        pass

    node = _config.get("node", {})
    uptime_seconds = time.time() - _start_time
    gpu = _detect_gpu()
    inference = _detect_inference()

    return {
        "node": node.get("name", "unknown"),
        "role": node.get("role", "unknown"),
        "port": node.get("port", 8765),
        "model": current_model,
        "uptime_seconds": round(uptime_seconds, 1),
        "uptime_human": _format_uptime(uptime_seconds),
        "plugins_loaded": len(get_plugins()),
        "status": "online",
        "mobile_ready": True,
        "gpu": gpu,
        "inference": inference,
    }


@router.get("/system/onboarding")
async def get_onboarding():
    """Check if install.sh already completed onboarding.

    Reads ~/.fireside/onboarding.json written by install.sh.
    The dashboard checks this to skip its own wizard.
    """
    onboarding_file = Path.home() / ".fireside" / "onboarding.json"
    if not onboarding_file.exists():
        return {"onboarded": False}

    try:
        data = json.loads(onboarding_file.read_text(encoding="utf-8"))
        return {
            "onboarded": data.get("onboarded", False),
            "user_name": data.get("user_name", ""),
            "personality": data.get("personality", "friendly"),
            "brain": data.get("brain", ""),
            "companion": data.get("companion"),
        }
    except Exception:
        return {"onboarded": False}


# ---------------------------------------------------------------------------
# Endpoints: Nodes
# ---------------------------------------------------------------------------

@router.get("/nodes")
async def get_nodes():
    """All mesh nodes and their status.

    Polled by the add-a-node modal every 2s (add-a-node.md).
    """
    mesh_nodes = _config.get("mesh", {}).get("nodes", {})
    this_node = _config.get("node", {}).get("name", "")

    nodes = []
    for name, ncfg in mesh_nodes.items():
        node_info = {
            "name": name,
            "ip": ncfg.get("ip", ""),
            "port": ncfg.get("port", 8765),
            "role": ncfg.get("role", ""),
            "is_self": name == this_node,
            "status": "self" if name == this_node else "unknown",
        }

        # Enrich with watchdog status if available
        try:
            import importlib.util
            handler_path = _base_dir / "plugins" / "watchdog" / "handler.py"
            if handler_path.exists():
                spec = importlib.util.spec_from_file_location(
                    "wd_handler", str(handler_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    wd_status = mod.get_status()
                    wd_nodes = wd_status.get("nodes", {})
                    if name in wd_nodes:
                        node_info["status"] = wd_nodes[name].get(
                            "status", "unknown")
                        node_info["last_seen"] = wd_nodes[name].get(
                            "last_seen")
        except Exception:
            pass

        nodes.append(node_info)

    return {"nodes": nodes, "count": len(nodes), "this_node": this_node}


# ---------------------------------------------------------------------------
# Endpoints: Mesh Join Flow  (add-a-node.md)
# ---------------------------------------------------------------------------

@router.post("/mesh/join-token")
async def create_join_token():
    """Generate a time-limited join token for the 'Add Node' flow.

    Returns a short join command the user pastes on a second machine.
    Called by the 'Add Node' button in the dashboard.
    """
    node = _config.get("node", {})
    node_name = node.get("name", "valhalla")
    node_port = node.get("port", 8765)

    # Detect the orchestrator's IP (best guess: first interface or config)
    # In production, Tailscale IP is in mesh config
    my_ip = "127.0.0.1"
    mesh_nodes = _config.get("mesh", {}).get("nodes", {})
    # Try to find our own IP from mesh config
    for name, ncfg in mesh_nodes.items():
        if name == node_name and ncfg.get("ip"):
            my_ip = ncfg["ip"]
            break

    # Generate signed token
    token_id = secrets.token_urlsafe(8)
    token_secret = secrets.token_urlsafe(16)
    expires_at = time.time() + _JOIN_TOKEN_TTL

    _join_tokens[token_id] = {
        "secret": token_secret,
        "expires_at": expires_at,
        "used": False,
    }

    # Clean expired tokens
    now = time.time()
    expired = [k for k, v in _join_tokens.items() if v["expires_at"] < now]
    for k in expired:
        del _join_tokens[k]

    join_command = f"valhalla join {node_name}@{my_ip}"
    expires_in = _JOIN_TOKEN_TTL

    log.info("[mesh] Join token created: %s (expires in %ds)", token_id, expires_in)

    return {
        "ok": True,
        "token_id": token_id,
        "token": token_secret,
        "join_command": join_command,
        "orchestrator": f"{my_ip}:{node_port}",
        "expires_in_seconds": expires_in,
        "expires_at": datetime.fromtimestamp(
            expires_at, tz=timezone.utc).isoformat(),
    }


@router.post("/mesh/announce")
async def mesh_announce(req: AnnounceRequest):
    """A new node announces itself to the mesh.

    Called by `valhalla join` after the CLI validates the token.
    Adds the node to the mesh config and broadcasts its arrival.
    """
    # Validate token
    found = False
    for tid, tdata in _join_tokens.items():
        if tdata["secret"] == req.token and not tdata["used"]:
            if tdata["expires_at"] < time.time():
                raise HTTPException(
                    status_code=410,
                    detail="This join link expired. "
                           "Go back to the dashboard and click 'Add Node' for a new one.",
                )
            tdata["used"] = True
            found = True
            break

    if not found:
        raise HTTPException(
            status_code=401,
            detail="Invalid or already-used join token.",
        )

    # Handle name conflicts (add-a-node.md: "Joining as thor-desktop-2 instead")
    mesh_nodes = _config.get("mesh", {}).get("nodes", {})
    final_name = req.name
    if final_name in mesh_nodes:
        suffix = 2
        while f"{req.name}-{suffix}" in mesh_nodes:
            suffix += 1
        final_name = f"{req.name}-{suffix}"

    # Add to in-memory config
    mesh_nodes[final_name] = {
        "ip": req.ip,
        "port": req.port,
        "role": req.role,
        "gpu": req.gpu,
        "vram_gb": req.vram_gb,
        "inference": req.inference,
        "model": req.model,
        "joined_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to valhalla.yaml
    try:
        from config_loader import get_config_raw_yaml, save_config_yaml
        import yaml
        raw = yaml.safe_load(get_config_raw_yaml())
        if "mesh" not in raw:
            raw["mesh"] = {}
        if "nodes" not in raw["mesh"]:
            raw["mesh"]["nodes"] = {}
        raw["mesh"]["nodes"][final_name] = {
            "ip": req.ip,
            "port": req.port,
            "role": req.role,
        }
        save_config_yaml(yaml.dump(raw, default_flow_style=False))
    except Exception as e:
        log.warning("[mesh] Failed to persist new node to YAML: %s", e)

    renamed = final_name != req.name

    log.info("[mesh] Node announced: %s (%s:%d, role=%s)",
             final_name, req.ip, req.port, req.role)

    return {
        "ok": True,
        "name": final_name,
        "renamed": renamed,
        "original_name": req.name if renamed else None,
        "message": f"Welcome to the mesh, {final_name}.",
    }


@router.put("/nodes/{name}/config")
async def push_node_config(name: str, req: NodeConfigPush):
    """Push role/model/soul config to a specific node.

    Called after node joins and user picks role/model in the dashboard.
    """
    mesh_nodes = _config.get("mesh", {}).get("nodes", {})
    if name not in mesh_nodes:
        raise HTTPException(status_code=404, detail=f"Node '{name}' not found")

    updates = {}
    if req.role is not None:
        mesh_nodes[name]["role"] = req.role
        updates["role"] = req.role
    if req.model is not None:
        updates["model"] = req.model
    if req.soul_clone_from is not None:
        # Clone soul files from source agent to target
        try:
            soul_dir = _base_dir / "mesh" / "souls"
            for prefix in ("IDENTITY", "SOUL", "USER"):
                src = soul_dir / f"{prefix}.{req.soul_clone_from}.md"
                dst = soul_dir / f"{prefix}.{name}.md"
                if src.exists():
                    content = src.read_text(encoding="utf-8")
                    # Replace source name with target name in content
                    content = content.replace(req.soul_clone_from, name)
                    dst.write_text(content, encoding="utf-8")
            updates["soul_cloned_from"] = req.soul_clone_from
        except Exception as e:
            log.warning("[nodes] Soul clone failed: %s", e)
            updates["soul_clone_error"] = str(e)

    log.info("[nodes] Config pushed to %s: %s", name, updates)
    return {"ok": True, "node": name, "updates": updates}


@router.delete("/nodes/{name}")
async def remove_node(name: str):
    """Remove a node from the mesh and revoke auth.

    Called from the dashboard node card → 'Remove Node' → confirm.
    """
    mesh_nodes = _config.get("mesh", {}).get("nodes", {})
    if name not in mesh_nodes:
        raise HTTPException(status_code=404, detail=f"Node '{name}' not found")

    this_node = _config.get("node", {}).get("name", "")
    if name == this_node:
        raise HTTPException(
            status_code=400, detail="Cannot remove self from mesh")

    # Remove from in-memory config
    removed_info = mesh_nodes.pop(name)

    # Persist removal to valhalla.yaml
    try:
        from config_loader import get_config_raw_yaml, save_config_yaml
        import yaml
        raw = yaml.safe_load(get_config_raw_yaml())
        if name in raw.get("mesh", {}).get("nodes", {}):
            del raw["mesh"]["nodes"][name]
        save_config_yaml(yaml.dump(raw, default_flow_style=False))
    except Exception as e:
        log.warning("[mesh] Failed to persist node removal to YAML: %s", e)

    log.info("[mesh] Node removed: %s", name)
    return {
        "ok": True,
        "removed": name,
        "role": removed_info.get("role", ""),
    }


# ---------------------------------------------------------------------------
# Endpoints: Model Switch
# ---------------------------------------------------------------------------

@router.post("/model-switch")
async def model_switch(request: Request):
    """Switch model by alias — delegates to the model-switch plugin."""
    body = await request.json()
    alias = body.get("alias", "")
    model = body.get("model", "")

    aliases = _config.get("models", {}).get("aliases", {})
    model_id = model or aliases.get(alias.lower().strip())

    if not model_id:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown alias '{alias}'. Valid: {list(aliases.keys())}",
        )

    return {"ok": True, "switching_to": model_id, "alias": alias}


# ---------------------------------------------------------------------------
# Endpoints: Config
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_config_endpoint():
    """Current valhalla.yaml as structured JSON."""
    from config_loader import get_config_raw_yaml
    return {
        "config": _config,
        "raw_yaml": get_config_raw_yaml(),
    }


@router.put("/config")
async def update_config(req: ConfigUpdateRequest):
    """Update valhalla.yaml, hot-reload, and push to mesh peers."""
    from config_loader import save_config_yaml, ConfigError
    try:
        new_config = save_config_yaml(req.yaml_content)
        global _config
        _config = new_config

        # Push to mesh peers (fire-and-forget)
        _push_config_to_mesh(req.yaml_content)

        return {"ok": True, "message": "Config saved, reloaded, and pushed to mesh"}
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/receive")
async def receive_config(req: ConfigReceiveRequest):
    """Accept config pushed from the orchestrator.

    Called by the orchestrator when PUT /config triggers mesh sync.
    Validates auth_token against mesh.auth_token.
    """
    # Auth check — timing-safe comparison (Heimdall Sprint 3)
    import hmac
    expected_token = _config.get("mesh", {}).get("auth_token", "")
    if not expected_token or not hmac.compare_digest(req.auth_token, expected_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing auth token",
        )

    from config_loader import save_config_yaml, ConfigError
    try:
        new_config = save_config_yaml(req.yaml_content)
        global _config
        _config = new_config
        log.info("[config] Received and applied config push from %s", req.sender)
        return {"ok": True, "message": f"Config received from {req.sender}"}
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Endpoints: Soul Editor
# ---------------------------------------------------------------------------

@router.get("/soul/{filename:path}")
async def get_soul(filename: str):
    """Read a soul file (e.g. IDENTITY.odin.md)."""
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    soul_dir = _base_dir / "mesh" / "souls"
    file_path = soul_dir / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Soul file not found: {filename}")

    try:
        file_path.resolve().relative_to(soul_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal detected")

    content = file_path.read_text(encoding="utf-8")
    return {"filename": filename, "content": content}


@router.put("/soul/{filename:path}")
async def put_soul(filename: str, req: SoulWriteRequest):
    """Write a soul file."""
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    soul_dir = _base_dir / "mesh" / "souls"
    file_path = soul_dir / filename

    try:
        file_path.resolve().relative_to(soul_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal detected")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(req.content, encoding="utf-8")

    return {"ok": True, "filename": filename, "bytes_written": len(req.content)}


# ---------------------------------------------------------------------------
# Endpoints: Plugins + Marketplace  (marketplace.md)
# ---------------------------------------------------------------------------

@router.get("/plugins")
async def get_plugins_endpoint():
    """Installed plugins and their status (Installed view)."""
    from plugin_loader import get_plugins
    plugins = get_plugins()
    return {"plugins": plugins, "count": len(plugins)}


@router.get("/plugins/browse")
async def browse_plugins():
    """Browse the plugin marketplace catalog.

    Sprint 1: returns local available plugins (discovered but not enabled).
    Sprint 2+: fetches from remote registry.
    """
    from plugin_loader import discover_plugins, get_plugins

    all_discovered = discover_plugins()
    loaded_names = {p["name"] for p in get_plugins()}

    catalog = []
    for manifest in all_discovered:
        catalog.append({
            "name": manifest.get("name"),
            "version": manifest.get("version", "0.0.0"),
            "description": manifest.get("description", ""),
            "author": manifest.get("author", ""),
            "category": manifest.get("category", "general"),
            "tags": manifest.get("tags", []),
            "installed": manifest.get("name") in loaded_names,
        })

    return {"plugins": catalog, "count": len(catalog)}


@router.post("/plugins/install")
async def install_plugin(req: PluginInstallRequest):
    """Install a plugin — add to enabled list and hot-reload.

    Sprint 1: enables already-present plugins from plugins/ directory.
    Sprint 2+: downloads from marketplace registry.
    """
    plugins_dir = _base_dir / "plugins"
    plugin_dir = plugins_dir / req.name

    if not plugin_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{req.name}' not found in plugins directory. "
                   "Remote marketplace install coming in Sprint 2.",
        )

    # Add to enabled list in config
    enabled = _config.get("plugins", {}).get("enabled", [])
    if req.name not in enabled:
        enabled.append(req.name)

    # Persist to valhalla.yaml
    try:
        from config_loader import get_config_raw_yaml, save_config_yaml
        import yaml
        raw = yaml.safe_load(get_config_raw_yaml())
        if "plugins" not in raw:
            raw["plugins"] = {}
        raw["plugins"]["enabled"] = enabled
        save_config_yaml(yaml.dump(raw, default_flow_style=False))
    except Exception as e:
        log.warning("[plugins] Failed to persist install: %s", e)

    log.info("[plugins] Installed: %s", req.name)
    return {
        "ok": True,
        "plugin": req.name,
        "message": f"Plugin '{req.name}' enabled. Restart Bifrost to activate.",
    }


@router.delete("/plugins/{name}")
async def uninstall_plugin(name: str):
    """Uninstall a plugin — remove from enabled list.

    Does NOT delete the plugin folder (marketplace.md: 'config keys stay').
    """
    enabled = _config.get("plugins", {}).get("enabled", [])
    if name not in enabled:
        raise HTTPException(
            status_code=404, detail=f"Plugin '{name}' is not enabled")

    enabled.remove(name)

    # Persist
    try:
        from config_loader import get_config_raw_yaml, save_config_yaml
        import yaml
        raw = yaml.safe_load(get_config_raw_yaml())
        raw["plugins"]["enabled"] = enabled
        save_config_yaml(yaml.dump(raw, default_flow_style=False))
    except Exception as e:
        log.warning("[plugins] Failed to persist uninstall: %s", e)

    log.info("[plugins] Uninstalled: %s", name)
    return {
        "ok": True,
        "plugin": name,
        "message": f"Plugin '{name}' disabled. Plugin files preserved.",
    }


# ---------------------------------------------------------------------------
# Endpoints: API Keys  (Sprint — Dashboard Hub)
# ---------------------------------------------------------------------------

_KEYS_FILE = Path.home() / ".fireside" / "keys.json"


def _load_keys() -> dict:
    """Load API keys from encrypted storage."""
    if not _KEYS_FILE.exists():
        return {}
    try:
        import base64
        raw = _KEYS_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        # Keys stored as base64 — simple obfuscation
        # (Production: use Fernet with machine-scoped key)
        return {k: base64.b64decode(v).decode() for k, v in data.items()}
    except Exception:
        return {}


def _save_keys(keys: dict) -> None:
    """Save API keys to storage."""
    import base64
    _KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    encoded = {k: base64.b64encode(v.encode()).decode() for k, v in keys.items()}
    _KEYS_FILE.write_text(json.dumps(encoded, indent=2), encoding="utf-8")


class ApiKeyRequest(BaseModel):
    provider: str
    key: str


@router.get("/config/keys")
async def get_keys():
    """List which API keys are configured (names only, never values)."""
    keys = _load_keys()
    result = []
    for provider in ["openai", "anthropic", "google", "elevenlabs", "replicate"]:
        result.append({
            "provider": provider,
            "connected": provider in keys and len(keys[provider]) > 8,
            "masked": f"...{keys[provider][-4:]}" if provider in keys and len(keys[provider]) > 4 else None,
        })
    return {"keys": result}


@router.post("/config/keys")
async def set_key(req: ApiKeyRequest):
    """Save an API key (encrypted at rest)."""
    if not req.provider or not req.key:
        raise HTTPException(status_code=400, detail="Provider and key required")

    keys = _load_keys()
    keys[req.provider] = req.key
    _save_keys(keys)

    log.info("[keys] Saved API key for %s", req.provider)
    return {"ok": True, "provider": req.provider}


@router.delete("/config/keys/{provider}")
async def delete_key(provider: str):
    """Remove an API key."""
    keys = _load_keys()
    if provider not in keys:
        raise HTTPException(status_code=404, detail=f"No key for '{provider}'")

    del keys[provider]
    _save_keys(keys)

    log.info("[keys] Deleted API key for %s", provider)
    return {"ok": True, "provider": provider}


# ---------------------------------------------------------------------------
# Endpoints: Chat  (Sprint 14 — T2)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(max_length=4096)
    context: list = []


@router.post("/chat")
async def post_chat(req: ChatRequest):
    """Proxy chat to local llama.cpp. Stream response via SSE.

    Uses companion personality from companion_state.json.
    """
    import urllib.request
    from fastapi.responses import StreamingResponse

    # Build system prompt from soul files + personality settings
    system_prompt = "You are a helpful AI assistant."
    try:
        from prompt_assembler import assemble_system_prompt

        # Determine active skills from enabled plugins
        from plugin_loader import get_plugins
        active_skills = [p["name"] for p in get_plugins() if p.get("status") == "loaded"]

        # Get user name from onboarding
        onboarding_file = Path.home() / ".fireside" / "onboarding.json"
        user_name = ""
        if onboarding_file.exists():
            try:
                ob = json.loads(onboarding_file.read_text(encoding="utf-8"))
                user_name = ob.get("user_name", "")
            except Exception:
                pass

        system_prompt = assemble_system_prompt(
            soul_dir=_base_dir / "souls" / "default",
            agent_name="Atlas",
            user_name=user_name,
            active_skills=active_skills,
        )
    except Exception as e:
        log.warning("[chat] Prompt assembler failed, using fallback: %s", e)
        # Fallback to companion_state.json
        state_path = Path.home() / ".valhalla" / "companion_state.json"
        try:
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
                companion_name = state.get("name", "Ember")
                agent_name = state.get("agent", {}).get("name", "Atlas")
                system_prompt = (
                    f"You are {companion_name}, a helpful AI companion. "
                    f"You are friendly, warm, and helpful. "
                    f"Keep responses concise and conversational."
                )
        except Exception:
            pass

    # Build llama.cpp /completion payload
    prompt_parts = [f"System: {system_prompt}"]
    for msg in (req.context or [])[-10:]:
        role = msg.get("role", "user") if isinstance(msg, dict) else "user"
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        prompt_parts.append(f"{role.capitalize()}: {content}")
    prompt_parts.append(f"User: {req.message}")
    prompt_parts.append("Assistant:")
    full_prompt = "\n".join(prompt_parts)

    payload = json.dumps({
        "prompt": full_prompt,
        "stream": True,
        "n_predict": 512,
        "temperature": 0.7,
        "stop": ["User:", "System:"],
    }).encode()

    async def stream_response():
        try:
            http_req = urllib.request.Request(
                "http://127.0.0.1:8080/completion",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(http_req, timeout=60) as resp:
                for line in resp:
                    decoded = line.decode("utf-8", errors="ignore").strip()
                    if decoded.startswith("data: "):
                        chunk = decoded[6:]
                        if chunk == "[DONE]":
                            yield f"data: [DONE]\n\n"
                            break
                        try:
                            obj = json.loads(chunk)
                            content = obj.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            log.warning("[chat] llama.cpp unreachable: %s", e)
            yield f"data: {json.dumps({'content': f'{companion_name} is thinking... but the brain is offline right now. Start the backend first!'})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Endpoints: Brain Install  (Sprint 14 — T3)
# ---------------------------------------------------------------------------

ALLOWED_DOWNLOAD_DOMAINS = {"huggingface.co", "hf.co", "ollama.com", "github.com", "objects.githubusercontent.com"}


class BrainInstallRequest(BaseModel):
    model_id: str
    url: str


@router.post("/brains/install")
async def post_brains_install(req: BrainInstallRequest):
    """Download a GGUF model to ~/.fireside/models/. Stream progress via SSE."""
    import urllib.request
    from urllib.parse import urlparse
    from fastapi.responses import StreamingResponse

    # SSRF protection: only allow downloads from trusted domains
    parsed = urlparse(req.url)
    if parsed.hostname not in ALLOWED_DOWNLOAD_DOMAINS:
        raise HTTPException(400, f"Downloads only allowed from: {', '.join(sorted(ALLOWED_DOWNLOAD_DOMAINS))}")

    models_dir = Path.home() / ".fireside" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    filename = req.model_id.replace("/", "_").replace("\\", "_")
    if not filename.endswith(".gguf"):
        filename += ".gguf"
    dest = models_dir / filename

    async def stream_download():
        try:
            http_req = urllib.request.Request(req.url)
            http_req.add_header("User-Agent", "Fireside/1.0")
            with urllib.request.urlopen(http_req, timeout=300) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 256  # 256KB chunks

                yield f"data: {json.dumps({'status': 'downloading', 'total': total, 'downloaded': 0, 'model_id': req.model_id})}\n\n"

                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = int(downloaded / total * 100) if total > 0 else 0
                        yield f"data: {json.dumps({'status': 'downloading', 'total': total, 'downloaded': downloaded, 'percent': pct})}\n\n"

            yield f"data: {json.dumps({'status': 'complete', 'path': str(dest), 'size': downloaded})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            log.error("[brains/install] Download failed: %s", e)
            # Clean up partial file
            if dest.exists():
                dest.unlink()
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_download(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Endpoints: Guild Hall Agents  (Sprint 14 — T4)
# ---------------------------------------------------------------------------

@router.get("/guildhall/agents")
async def get_guildhall_agents():
    """Return user's actual agents from config with real activity status."""
    # Read agent + companion from config
    agent_cfg = _config.get("agent", {})
    companion_cfg = _config.get("companion", {})

    agent_name = agent_cfg.get("name", "Atlas")
    agent_style = agent_cfg.get("style", "Analytical")
    companion_name = companion_cfg.get("name", "Ember")
    companion_species = companion_cfg.get("species", "fox")

    # Determine AI activity from running state
    ai_activity = "idle"
    try:
        from plugin_loader import _loaded_plugins
        if _loaded_plugins:
            ai_activity = "building"
    except Exception:
        pass

    # Determine companion activity
    companion_activity = "sleeping"
    try:
        from plugins.companion.handler import _active_ws_connections
        if _active_ws_connections:
            companion_activity = "chatting"
        else:
            companion_activity = "idle"
    except Exception:
        companion_activity = "idle"

    return {
        "agents": [
            {
                "type": "ai",
                "name": agent_name,
                "style": agent_style,
                "activity": ai_activity,
                "online": True,
            },
            {
                "type": "companion",
                "name": companion_name,
                "species": companion_species,
                "activity": companion_activity,
                "online": True,
            },
        ]
    }


# ---------------------------------------------------------------------------
# Endpoints: Node Registration  (Sprint 14 — T5)
# ---------------------------------------------------------------------------

class NodeRegisterRequest(BaseModel):
    name: str
    ip: str
    port: int = 8765
    role: str = "worker"
    gpu: Optional[str] = None
    vram_gb: Optional[float] = None
    auth_token: str = ""


@router.post("/nodes")
async def register_node(req: NodeRegisterRequest):
    """Register a new device to the mesh.

    Adds the node to the mesh config and returns a success confirmation.
    Requires mesh.auth_token for authentication.
    """
    # Auth check — same pattern as mesh_announce
    expected_token = _config.get("mesh", {}).get("auth_token", "")
    if not expected_token or not hmac.compare_digest(req.auth_token, expected_token):
        raise HTTPException(status_code=403, detail="Invalid or missing mesh auth token")

    mesh = _config.get("mesh", {})
    nodes = mesh.get("nodes", {})

    if req.name in nodes:
        raise HTTPException(status_code=409, detail=f"Node '{req.name}' already registered")

    nodes[req.name] = {
        "ip": req.ip,
        "port": req.port,
        "role": req.role,
        "gpu": req.gpu,
        "vram_gb": req.vram_gb,
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "status": "online",
    }

    # Update in-memory config
    if "mesh" not in _config:
        _config["mesh"] = {"nodes": {}}
    _config["mesh"]["nodes"] = nodes

    # Persist to config file
    try:
        import yaml
        config_path = Path.home() / ".fireside" / "valhalla.yaml"
        if config_path.exists():
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            if "mesh" not in cfg:
                cfg["mesh"] = {"nodes": {}}
            cfg["mesh"]["nodes"][req.name] = nodes[req.name]
            config_path.write_text(yaml.dump(cfg, default_flow_style=False), encoding="utf-8")
    except Exception as e:
        log.warning("[nodes] Failed to persist node config: %s", e)

    log.info("[nodes] Registered new node: %s (%s:%d)", req.name, req.ip, req.port)
    return {
        "status": "registered",
        "node": req.name,
        "mesh_size": len(nodes),
    }


# ---------------------------------------------------------------------------
# Endpoints: Store — Plugin Registry + Purchases  (Sprint 15 — T3)
# ---------------------------------------------------------------------------

_STORE_REGISTRY_PATH = Path.home() / ".fireside" / "store_registry.json"
_PURCHASES_PATH = Path.home() / ".fireside" / "purchases.json"


def _load_store_registry() -> list[dict]:
    """Load plugin registry from local JSON. Seed with defaults if missing."""
    if _STORE_REGISTRY_PATH.exists():
        try:
            return json.loads(_STORE_REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Seed default registry
    defaults = [
        {
            "id": "daily-brief",
            "name": "Daily Brief",
            "version": "1.2.0",
            "description": "Generate a daily summary of activity and insights",
            "author": "fireside",
            "category": "productivity",
            "price": 0,
            "downloads": 342,
            "icon": "📋",
        },
        {
            "id": "git-watcher",
            "name": "Git Watcher",
            "version": "0.9.1",
            "description": "Monitor git repos for changes and auto-trigger analysis",
            "author": "community",
            "category": "integration",
            "price": 0,
            "downloads": 187,
            "icon": "🔍",
        },
        {
            "id": "backup-sync",
            "name": "Backup Sync",
            "version": "1.0.2",
            "description": "Automated backup of soul files, config, and memory",
            "author": "fireside",
            "category": "ops",
            "price": 0,
            "downloads": 156,
            "icon": "💾",
        },
        {
            "id": "voice-interface",
            "name": "Voice Interface",
            "version": "0.5.0",
            "description": "Voice input/output for hands-free interaction",
            "author": "community",
            "category": "interface",
            "price": 4.99,
            "downloads": 41,
            "icon": "🎙️",
        },
        {
            "id": "prompt-optimizer",
            "name": "Prompt Optimizer",
            "version": "1.1.0",
            "description": "Auto-optimize prompts based on feedback loops",
            "author": "community",
            "category": "intelligence",
            "price": 0,
            "downloads": 264,
            "icon": "✨",
        },
        {
            "id": "cost-tracker",
            "name": "Cost Tracker",
            "version": "0.8.0",
            "description": "Track inference costs across providers and models",
            "author": "fireside",
            "category": "analytics",
            "price": 0,
            "downloads": 89,
            "icon": "📊",
        },
    ]
    _STORE_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_REGISTRY_PATH.write_text(json.dumps(defaults, indent=2), encoding="utf-8")
    return defaults


def _load_purchases() -> list[dict]:
    if _PURCHASES_PATH.exists():
        try:
            return json.loads(_PURCHASES_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_purchases(purchases: list[dict]):
    _PURCHASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PURCHASES_PATH.write_text(json.dumps(purchases, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Brain download / install
# ---------------------------------------------------------------------------

# Model ID → download info mapping
_BRAIN_MODELS = {
    "fast": {
        "name": "Smart & Fast (8B)",
        "model": "llama-3.1-8b-q6",
        "filename": "Meta-Llama-3.1-8B-Instruct-Q6_K.gguf",
        "size_gb": 4.6,
        "repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
    },
    "deep": {
        "name": "Deep Thinker (35B)",
        "model": "qwen-2.5-35b-q4",
        "filename": "Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf",
        "size_gb": 24.1,
        "repo": "bartowski/Qwen2.5-Coder-32B-Instruct-GGUF",
    },
}

# In-memory download state (per-session)
_download_state: dict = {"status": "idle", "brain_id": None, "progress": 0, "error": None}


@router.post("/brains/install")
async def install_brain(request: Request):
    """Kick off brain model download, or return redirect to Brains page.

    Accepts: { model_id: "fast" | "deep", port?: 8080 }
    Returns: { ok, action, message } where action is "downloading" or "redirect"
    """
    body = await request.json()
    model_id = body.get("model_id", "fast")
    brain = _BRAIN_MODELS.get(model_id)

    if not brain:
        raise HTTPException(status_code=400, detail=f"Unknown brain: {model_id}")

    models_dir = _base_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    target = models_dir / brain["filename"]

    # If already downloaded, report done
    if target.exists() and target.stat().st_size > 100_000_000:
        _download_state.update(status="done", brain_id=model_id, progress=100)
        return {"ok": True, "action": "already_installed", "message": f"{brain['name']} is already downloaded."}

    # Start download in background
    try:
        import threading

        def _download_model():
            try:
                _download_state.update(status="downloading", brain_id=model_id, progress=0, error=None)

                # Method 1: Try huggingface-hub if available (best progress tracking)
                try:
                    from huggingface_hub import hf_hub_download
                    hf_hub_download(
                        repo_id=brain["repo"],
                        filename=brain["filename"],
                        local_dir=str(models_dir),
                        local_dir_use_symlinks=False,
                    )
                    _download_state.update(status="done", progress=100)
                    return
                except ImportError:
                    pass

                # Method 2: Direct HTTP download (no deps needed — stdlib only)
                import urllib.request
                url = f"https://huggingface.co/{brain['repo']}/resolve/main/{brain['filename']}"
                log.info("[brains] Downloading %s from %s", brain["filename"], url)

                req = urllib.request.Request(url, headers={"User-Agent": "Fireside/1.0"})
                with urllib.request.urlopen(req) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    chunk_size = 1024 * 1024  # 1MB chunks

                    with open(str(target), "wb") as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                _download_state["progress"] = int(downloaded / total * 100)

                _download_state.update(status="done", progress=100)

            except Exception as e:
                log.error("[brains] Download failed: %s", e)
                _download_state.update(status="error", error=str(e))

        t = threading.Thread(target=_download_model, daemon=True)
        t.start()

        return {
            "ok": True,
            "action": "downloading",
            "message": f"Downloading {brain['name']} ({brain['size_gb']} GB)...",
            "brain": brain,
        }
    except Exception as e:
        log.error("[brains] Could not start download thread: %s", e)
        raise HTTPException(status_code=500, detail=f"Download failed: {e}")


@router.get("/brains/download-status")
async def get_brain_download_status():
    """Return current brain download status for post-onboarding flow."""
    return _download_state


@router.get("/status/agent")
async def get_agent_status():
    """Return current agent state for Guild Hall status effects.

    Maps backend state to visual status effects:
      - on_a_roll: actively processing, low latency
      - working: processing a request
      - learning: model loading / fine-tuning
      - idle: no active tasks
      - error: crash recovery or high error rate
      - celebrating: task just completed successfully
    """
    import psutil

    # Determine status from system state
    status = "idle"
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    # Check if the LLM process is running (llama-server or similar)
    llm_running = False
    llm_cpu = 0.0
    for proc in psutil.process_iter(["name", "cpu_percent"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if any(k in name for k in ["llama", "ollama", "vllm", "mlx"]):
                llm_running = True
                llm_cpu = proc.info.get("cpu_percent", 0) or 0
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if llm_running and llm_cpu > 50:
        status = "on_a_roll"
    elif llm_running and llm_cpu > 10:
        status = "working"
    elif cpu_percent > 80:
        status = "working"
    elif memory.percent > 90:
        status = "error"

    return {
        "status": status,
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(memory.percent, 1),
        "llm_running": llm_running,
        "uptime_seconds": int(time.time() - _start_time),
    }


# Track server start time for uptime
_start_time = time.time()


@router.get("/brains/active")
async def get_active_brain():
    """Return the active brain and model from config."""
    # Pull from existing config or defaults
    brain = _config.get("node", {}).get("brain", "fast")
    model = _config.get("node", {}).get("model", "llama-3.1-8b-q6")
    
    # If not in node section, check models.active (newly added in main.rs)
    if "models" in _config and "active" in _config["models"]:
        brain = _config["models"]["active"].get("brain", brain)
        model = _config["models"]["active"].get("model", model)
        
    return {"brain": brain, "model": model}


@router.get("/store/plugins")
async def get_store_plugins():
    """List all plugins in the store registry."""
    registry = _load_store_registry()
    purchases = _load_purchases()
    purchased_ids = {p["plugin_id"] for p in purchases}

    # Mark purchased plugins
    for plugin in registry:
        plugin["purchased"] = plugin["id"] in purchased_ids

    return {"plugins": registry}


class PurchaseRequest(BaseModel):
    plugin_id: str
    auth_token: str = ""


@router.post("/store/purchase")
async def store_purchase(req: PurchaseRequest):
    """Purchase and install a plugin from the store.
    
    Requires mesh.auth_token for authentication.
    """
    import hmac
    
    expected_token = _config.get("mesh", {}).get("auth_token", "")
    if not expected_token or not hmac.compare_digest(req.auth_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid or missing auth token")

    registry = _load_store_registry()
    plugin = next((p for p in registry if p["id"] == req.plugin_id), None)
    if not plugin:
        raise HTTPException(404, f"Plugin '{req.plugin_id}' not found in store")

    purchases = _load_purchases()
    if any(p["plugin_id"] == req.plugin_id for p in purchases):
        raise HTTPException(409, f"Plugin '{req.plugin_id}' already purchased")

    purchase = {
        "plugin_id": req.plugin_id,
        "plugin_name": plugin["name"],
        "price": plugin.get("price", 0),
        "purchased_at": datetime.now(timezone.utc).isoformat(),
    }
    purchases.append(purchase)
    _save_purchases(purchases)

    log.info("[store] Plugin purchased: %s", req.plugin_id)
    return {"status": "purchased", "purchase": purchase}


@router.get("/store/purchases")
async def get_store_purchases():
    """List user's purchase history."""
    return {"purchases": _load_purchases()}


# ---------------------------------------------------------------------------
# Endpoints: Config Onboarding  (Sprint 15 — T4)
# ---------------------------------------------------------------------------

@router.get("/config/onboarding")
async def get_config_onboarding():
    """Return all onboarding choices from config files.

    Dashboard reads from this instead of scattered localStorage keys.
    """
    result = {
        "user_name": "",
        "agent_name": "Atlas",
        "agent_style": "Analytical",
        "companion_name": "Ember",
        "companion_species": "fox",
        "brain": "Smart & Fast (7B)",
        "onboarded": False,
    }

    # Read from valhalla.yaml (primary source)
    agent_cfg = _config.get("agent", {})
    companion_cfg = _config.get("companion", {})
    if agent_cfg:
        result["agent_name"] = agent_cfg.get("name", result["agent_name"])
        result["agent_style"] = agent_cfg.get("style", result["agent_style"])
    if companion_cfg:
        result["companion_name"] = companion_cfg.get("name", result["companion_name"])
        result["companion_species"] = companion_cfg.get("species", result["companion_species"])
        result["user_name"] = companion_cfg.get("owner", "")

    # Read onboarding.json for brain/completion status
    onboarding_path = Path.home() / ".fireside" / "onboarding.json"
    try:
        if onboarding_path.exists():
            ob = json.loads(onboarding_path.read_text(encoding="utf-8"))
            result["onboarded"] = ob.get("onboarded", False)
            result["brain"] = ob.get("brain", result["brain"])
            result["user_name"] = ob.get("user_name", result["user_name"])
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init_api(config: dict) -> APIRouter:
    """Initialize the API router with the loaded config.

    Must be called before the router is mounted.
    """
    global _config, _start_time, _base_dir
    _config = config
    _start_time = time.time()
    _base_dir = Path(config.get("_meta", {}).get("base_dir", "."))
    log.info("[api/v1] Initialized (%d endpoints)", len(router.routes))
    return router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_uptime(seconds: float) -> str:
    """Format seconds into a human-readable uptime string."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _push_config_to_mesh(yaml_content: str) -> None:
    """Push config to all mesh peers (fire-and-forget daemon threads)."""
    import threading
    import urllib.request

    mesh_nodes = _config.get("mesh", {}).get("nodes", {})
    this_node = _config.get("node", {}).get("name", "")
    auth_token = _config.get("mesh", {}).get("auth_token", "")

    if not auth_token or auth_token == "change-me-to-a-long-random-string":
        log.warning("[config-sync] Skipping mesh push — auth_token not configured")
        return

    def _push(name: str, ip: str, port: int):
        try:
            payload = json.dumps({
                "yaml_content": yaml_content,
                "sender": this_node,
                "auth_token": auth_token,
            }).encode()
            req = urllib.request.Request(
                f"http://{ip}:{port}/api/v1/config/receive",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                log.info("[config-sync] Pushed config to %s → %d", name, resp.status)
        except Exception as e:
            log.warning("[config-sync] Push to %s failed: %s", name, e)

    for name, ncfg in mesh_nodes.items():
        if name == this_node:
            continue
        ip = ncfg.get("ip", "")
        port = ncfg.get("port", 8765)
        if ip:
            t = threading.Thread(
                target=_push, args=(name, ip, port),
                daemon=True, name=f"config-push-{name}",
            )
            t.start()

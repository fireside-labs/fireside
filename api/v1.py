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
from pydantic import BaseModel

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
        "gpu": gpu,
        "inference": inference,
    }


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

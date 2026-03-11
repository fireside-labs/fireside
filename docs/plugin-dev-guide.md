# Plugin Developer Guide

---

## The Two-File Plugin

A Valhalla plugin is a folder with two files:

```
plugins/my-plugin/
├── plugin.yaml     ← manifest: what your plugin is
└── handler.py      ← logic: what your plugin does
```

Drop this folder into `plugins/`. Bifrost auto-loads it. No build step, no package manager, no binary.

---

## plugin.yaml Reference

```yaml
# Required
name: daily-brief                              # Unique ID, kebab-case
version: 1.0.0                                 # Semver
description: Morning summary of overnight mesh activity   # Max 120 chars
author: your-username

# Routes your plugin registers (optional)
routes:
  - method: GET
    path: /daily-brief
  - method: POST
    path: /daily-brief/generate

# Events your plugin emits (optional)
events:
  - daily-brief.generated
  - daily-brief.error

# Config keys your plugin reads from valhalla.yaml (optional)
config_keys:
  - daily_brief.timezone
  - daily_brief.include_predictions

# Marketplace metadata (optional, for published plugins)
license: MIT
category: automation         # automation | monitoring | security | memory | integration | utility
tags: [morning, summary, report]
min_valhalla_version: 2.0.0
dependencies: []             # Other plugin names this depends on
```

### Rules
- `name` must match the folder name exactly
- `routes[].path` is relative — Bifrost mounts at root, so `/daily-brief` becomes `http://localhost:8765/daily-brief`
- `config_keys` are dot-paths into `valhalla.yaml` — your plugin reads them but doesn't own them
- `events` are namespaced by plugin name by convention

---

## handler.py Reference

You implement up to four functions. Only `register_routes` is required.

```python
"""
daily-brief plugin — Morning summary of overnight activity.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter

log = logging.getLogger("valhalla.plugin.daily-brief")
router = APIRouter(tags=["daily-brief"])


def register_routes(app, config: dict) -> None:
    """
    Called once at startup. Register your HTTP routes here.

    Args:
        app:    The FastAPI application instance
        config: Full valhalla.yaml as a dict (already parsed, env vars resolved)
    """
    # Read your config
    tz = config.get("daily_brief", {}).get("timezone", "UTC")

    @router.get("/daily-brief")
    async def get_brief():
        return {"status": "ok", "timezone": tz, "brief": "..."}

    @router.post("/daily-brief/generate")
    async def generate_brief():
        # Your logic here
        log.info("[daily-brief] Generating morning brief")
        return {"ok": True}

    app.include_router(router)
    log.info("[daily-brief] Registered (timezone: %s)", tz)


def on_event(event_name: str, payload: dict, config: dict) -> None:
    """
    Called when a subscribed event fires. Optional.

    You'll receive events listed in your plugin.yaml's `events` field,
    plus any events you explicitly subscribe to.
    """
    if event_name == "model.switched":
        log.info("[daily-brief] Model changed to %s", payload.get("model"))


def on_config_change(key: str, old_value, new_value) -> None:
    """
    Called when a config key you declared in `config_keys` changes. Optional.
    This fires on hot-reload (PUT /api/v1/config).
    """
    log.info("[daily-brief] Config changed: %s = %s → %s", key, old_value, new_value)


def health_check() -> bool:
    """
    Called by the watchdog plugin periodically. Optional.
    Return True if your plugin is healthy.
    """
    return True
```

---

## How Plugin Loading Works

Here's exactly what `plugin_loader.py` does at startup:

```
1. Scans plugins/ for subdirectories
2. For each subdirectory:
   a. Reads plugin.yaml — validates name, version, description
   b. Imports handler.py as a Python module
   c. Calls handler.register_routes(app, config)
   d. Logs success or failure
3. Returns list of loaded plugin metadata
```

**Only plugins listed in `valhalla.yaml` under `plugins.enabled` are loaded:**

```yaml
plugins:
  enabled:
    - model-switch
    - watchdog
    - daily-brief    # ← add your plugin here
```

If a plugin folder exists but isn't in `enabled`, it's ignored.

---

## Accessing Config

Your plugin gets the full `valhalla.yaml` as a parsed dict. Access your keys with standard dict operations:

```python
def register_routes(app, config: dict) -> None:
    # Top-level section
    node_name = config["node"]["name"]           # "odin"
    node_role = config["node"]["role"]            # "orchestrator"

    # Your plugin's config keys
    tz = config.get("daily_brief", {}).get("timezone", "UTC")

    # Model info
    current_model = config["models"]["default"]  # "llama/Qwen3.5-35B-A3B-8bit"
    aliases = config["models"]["aliases"]         # {"odin": "...", "hugs": "..."}

    # Mesh peers
    peers = config.get("mesh", {}).get("nodes", {})
    for name, info in peers.items():
        print(f"{name}: {info['ip']}:{info['port']} ({info['role']})")
```

**Add your default config to `valhalla.yaml`:**

```yaml
daily_brief:
  timezone: America/Phoenix
  include_predictions: true
  max_events: 50
```

---

## Emitting Events

Events are how plugins communicate. The event bus is a shared in-process pub/sub system.

```python
from plugin_loader import emit_event  # available after Sprint 2

def register_routes(app, config):

    @router.post("/daily-brief/generate")
    async def generate():
        brief = build_brief()

        # Emit an event — other plugins can listen for this
        emit_event("daily-brief.generated", {
            "timestamp": time.time(),
            "sections": len(brief["sections"]),
        })

        return brief
```

**Sprint 2 adds the full event bus.** In Sprint 1, you can log events and they'll be picked up when the bus ships.

---

## Example: Building "daily-brief" From Scratch

### 1. Create the folder

```bash
mkdir -p plugins/daily-brief
```

### 2. Write plugin.yaml

```yaml
name: daily-brief
version: 1.0.0
description: Morning summary of overnight mesh activity
author: jordan
routes:
  - method: GET
    path: /daily-brief
  - method: POST
    path: /daily-brief/generate
config_keys:
  - daily_brief.timezone
  - daily_brief.max_events
```

### 3. Write handler.py

```python
"""daily-brief — morning summary plugin."""
from __future__ import annotations
import logging
import time
from fastapi import APIRouter

log = logging.getLogger("valhalla.plugin.daily-brief")
router = APIRouter(tags=["daily-brief"])

_last_brief = None


def register_routes(app, config: dict) -> None:
    tz = config.get("daily_brief", {}).get("timezone", "UTC")
    max_events = config.get("daily_brief", {}).get("max_events", 50)

    @router.get("/daily-brief")
    async def get_brief():
        if _last_brief is None:
            return {"status": "none", "message": "No brief generated yet. POST /daily-brief/generate"}
        return _last_brief

    @router.post("/daily-brief/generate")
    async def generate():
        global _last_brief
        _last_brief = {
            "generated_at": time.time(),
            "timezone": tz,
            "summary": "Mesh was quiet overnight. 2 model switches, 0 errors.",
            "events_scanned": max_events,
        }
        log.info("[daily-brief] Generated brief (%d events scanned)", max_events)
        return _last_brief

    app.include_router(router)
    log.info("[daily-brief] Registered (tz=%s, max_events=%d)", tz, max_events)


def health_check() -> bool:
    return True
```

### 4. Add to valhalla.yaml

```yaml
plugins:
  enabled:
    - model-switch
    - watchdog
    - daily-brief      # ← add this

daily_brief:
  timezone: America/Phoenix
  max_events: 50
```

### 5. Test it

```bash
# Restart Bifrost (or it hot-reloads if running)
python bifrost.py

# Generate a brief
curl -X POST http://localhost:8765/daily-brief/generate

# Read the brief
curl http://localhost:8765/daily-brief
```

---

## Publishing to the Marketplace

```bash
# Package your plugin
valhalla plugin pack
# → daily-brief-1.0.0.tar.gz

# Submit for review
valhalla plugin submit
```

See [marketplace.md](marketplace.md) for review criteria and revenue details.

---

## Gotchas

| Issue | Fix |
|---|---|
| Plugin folder name ≠ `name` in plugin.yaml | They must match exactly |
| Plugin not loading | Is it listed in `plugins.enabled` in valhalla.yaml? |
| Routes conflict with another plugin | Use your plugin name as a path prefix: `/daily-brief/...` |
| `import some_package` fails | Install the package in the same Python environment as Bifrost |
| `register_routes` not called | Check the Bifrost logs — errors during import are logged |
| Config changes not picked up | `on_config_change` only fires on hot-reload via `PUT /api/v1/config` |

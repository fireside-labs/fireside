"""
plugin_loader.py — Dynamic plugin system for Valhalla Mesh V2.

Scans the plugins/ directory, reads each plugin.yaml manifest,
dynamically imports handler.py, and calls register_routes(app, config)
at startup.
"""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("valhalla.plugins")

_BASE_DIR = Path(__file__).parent
_PLUGINS_DIR = _BASE_DIR / "plugins"

# Registry of loaded plugins
_loaded_plugins: list[dict[str, Any]] = []


def _load_plugin_manifest(plugin_dir: Path) -> dict | None:
    """Read and parse a plugin.yaml manifest."""
    manifest_path = plugin_dir / "plugin.yaml"
    if not manifest_path.exists():
        log.warning("No plugin.yaml in %s — skipping", plugin_dir.name)
        return None

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    if not isinstance(manifest, dict) or "name" not in manifest:
        log.warning("Invalid plugin.yaml in %s — missing 'name'", plugin_dir.name)
        return None

    manifest["_dir"] = str(plugin_dir)
    return manifest


def _import_handler(plugin_dir: Path, plugin_name: str):
    """Dynamically import handler.py from a plugin directory."""
    handler_path = plugin_dir / "handler.py"
    if not handler_path.exists():
        log.warning("No handler.py in plugin '%s' — skipping", plugin_name)
        return None

    spec = importlib.util.spec_from_file_location(
        f"plugins.{plugin_name}.handler", str(handler_path)
    )
    if spec is None or spec.loader is None:
        log.error("Could not create module spec for plugin '%s'", plugin_name)
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_plugins(plugins_dir: Path | None = None) -> list[dict]:
    """Discover all plugin manifests in the plugins directory.

    Returns a list of parsed plugin.yaml dicts.
    """
    pdir = plugins_dir or _PLUGINS_DIR
    if not pdir.is_dir():
        log.info("No plugins/ directory found at %s", pdir)
        return []

    manifests = []
    for child in sorted(pdir.iterdir()):
        if child.is_dir():
            manifest = _load_plugin_manifest(child)
            if manifest:
                manifests.append(manifest)

    return manifests


def load_plugins(app, config: dict, plugins_dir: Path | None = None) -> list[dict]:
    """Load and register all enabled plugins.

    For each plugin listed in config['plugins']['enabled']:
      1. Read its plugin.yaml
      2. Import handler.py
      3. Call handler.register_routes(app, config)

    Returns a list of loaded plugin manifests.
    """
    global _loaded_plugins, _loaded_handlers
    _loaded_plugins = []
    _loaded_handlers = {}

    enabled = config.get("plugins", {}).get("enabled", [])
    pdir = plugins_dir or _PLUGINS_DIR

    if not pdir.is_dir():
        log.warning("Plugins directory not found: %s", pdir)
        return _loaded_plugins

    for plugin_name in enabled:
        plugin_dir = pdir / plugin_name
        if not plugin_dir.is_dir():
            log.warning("Plugin '%s' is enabled but directory not found", plugin_name)
            continue

        manifest = _load_plugin_manifest(plugin_dir)
        if manifest is None:
            continue

        handler_module = _import_handler(plugin_dir, plugin_name)
        if handler_module is None:
            continue

        # Use sandbox for safe registration (circuit breaker + import audit)
        loaded = False
        try:
            from plugins.sandbox import safe_register_routes
            success = safe_register_routes(handler_module, app, config, plugin_name)
            if success:
                manifest["_status"] = "loaded"
                loaded = True
                log.info("✓ Plugin loaded: %s v%s",
                         manifest["name"], manifest.get("version", "?"))
            else:
                manifest["_status"] = "blocked (sandbox)"
                log.warning("✗ Plugin '%s' blocked by sandbox", plugin_name)
        except ImportError:
            # Fallback: sandbox not available, load directly
            register_fn = getattr(handler_module, "register_routes", None)
            if register_fn is None:
                log.warning("Plugin '%s' has no register_routes() function", plugin_name)
                continue
            try:
                register_fn(app, config)
                manifest["_status"] = "loaded"
                loaded = True
                log.info("✓ Plugin loaded: %s v%s",
                         manifest["name"], manifest.get("version", "?"))
            except Exception as e:
                manifest["_status"] = f"error: {e}"
                log.error("✗ Plugin '%s' failed to load: %s", plugin_name, e)

        # Track handler module for hook calls (Sprint 3)
        if loaded:
            _loaded_handlers[plugin_name] = handler_module

        _loaded_plugins.append(manifest)

    log.info("Loaded %d/%d plugins", len(_loaded_plugins), len(enabled))

    # Warm model connection (Sprint 3 — performance)
    model_preconnect(config)

    return _loaded_plugins



def get_plugins() -> list[dict]:
    """Return metadata for all loaded plugins."""
    return [
        {
            "name": p.get("name"),
            "version": p.get("version", "0.0.0"),
            "description": p.get("description", ""),
            "author": p.get("author", ""),
            "routes": p.get("routes", []),
            "events": p.get("events", []),
            "config_keys": p.get("config_keys", []),
            "status": p.get("_status", "unknown"),
        }
        for p in _loaded_plugins
    ]


# ---------------------------------------------------------------------------
# Plugin hooks — Sprint 3
# ---------------------------------------------------------------------------

# Handler modules indexed by plugin name (for calling hooks)
_loaded_handlers: dict[str, Any] = {}


def emit_event(event_name: str, payload: dict) -> None:
    """Emit an event to the event bus — convenience for plugins.

    Referenced in Valkyrie's plugin-dev-guide as:
        from plugin_loader import emit_event
    """
    try:
        eb_handler = _loaded_handlers.get("event-bus")
        if eb_handler and hasattr(eb_handler, "publish"):
            eb_handler.publish(event_name, payload)
    except Exception as e:
        log.debug("[plugins] emit_event failed: %s", e)


def notify_config_change(key: str, old_value, new_value) -> None:
    """Notify all loaded plugins of a config change.

    Calls on_config_change(key, old_value, new_value) on each handler
    that implements it. Called by config_loader on hot-reload.
    """
    for name, handler in _loaded_handlers.items():
        callback = getattr(handler, "on_config_change", None)
        if callback:
            try:
                callback(key, old_value, new_value)
            except Exception as e:
                log.warning("[plugins] %s.on_config_change failed: %s", name, e)


def check_plugin_health() -> dict:
    """Call health_check() on all plugins that implement it.

    Returns {plugin_name: bool} for each plugin with a health_check.
    """
    results = {}
    for name, handler in _loaded_handlers.items():
        check = getattr(handler, "health_check", None)
        if check:
            try:
                results[name] = check()
            except Exception:
                results[name] = False
    return results


def model_preconnect(config: dict) -> None:
    """Warm the inference connection at startup (fire-and-forget).

    Sends a minimal request to the default model provider to establish
    the TCP connection and trigger any model loading on the inference side.
    """
    import threading

    def _warmup():
        import json
        import urllib.request

        providers = config.get("models", {}).get("providers", {})
        default_model = config.get("models", {}).get("default", "")

        # Determine provider from model string (e.g. "llama/..." → llama provider)
        provider_key = default_model.split("/")[0] if "/" in default_model else ""
        provider = providers.get(provider_key, {})
        url = provider.get("url", "")

        if not url:
            return

        # Send a lightweight models list request
        try:
            models_url = url.rstrip("/")
            if not models_url.endswith("/models"):
                models_url += "/models"
            req = urllib.request.Request(models_url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as r:
                log.info("[preconnect] Model provider at %s is warm (%d)",
                         url, r.status)
        except Exception as e:
            log.debug("[preconnect] Warmup to %s failed (non-critical): %s", url, e)

    t = threading.Thread(target=_warmup, daemon=True, name="model-preconnect")
    t.start()


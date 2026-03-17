"""
plugins/__init__.py — Module alias bridge for hyphenated plugin directories.

Python can't import "plugins.brain-installer" because hyphens are invalid
in identifiers.  This __init__.py registers sys.modules aliases so that
"plugins.brain_installer.handler" resolves to the file at
"plugins/brain-installer/handler.py".

The runtime plugin_loader.py uses importlib.util.spec_from_file_location()
directly (bypassing this), so this only matters for:
  - Unit tests: from plugins.brain_installer.handler import register_routes
  - Cross-plugin imports: from plugins.event_bus.handler import publish
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PLUGINS_DIR = Path(__file__).parent

# Map of underscored module names → actual hyphenated directory names
_HYPHENATED = {
    "adaptive_thinking": "adaptive-thinking",
    "belief_shadows": "belief-shadows",
    "brain_installer": "brain-installer",
    "consumer_api": "consumer-api",
    "context_compactor": "context-compactor",
    "event_bus": "event-bus",
    "model_router": "model-router",
    "model_switch": "model-switch",
    "philosopher_stone": "philosopher-stone",
    "self_model": "self-model",
    "task_persistence": "task-persistence",
    "working_memory": "working-memory",
}


def _register_alias(underscored: str, hyphenated: str) -> None:
    """Register a sys.modules alias so 'plugins.{underscored}.handler' works."""
    handler_path = _PLUGINS_DIR / hyphenated / "handler.py"
    if not handler_path.exists():
        return

    pkg_key = f"plugins.{underscored}"
    handler_key = f"plugins.{underscored}.handler"

    # Skip if already registered
    if handler_key in sys.modules:
        return

    try:
        # Create a package-like module for plugins.{underscored}
        import types
        pkg = types.ModuleType(pkg_key)
        pkg.__path__ = [str(_PLUGINS_DIR / hyphenated)]
        pkg.__package__ = pkg_key
        sys.modules[pkg_key] = pkg

        # Load the handler
        spec = importlib.util.spec_from_file_location(
            handler_key, str(handler_path)
        )
        if spec and spec.loader:
            handler = importlib.util.module_from_spec(spec)
            handler.__package__ = pkg_key
            sys.modules[handler_key] = handler
            spec.loader.exec_module(handler)
            pkg.handler = handler  # type: ignore[attr-defined]
    except Exception:
        # Don't crash the entire plugins package if one alias fails
        pass


# Register all aliases on import
for _underscored, _hyphenated in _HYPHENATED.items():
    _register_alias(_underscored, _hyphenated)

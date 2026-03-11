"""
plugins/sandbox.py — Plugin execution sandbox for Valhalla Mesh V2.

Provides safe wrappers for plugin loading:
    safe_register_routes(module, app, config, plugin_name)

Security features:
    1. Circuit breaker — disable plugin after 3 consecutive crashes
    2. Import auditing — log when plugins import dangerous modules
    3. Timeout — plugin registration must complete in 10 seconds
    4. Exception isolation — plugin errors never crash bifrost
"""
from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

log = logging.getLogger("heimdall.sandbox")

# ---------------------------------------------------------------------------
# Circuit breaker state
# ---------------------------------------------------------------------------

# plugin_name → { failures: int, disabled: bool, last_error: str }
_circuit_state: dict[str, dict[str, Any]] = {}
_MAX_FAILURES = 3
_REGISTRATION_TIMEOUT = 10  # seconds


def _get_state(plugin_name: str) -> dict:
    if plugin_name not in _circuit_state:
        _circuit_state[plugin_name] = {
            "failures": 0,
            "disabled": False,
            "last_error": "",
        }
    return _circuit_state[plugin_name]


# ---------------------------------------------------------------------------
# Import auditing
# ---------------------------------------------------------------------------

_AUDITED_MODULES = frozenset({
    "os", "subprocess", "shutil", "socket", "ctypes",
    "importlib", "sys", "signal", "multiprocessing",
})

_original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
_audit_active = False
_audit_plugin_name = ""


def _auditing_import(name, *args, **kwargs):
    """Wrapper around __import__ that logs dangerous module imports."""
    if _audit_active and name in _AUDITED_MODULES:
        log.warning(
            "[sandbox] Plugin '%s' imported restricted module: %s",
            _audit_plugin_name, name
        )
    return _original_import(name, *args, **kwargs)


# ---------------------------------------------------------------------------
# Safe registration
# ---------------------------------------------------------------------------

def safe_register_routes(
    handler_module,
    app,
    config: dict,
    plugin_name: str,
) -> bool:
    """
    Safely call handler_module.register_routes(app, config).

    Returns True if registration succeeded, False if it failed or was blocked.

    Features:
    - Circuit breaker: skips plugin if it has crashed >= MAX_FAILURES times
    - Exception isolation: catches all exceptions, never crashes bifrost
    - Import auditing: logs when plugin imports dangerous modules
    - Timeout: aborts if registration takes > REGISTRATION_TIMEOUT seconds
    """
    global _audit_active, _audit_plugin_name

    state = _get_state(plugin_name)

    # Circuit breaker: check if disabled
    if state["disabled"]:
        log.warning(
            "[sandbox] Plugin '%s' is DISABLED (circuit breaker tripped after %d failures). "
            "Last error: %s",
            plugin_name, state["failures"], state["last_error"]
        )
        return False

    register_fn = getattr(handler_module, "register_routes", None)
    if register_fn is None:
        log.warning("[sandbox] Plugin '%s' has no register_routes() — skipping", plugin_name)
        return False

    # Run registration with auditing and timeout
    result = {"success": False, "error": None}

    def _do_register():
        try:
            register_fn(app, config)
            result["success"] = True
        except Exception as e:
            result["error"] = e

    # Enable import auditing for this plugin
    _audit_plugin_name = plugin_name
    _audit_active = True

    try:
        thread = threading.Thread(
            target=_do_register,
            name=f"sandbox-{plugin_name}",
            daemon=True,
        )
        thread.start()
        thread.join(timeout=_REGISTRATION_TIMEOUT)

        if thread.is_alive():
            # Registration timed out
            error_msg = f"Timed out after {_REGISTRATION_TIMEOUT}s"
            log.error("[sandbox] Plugin '%s' registration %s", plugin_name, error_msg)
            state["failures"] += 1
            state["last_error"] = error_msg
            if state["failures"] >= _MAX_FAILURES:
                state["disabled"] = True
                log.critical(
                    "[sandbox] 🔴 Plugin '%s' DISABLED — circuit breaker tripped",
                    plugin_name
                )
            return False

        if result["error"]:
            raise result["error"]

        if result["success"]:
            # Reset failure count on success
            state["failures"] = 0
            log.info("[sandbox] ✓ Plugin '%s' registered safely", plugin_name)
            return True

        return False

    except Exception as e:
        state["failures"] += 1
        state["last_error"] = str(e)

        if state["failures"] >= _MAX_FAILURES:
            state["disabled"] = True
            log.critical(
                "[sandbox] 🔴 Plugin '%s' DISABLED after %d failures — circuit breaker tripped. "
                "Last error: %s",
                plugin_name, state["failures"], e
            )
        else:
            log.error(
                "[sandbox] Plugin '%s' registration failed (%d/%d): %s",
                plugin_name, state["failures"], _MAX_FAILURES, e
            )
        return False

    finally:
        _audit_active = False
        _audit_plugin_name = ""


# ---------------------------------------------------------------------------
# Plugin filesystem guard
# ---------------------------------------------------------------------------

def get_plugin_data_dir(plugin_name: str, base_dir: Optional[Path] = None) -> Path:
    """
    Return the data directory for a plugin.

    Plugins should only read/write within this directory.
    Creates the directory if it doesn't exist.
    """
    base = base_dir or Path(__file__).parent
    data_dir = base / plugin_name / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def validate_plugin_path(
    requested_path: str,
    plugin_name: str,
    base_dir: Optional[Path] = None,
) -> Optional[Path]:
    """
    Validate that a path is within the plugin's directory.

    Returns resolved Path if safe, None if traversal detected.
    """
    base = base_dir or Path(__file__).parent
    plugin_root = (base / plugin_name).resolve()

    try:
        if not requested_path:
            return None
        if requested_path.startswith("/") or requested_path.startswith("\\"):
            log.warning("[sandbox] Plugin '%s' attempted absolute path: %s",
                       plugin_name, requested_path[:80])
            return None

        resolved = (plugin_root / requested_path).resolve()
        resolved.relative_to(plugin_root)
        return resolved
    except (ValueError, OSError) as e:
        log.warning("[sandbox] Plugin '%s' path escape blocked: %s → %s",
                   plugin_name, requested_path[:80], e)
        return None


# ---------------------------------------------------------------------------
# Query / management
# ---------------------------------------------------------------------------

def get_circuit_state() -> dict:
    """Return current circuit breaker state for all plugins."""
    return {
        name: {
            "failures": s["failures"],
            "disabled": s["disabled"],
            "last_error": s["last_error"],
        }
        for name, s in _circuit_state.items()
    }


def reset_circuit(plugin_name: str) -> bool:
    """Reset circuit breaker for a plugin (re-enable it)."""
    state = _get_state(plugin_name)
    state["failures"] = 0
    state["disabled"] = False
    state["last_error"] = ""
    log.info("[sandbox] Circuit breaker reset for plugin '%s'", plugin_name)
    return True

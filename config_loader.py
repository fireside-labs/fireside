"""
config_loader.py — Unified YAML config for Valhalla Mesh V2.

Reads valhalla.yaml, resolves ${ENV_VAR} references, validates schema,
and exposes a get_config() singleton.  All plugins and core use this
instead of scattered JSON files.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("valhalla.config")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).parent
_DEFAULT_CONFIG_PATH = _BASE_DIR / "valhalla.yaml"

_REQUIRED_KEYS = {"node", "plugins"}

# Singleton
_config: dict | None = None
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# ENV var resolution
# ---------------------------------------------------------------------------
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_env(value: Any) -> Any:
    """Recursively resolve ${ENV_VAR} references in strings, lists, dicts."""
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            var = match.group(1)
            resolved = os.environ.get(var, "")
            if not resolved:
                log.warning("Environment variable ${%s} is not set", var)
            return resolved
        return _ENV_PATTERN.sub(_replace, value)
    elif isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Raised when config is invalid."""


def _validate(config: dict) -> None:
    """Validate that required top-level keys exist and have sane types."""
    missing = _REQUIRED_KEYS - set(config.keys())
    if missing:
        raise ConfigError(f"Missing required config keys: {missing}")

    # node
    node = config["node"]
    if not isinstance(node, dict):
        raise ConfigError("'node' must be a mapping")
    if "name" not in node:
        raise ConfigError("'node.name' is required")
    node.setdefault("port", 8765)

    # mesh — optional for single-node installs
    if "mesh" in config:
        mesh = config["mesh"]
        if not isinstance(mesh, dict):
            raise ConfigError("'mesh' must be a mapping")
    else:
        config["mesh"] = {"nodes": {}, "auth_token": ""}

    # models — optional, default to local llama
    if "models" in config:
        models = config["models"]
        if not isinstance(models, dict):
            raise ConfigError("'models' must be a mapping")
    else:
        config["models"] = {
            "default": "llama/local",
            "providers": {
                "llama": {"url": "http://127.0.0.1:8080/v1", "key": "local", "api": "openai-completions"}
            },
            "aliases": {},
        }

    # plugins
    plugins = config["plugins"]
    if not isinstance(plugins, dict):
        raise ConfigError("'plugins' must be a mapping")
    if "enabled" not in plugins:
        raise ConfigError("'plugins.enabled' is required")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(path: str | Path | None = None) -> dict:
    """Load, resolve, and validate a valhalla.yaml file.

    Returns the fully-resolved config dict.  Does NOT set the singleton —
    use reload_config() or get_config() for that.
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    log.info("Loading config from %s", config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError("Config file must be a YAML mapping")

    config = _resolve_env(raw)
    _validate(config)

    # Inject metadata
    config["_meta"] = {
        "config_path": str(config_path.resolve()),
        "base_dir": str(config_path.parent.resolve()),
    }

    return config


def get_config(path: str | Path | None = None) -> dict:
    """Return the singleton config, loading it on first call."""
    global _config
    if _config is None:
        with _lock:
            if _config is None:
                _config = load_config(path)
    return _config


def reload_config(path: str | Path | None = None) -> dict:
    """Force-reload the config from disk and update the singleton."""
    global _config
    with _lock:
        _config = load_config(path)
    log.info("Config reloaded successfully")
    return _config


def get_config_raw_yaml(path: str | Path | None = None) -> str:
    """Return the raw YAML text of the config file (for the config editor)."""
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    return config_path.read_text(encoding="utf-8")


def save_config_yaml(yaml_text: str, path: str | Path | None = None) -> dict:
    """Write new YAML to disk, validate it, and reload the singleton.

    Returns the newly-loaded config dict.
    Raises ConfigError if the new YAML is invalid.
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH

    # Parse + validate before writing
    try:
        raw = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")
    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping")
    resolved = _resolve_env(raw)
    _validate(resolved)

    # Write
    config_path.write_text(yaml_text, encoding="utf-8")
    log.info("Config saved to %s", config_path)

    # Reload singleton
    return reload_config(path)

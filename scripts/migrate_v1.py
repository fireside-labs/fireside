#!/usr/bin/env python3
"""
migrate_v1.py — V1 → V2 Config Migration Tool.

Reads V1's scattered JSON config files and generates a unified valhalla.yaml.

Usage:
    python3 scripts/migrate_v1.py bot/
    python3 scripts/migrate_v1.py bot/ --output valhalla.yaml
    python3 scripts/migrate_v1.py bot/ --node odin
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger("migrate_v1")


# ---------------------------------------------------------------------------
# JSON reading helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Optional[dict]:
    """Read a JSON file, returning None on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Could not read %s: %s", path, e)
    return None


def _guess_node_name() -> str:
    """Guess the node name from hostname."""
    hostname = socket.gethostname().lower()
    # Common OpenClaw hostnames
    for name in ["odin", "thor", "freya", "heimdall", "hermes"]:
        if name in hostname:
            return name
    return hostname.split(".")[0]


# ---------------------------------------------------------------------------
# V1 Config parsing
# ---------------------------------------------------------------------------

def parse_v1_configs(v1_dir: Path, node_name: str) -> dict:
    """Parse all V1 JSON configs into a V2 config dict."""

    v2 = {
        "node": {"name": node_name, "role": "worker", "port": 8765},
        "mesh": {"auth_token": "change-me-to-a-long-random-string", "nodes": {}},
        "dashboard": {
            "auth_key": "change-me-dashboard-key",
            "allow_localhost": True,
            "cors_origins": ["http://localhost:3000", "http://localhost:3001"],
        },
        "models": {
            "default": "llama/Qwen3.5-35B-A3B-8bit",
            "providers": {},
            "aliases": {},
        },
        "plugins": {"enabled": ["model-switch", "watchdog"]},
        "soul": {},
    }

    # -----------------------------------------------------------------------
    # 1. Node-specific config: config.<node>.json or config.json
    # -----------------------------------------------------------------------
    node_config = _read_json(v1_dir / f"config.{node_name}.json")
    if not node_config:
        node_config = _read_json(v1_dir / "config.json")
    if not node_config:
        # Try any config.*.json
        for f in sorted(v1_dir.glob("config.*.json")):
            node_config = _read_json(f)
            if node_config:
                log.info("Using config from %s", f.name)
                break

    if node_config:
        # Extract port
        v2["node"]["port"] = node_config.get("port", 8765)

        # Extract role
        if "role" in node_config:
            v2["node"]["role"] = node_config["role"]
        elif node_name == "odin":
            v2["node"]["role"] = "orchestrator"

        # Extract model config
        if "model" in node_config:
            v2["models"]["default"] = node_config["model"]
        if "default_model" in node_config:
            v2["models"]["default"] = node_config["default_model"]

        # Extract inference providers
        if "ollama_base" in node_config or "ollama" in node_config:
            ollama_url = node_config.get("ollama_base",
                         node_config.get("ollama", {}).get("url", "http://127.0.0.1:11434"))
            v2["models"]["providers"]["llama"] = {
                "url": ollama_url,
                "key": "local",
                "api": "openai-completions",
            }

        if "nvidia_api_key" in node_config or "nvidia" in node_config:
            v2["models"]["providers"]["nvidia"] = {
                "url": "https://integrate.api.nvidia.com/v1",
                "key": "${NVIDIA_API_KEY}",
                "api": "openai-completions",
            }

        # Extract aliases
        if "aliases" in node_config:
            v2["models"]["aliases"] = node_config["aliases"]
        if "model_aliases" in node_config:
            v2["models"]["aliases"] = node_config["model_aliases"]

        # Extract mesh nodes
        if "nodes" in node_config:
            for name, info in node_config["nodes"].items():
                if isinstance(info, dict):
                    v2["mesh"]["nodes"][name] = {
                        "ip": info.get("ip", info.get("host", "")),
                        "port": info.get("port", 8765),
                        "role": info.get("role", "worker"),
                    }
                elif isinstance(info, str):
                    # Simple "name": "ip:port" format
                    parts = info.split(":")
                    v2["mesh"]["nodes"][name] = {
                        "ip": parts[0],
                        "port": int(parts[1]) if len(parts) > 1 else 8765,
                        "role": "worker",
                    }

        # Auth tokens
        if "auth_token" in node_config:
            v2["mesh"]["auth_token"] = node_config["auth_token"]
        if "dashboard_key" in node_config:
            v2["dashboard"]["auth_key"] = node_config["dashboard_key"]

    # -----------------------------------------------------------------------
    # 2. Personality data
    # -----------------------------------------------------------------------
    personality = _read_json(v1_dir / "personality.json")
    if personality:
        agents = personality.get("agents", personality)
        if node_name in agents:
            agent_data = agents[node_name]
            if "role" in agent_data and v2["node"]["role"] == "worker":
                v2["node"]["role"] = agent_data["role"]

    # -----------------------------------------------------------------------
    # 3. Commands / hooks → discover enabled plugins
    # -----------------------------------------------------------------------
    commands = _read_json(v1_dir / "commands.json")
    hooks = _read_json(v1_dir / "hooks.json")

    # If there are war room related configs, enable those plugins
    war_room_dir = v1_dir / "war_room"
    if war_room_dir.is_dir():
        war_room_plugins = ["event-bus", "working-memory", "predictions",
                           "self-model", "hypotheses"]
        for p in war_room_plugins:
            if p not in v2["plugins"]["enabled"]:
                v2["plugins"]["enabled"].append(p)

    # Check for hydra
    if (v1_dir / "hydra.py").exists():
        if "hydra" not in v2["plugins"]["enabled"]:
            v2["plugins"]["enabled"].append("hydra")

    # -----------------------------------------------------------------------
    # 4. Soul files — detect from mesh/souls/
    # -----------------------------------------------------------------------
    soul_dir = v1_dir.parent / "mesh" / "souls"
    if not soul_dir.exists():
        soul_dir = v1_dir / "mesh" / "souls"

    if soul_dir.exists():
        identity = soul_dir / f"IDENTITY.{node_name}.md"
        soul = soul_dir / f"SOUL.{node_name}.md"
        user = soul_dir / f"USER.{node_name}.md"

        if identity.exists():
            v2["soul"]["identity"] = f"mesh/souls/IDENTITY.{node_name}.md"
        if soul.exists():
            v2["soul"]["personality"] = f"mesh/souls/SOUL.{node_name}.md"
        if user.exists():
            v2["soul"]["user_profile"] = f"mesh/souls/USER.{node_name}.md"

    # -----------------------------------------------------------------------
    # 5. Scan other node configs for mesh topology
    # -----------------------------------------------------------------------
    for config_file in sorted(v1_dir.glob("config.*.json")):
        other_name = config_file.stem.replace("config.", "")
        if other_name == node_name or other_name in v2["mesh"]["nodes"]:
            continue

        other_config = _read_json(config_file)
        if other_config:
            ip = other_config.get("ip",
                 other_config.get("host",
                 other_config.get("tailscale_ip", "")))
            port = other_config.get("port", 8765)
            role = other_config.get("role", "worker")

            if ip:
                v2["mesh"]["nodes"][other_name] = {
                    "ip": ip,
                    "port": port,
                    "role": role,
                }

    return v2


# ---------------------------------------------------------------------------
# YAML output
# ---------------------------------------------------------------------------

def to_yaml(config: dict, indent: int = 0) -> str:
    """Convert config dict to YAML string (no PyYAML dependency)."""
    lines = []
    prefix = "  " * indent

    for key, value in config.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(to_yaml(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.append(to_yaml(item, indent + 2))
                else:
                    val_str = _yaml_value(item)
                    lines.append(f"{prefix}  - {val_str}")
        else:
            val_str = _yaml_value(value)
            lines.append(f"{prefix}{key}: {val_str}")

    return "\n".join(lines)


def _yaml_value(value) -> str:
    """Format a scalar value for YAML output."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    # Quote strings that contain special YAML characters
    if any(c in s for c in ":{}[]#&*!|>'\"%@`,$"  ) or s.startswith("- "):
        return f'"{s}"'
    if s.lower() in ("true", "false", "null", "yes", "no", "on", "off"):
        return f'"{s}"'
    return s


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Migrate V1 JSON configs to V2 valhalla.yaml",
    )
    parser.add_argument(
        "v1_dir",
        help="Path to V1 bot/ directory containing JSON config files",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)",
        default=None,
    )
    parser.add_argument(
        "--node", "-n",
        help="Node name (default: auto-detect from hostname)",
        default=None,
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    v1_dir = Path(args.v1_dir).resolve()
    if not v1_dir.is_dir():
        print(f"Error: {v1_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    node_name = args.node or _guess_node_name()
    log.info("Migrating V1 configs from %s for node '%s'", v1_dir, node_name)

    config = parse_v1_configs(v1_dir, node_name)

    header = (
        "# ─────────────────────────────────────────────────────────────\n"
        "# Valhalla Mesh V2 — Unified Node Config\n"
        f"# Migrated from V1 JSON configs ({v1_dir.name}/)\n"
        f"# Node: {node_name}\n"
        "# ─────────────────────────────────────────────────────────────\n"
    )

    yaml_content = header + "\n" + to_yaml(config) + "\n"

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(yaml_content, encoding="utf-8")
        log.info("Written to %s", output_path)
    else:
        print(yaml_content)

    # Summary
    log.info("")
    log.info("Migration summary:")
    log.info("  Node: %s (%s)", config["node"]["name"], config["node"]["role"])
    log.info("  Mesh nodes: %d", len(config["mesh"]["nodes"]))
    log.info("  Plugins: %s", ", ".join(config["plugins"]["enabled"]))
    log.info("  Model: %s", config["models"]["default"])
    if config.get("soul"):
        log.info("  Soul files: %d", len(config["soul"]))


if __name__ == "__main__":
    main()

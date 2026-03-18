#!/usr/bin/env python3
"""
valhalla — CLI for the Valhalla Mesh.

Usage:
    valhalla start                        Start Bifrost + Dashboard
    valhalla start --backend-only         Start Bifrost only (no dashboard)

    valhalla plugin create <name>         Scaffold a new plugin
    valhalla plugin pack [name]           Package a plugin as .tar.gz
    valhalla plugin list                  List installed plugins

    valhalla join <host>                  Connect to a mesh peer
    valhalla status                       Show node status
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent  # cli/ → project root
PLUGINS_DIR = BASE_DIR / "plugins"
DASHBOARD_DIR = BASE_DIR / "dashboard"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_start(args):
    """Start Bifrost and optionally the Dashboard."""
    bifrost = BASE_DIR / "bifrost.py"
    if not bifrost.exists():
        print(f"❌ bifrost.py not found at {bifrost}")
        sys.exit(1)

    port = args.port or 8765
    procs = []

    # Start backend
    print(f"⚡ Starting Bifrost on port {port}...")
    backend = subprocess.Popen(
        [sys.executable, str(bifrost), "--port", str(port)],
        cwd=str(BASE_DIR),
    )
    procs.append(backend)

    # Start dashboard unless --backend-only
    if not args.backend_only and DASHBOARD_DIR.exists():
        print("🖥️  Starting Dashboard...")
        dashboard = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(DASHBOARD_DIR),
            shell=True,
        )
        procs.append(dashboard)

    try:
        print("✅ Valhalla is running. Press Ctrl+C to stop.")
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        for p in procs:
            p.terminate()


def cmd_plugin_create(args):
    """Scaffold a new plugin directory."""
    name = args.name
    plugin_dir = PLUGINS_DIR / name

    if plugin_dir.exists():
        print(f"❌ Plugin '{name}' already exists at {plugin_dir}")
        sys.exit(1)

    plugin_dir.mkdir(parents=True)

    # plugin.yaml
    yaml_content = f"""name: {name}
version: 1.0.0
description: TODO — describe what {name} does
author: your-name
license: MIT
category: utility
rarity: common

routes:
  - method: GET
    path: /api/v1/{name}/status

events: []

config_keys: []
"""
    (plugin_dir / "plugin.yaml").write_text(yaml_content, encoding="utf-8")

    # handler.py
    handler_content = f'''"""
{name} plugin — TODO: describe what this plugin does.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter

log = logging.getLogger("valhalla.{name}")


def register_routes(app, config: dict) -> None:
    """Called by plugin_loader at startup."""
    router = APIRouter(tags=["{name}"])

    @router.get("/api/v1/{name}/status")
    async def get_status():
        return {{"ok": True, "plugin": "{name}"}}

    app.include_router(router)
    log.info("[{name}] Plugin loaded.")


def on_event(event_name: str, payload: dict, config: dict) -> None:
    """Called when a subscribed event fires."""
    pass


def health_check() -> bool:
    """Watchdog calls this. Return True if healthy."""
    return True
'''
    (plugin_dir / "handler.py").write_text(handler_content, encoding="utf-8")

    print(f"✅ Created plugin: {plugin_dir}")
    print(f"   📄 {plugin_dir / 'plugin.yaml'}")
    print(f"   🐍 {plugin_dir / 'handler.py'}")
    print(f"\nNext: edit handler.py, then run 'valhalla start' to test.")


def cmd_plugin_pack(args):
    """Package a plugin as a .tar.gz archive."""
    name = args.name
    plugin_dir = PLUGINS_DIR / name

    if not plugin_dir.exists():
        print(f"❌ Plugin '{name}' not found at {plugin_dir}")
        sys.exit(1)

    # Read version from plugin.yaml
    yaml_path = plugin_dir / "plugin.yaml"
    version = "1.0.0"
    if yaml_path.exists():
        for line in yaml_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version:"):
                version = line.split(":", 1)[1].strip()
                break

    archive_name = f"{name}-{version}.tar.gz"
    archive_path = BASE_DIR / archive_name

    with tarfile.open(str(archive_path), "w:gz") as tar:
        tar.add(str(plugin_dir), arcname=name)

    size_kb = archive_path.stat().st_size / 1024
    print(f"📦 Packed: {archive_name} ({size_kb:.1f} KB)")
    print(f"   Install on another node: valhalla plugin install ./{archive_name}")


def cmd_plugin_list(args):
    """List installed plugins."""
    if not PLUGINS_DIR.exists():
        print("No plugins directory found.")
        return

    print("📦 Installed Plugins:")
    print(f"{'Name':<25} {'Version':<10} {'Category':<15} {'Rarity'}")
    print("─" * 65)

    for d in sorted(PLUGINS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("__"):
            continue
        yaml_path = d / "plugin.yaml"
        if not yaml_path.exists():
            continue

        # Quick parse (no yaml dependency needed)
        info = {"version": "?", "category": "?", "rarity": "?"}
        for line in yaml_path.read_text(encoding="utf-8").splitlines():
            for key in info:
                if line.strip().startswith(f"{key}:"):
                    info[key] = line.split(":", 1)[1].strip()

        print(f"  {d.name:<23} {info['version']:<10} {info['category']:<15} {info['rarity']}")


def cmd_join(args):
    """Connect to a mesh peer."""
    host = args.host
    if ":" not in host:
        host += ":8765"

    # Parse name@host:port format
    if "@" in host:
        peer_name, host = host.split("@", 1)
    else:
        peer_name = host.split(":")[0]

    print(f"🔗 Connecting to {host}...")

    try:
        url = f"http://{host}/api/v1/status"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            print(f"✅ Connected to {data.get('node', 'unknown')} "
                  f"(role: {data.get('role', '?')}, "
                  f"model: {data.get('model', '?')})")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)


def cmd_status(args):
    """Show local node status."""
    port = args.port or 8765
    try:
        url = f"http://127.0.0.1:{port}/api/v1/status"
        with urllib.request.urlopen(url, timeout=3) as r:
            data = json.loads(r.read())
            print(f"⚡ Node: {data.get('node', '?')}")
            print(f"   Role: {data.get('role', '?')}")
            print(f"   Model: {data.get('model', '?')}")
            print(f"   Uptime: {data.get('uptime', '?')}s")
    except Exception:
        print("❌ Bifrost is not running (or not on this port)")
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="valhalla",
        description="Valhalla Mesh CLI — manage your AI agents",
    )
    sub = parser.add_subparsers(dest="command")

    # start
    p_start = sub.add_parser("start", help="Start Bifrost + Dashboard")
    p_start.add_argument("--port", type=int, default=None)
    p_start.add_argument("--backend-only", action="store_true")

    # plugin
    p_plugin = sub.add_parser("plugin", help="Manage plugins")
    plugin_sub = p_plugin.add_subparsers(dest="plugin_command")

    p_create = plugin_sub.add_parser("create", help="Scaffold a new plugin")
    p_create.add_argument("name")

    p_pack = plugin_sub.add_parser("pack", help="Package a plugin")
    p_pack.add_argument("name")

    p_list = plugin_sub.add_parser("list", help="List installed plugins")

    # join
    p_join = sub.add_parser("join", help="Connect to a mesh peer")
    p_join.add_argument("host", help="e.g. odin@192.168.1.100:8765")

    # status
    p_status = sub.add_parser("status", help="Show node status")
    p_status.add_argument("--port", type=int, default=None)

    args = parser.parse_args()

    if args.command == "start":
        cmd_start(args)
    elif args.command == "plugin":
        if args.plugin_command == "create":
            cmd_plugin_create(args)
        elif args.plugin_command == "pack":
            cmd_plugin_pack(args)
        elif args.plugin_command == "list":
            cmd_plugin_list(args)
        else:
            p_plugin.print_help()
    elif args.command == "join":
        cmd_join(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

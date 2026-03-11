"""
brain-installer/process_manager.py — Keep inference servers running.

Generates launchd plists (Mac) or systemd units (Linux) for auto-start.
"""
from __future__ import annotations

import logging
import os
import platform
import signal
import subprocess
from pathlib import Path

log = logging.getLogger("valhalla.brain-installer.process")

_PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
_SYSTEMD_DIR = Path.home() / ".config" / "systemd" / "user"
_SERVICE_NAME = "ai.valhalla.inference"


def _plist_content(cmd: list, label: str = _SERVICE_NAME) -> str:
    """Generate a launchd plist for auto-start on macOS."""
    args = "\n".join(f"        <string>{a}</string>" for a in cmd)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
{args}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/valhalla-inference.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/valhalla-inference.err</string>
</dict>
</plist>"""


def _systemd_content(cmd: list) -> str:
    """Generate a systemd user unit for auto-start on Linux."""
    exec_start = " ".join(cmd)
    return f"""[Unit]
Description=Valhalla Inference Server
After=network.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""


def install_service(cmd: list) -> dict:
    """Install auto-start service for the inference server."""
    system = platform.system()

    try:
        if system == "Darwin":
            _PLIST_DIR.mkdir(parents=True, exist_ok=True)
            plist_path = _PLIST_DIR / f"{_SERVICE_NAME}.plist"
            plist_path.write_text(_plist_content(cmd), encoding="utf-8")
            log.info("[process] Installed launchd plist: %s", plist_path)
            return {"ok": True, "path": str(plist_path), "type": "launchd"}

        elif system == "Linux":
            _SYSTEMD_DIR.mkdir(parents=True, exist_ok=True)
            unit_path = _SYSTEMD_DIR / f"{_SERVICE_NAME}.service"
            unit_path.write_text(_systemd_content(cmd), encoding="utf-8")
            subprocess.run(["systemctl", "--user", "daemon-reload"],
                         capture_output=True, timeout=10)
            log.info("[process] Installed systemd unit: %s", unit_path)
            return {"ok": True, "path": str(unit_path), "type": "systemd"}

        return {"ok": False, "error": f"Unsupported OS: {system}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def start_service() -> dict:
    """Start the inference service."""
    system = platform.system()
    try:
        if system == "Darwin":
            plist = _PLIST_DIR / f"{_SERVICE_NAME}.plist"
            if not plist.exists():
                return {"ok": False, "error": "Service not installed"}
            subprocess.run(["launchctl", "load", str(plist)],
                         capture_output=True, timeout=10)
            return {"ok": True, "message": "Service started (launchd)"}

        elif system == "Linux":
            subprocess.run(
                ["systemctl", "--user", "start", _SERVICE_NAME],
                capture_output=True, timeout=10,
            )
            return {"ok": True, "message": "Service started (systemd)"}

        return {"ok": False, "error": f"Unsupported OS: {system}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop_service() -> dict:
    """Stop the inference service."""
    system = platform.system()
    try:
        if system == "Darwin":
            plist = _PLIST_DIR / f"{_SERVICE_NAME}.plist"
            if plist.exists():
                subprocess.run(["launchctl", "unload", str(plist)],
                             capture_output=True, timeout=10)
            return {"ok": True, "message": "Service stopped"}

        elif system == "Linux":
            subprocess.run(
                ["systemctl", "--user", "stop", _SERVICE_NAME],
                capture_output=True, timeout=10,
            )
            return {"ok": True, "message": "Service stopped"}

        return {"ok": False, "error": f"Unsupported OS: {system}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def is_running() -> bool:
    """Check if inference service is running."""
    system = platform.system()
    try:
        if system == "Darwin":
            r = subprocess.run(
                ["launchctl", "list", _SERVICE_NAME],
                capture_output=True, text=True, timeout=5,
            )
            return r.returncode == 0

        elif system == "Linux":
            r = subprocess.run(
                ["systemctl", "--user", "is-active", _SERVICE_NAME],
                capture_output=True, text=True, timeout=5,
            )
            return "active" in r.stdout
    except Exception:
        pass
    return False

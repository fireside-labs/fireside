"""
installers/omlx.py — Apple Silicon (MLX) model installer.

For Mac M1-M4: uses mlx-lm library for native Metal inference.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("valhalla.brain-installer.omlx")

DEFAULT_PORT = 8080


def is_available() -> bool:
    """Check if this machine supports oMLX (Apple Silicon)."""
    try:
        r = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True, timeout=5,
        )
        return "Apple" in r.stdout
    except Exception:
        return False


def is_installed() -> bool:
    """Check if mlx-lm is installed."""
    try:
        r = subprocess.run(
            ["python3", "-m", "mlx_lm", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 or "mlx_lm" in r.stdout + r.stderr
    except Exception:
        return False


def install_runtime() -> dict:
    """Install mlx-lm if needed."""
    if is_installed():
        return {"ok": True, "message": "mlx-lm already installed"}

    # Check Python 3.10+
    try:
        r = subprocess.run(
            ["python3", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        version = r.stdout.strip().split()[-1]
        major, minor = int(version.split(".")[0]), int(version.split(".")[1])
        if major < 3 or (major == 3 and minor < 10):
            return {"ok": False, "error": f"Python 3.10+ required, found {version}"}
    except Exception as e:
        return {"ok": False, "error": f"Python check failed: {e}"}

    # Install mlx-lm
    try:
        r = subprocess.run(
            ["pip3", "install", "mlx-lm"],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            return {"ok": False, "error": f"pip install failed: {r.stderr[:200]}"}
        return {"ok": True, "message": "mlx-lm installed successfully"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def download_model(omlx_id: str) -> dict:
    """Download a model via mlx-lm (HuggingFace cache)."""
    try:
        # mlx_lm.generate with a tiny prompt triggers download
        r = subprocess.run(
            ["python3", "-m", "mlx_lm.generate",
             "--model", omlx_id,
             "--prompt", "Hi",
             "--max-tokens", "1"],
            capture_output=True, text=True, timeout=1800,  # 30 min for large models
        )
        if r.returncode == 0:
            return {"ok": True, "message": f"Model {omlx_id} ready"}
        return {"ok": False, "error": r.stderr[:300]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def start_server(omlx_id: str, port: int = DEFAULT_PORT) -> dict:
    """Start oMLX server."""
    try:
        cmd = [
            "python3", "-m", "mlx_lm.server",
            "--model", omlx_id,
            "--port", str(port),
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        log.info("[omlx] Started server PID=%d on port %d", proc.pid, port)
        return {"ok": True, "pid": proc.pid, "port": port}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_install_info() -> dict:
    """Return oMLX installer info."""
    return {
        "runtime": "omlx",
        "name": "MLX (Apple Silicon)",
        "available": is_available(),
        "installed": is_installed(),
        "platform": "macOS (Apple Silicon)",
    }

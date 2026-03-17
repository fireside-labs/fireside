"""
installers/llamacpp.py — NVIDIA GPU model installer (llama.cpp server).

Downloads pre-built llama-server binary + GGUF model, starts with optimal settings.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path

log = logging.getLogger("valhalla.brain-installer.llamacpp")

DEFAULT_PORT = 8080
LLAMA_CPP_RELEASE = "b5460"  # Pin to known-good release
MODELS_DIR = Path.home() / ".valhalla" / "models"


def is_available() -> bool:
    """Check if NVIDIA GPU is present."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0 and len(r.stdout.strip()) > 0
    except Exception:
        return False


def is_installed() -> bool:
    """Check if llama-server binary exists."""
    system = platform.system().lower()
    exe = "llama-server.exe" if system == "windows" else "llama-server"
    return shutil.which(exe) is not None or \
           (MODELS_DIR.parent / "bin" / exe).exists()


def _get_binary_url() -> str:
    """Get llama-server download URL for this platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    base = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_CPP_RELEASE}"

    if system == "windows":
        # Windows CUDA binary (CUDA 12.4, x64)
        return f"{base}/llama-{LLAMA_CPP_RELEASE}-bin-win-cuda-cu12.4-x64.zip"
    elif system == "darwin":
        return f"{base}/llama-{LLAMA_CPP_RELEASE}-bin-macos-arm64.zip"
    elif system == "linux" and "x86" in machine:
        return f"{base}/llama-{LLAMA_CPP_RELEASE}-bin-ubuntu-x64.zip"
    return f"{base}/llama-{LLAMA_CPP_RELEASE}-bin-ubuntu-x64.zip"


def install_runtime() -> dict:
    """Download llama-server binary."""
    if is_installed():
        return {"ok": True, "message": "llama-server already installed"}

    bin_dir = MODELS_DIR.parent / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    url = _get_binary_url()
    zip_path = bin_dir / "llama-server.zip"

    try:
        log.info("[llamacpp] Downloading llama-server from %s", url)
        urllib.request.urlretrieve(url, str(zip_path))

        # Extract
        import zipfile
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            zf.extractall(str(bin_dir))

        # Find and make executable (not needed on Windows)
        system = platform.system().lower()
        exe_name = "llama-server.exe" if system == "windows" else "llama-server"
        for f in bin_dir.rglob(exe_name):
            if system != "windows":
                os.chmod(str(f), 0o755)

        zip_path.unlink(missing_ok=True)
        return {"ok": True, "message": "llama-server installed"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def download_model(model_id: str, gguf_url: str) -> dict:
    """Download a GGUF model file."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    filename = gguf_url.rsplit("/", 1)[-1]
    model_path = MODELS_DIR / filename

    if model_path.exists():
        return {"ok": True, "path": str(model_path), "message": "Already downloaded"}

    try:
        log.info("[llamacpp] Downloading %s", filename)
        urllib.request.urlretrieve(gguf_url, str(model_path))
        return {"ok": True, "path": str(model_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def start_server(model_path: str, port: int = DEFAULT_PORT,
                 context: int = 32768, gpu_layers: int = 99) -> dict:
    """Start llama-server with optimal settings."""
    system = platform.system().lower()
    exe = "llama-server.exe" if system == "windows" else "llama-server"
    binary = shutil.which(exe)
    if not binary:
        alt = MODELS_DIR.parent / "bin" / exe
        if alt.exists():
            binary = str(alt)
        else:
            return {"ok": False, "error": f"{exe} binary not found"}

    try:
        cmd = [
            binary,
            "-m", model_path,
            "--port", str(port),
            "-c", str(context),
            "--cache-type-k", "q8_0",
            "--cache-type-v", "q8_0",
            "-ngl", str(gpu_layers),
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        log.info("[llamacpp] Started server PID=%d on port %d", proc.pid, port)
        return {"ok": True, "pid": proc.pid, "port": port}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_install_info() -> dict:
    """Return llama-server installer info."""
    return {
        "runtime": "llamacpp",
        "name": "llama.cpp (NVIDIA GPU)",
        "available": is_available(),
        "installed": is_installed(),
        "platform": "Windows/Linux/Mac (NVIDIA CUDA)",
    }

"""
bot/brain_manager.py — llama-server lifecycle manager.

Fireside owns the llama-server process. When Bifrost starts:
  1. Reads the active model from onboarding.json / valhalla.yaml
  2. Starts llama-server with ALL layers on GPU (-ngl 99)
  3. Keeps it running — no idle offloading, model stays hot in VRAM

Model is kept resident in VRAM at all times:
  -ngl 99         → load all layers to GPU, never offload to CPU
  --keep -1       → keep ALL tokens in KV cache (no context eviction)
  --no-mmap       → load model fully into memory (faster cold inference)
  -c 8192         → context window (tunable via config)

Brain switching:
  switch_model(path) → kills running process → starts new one
"""
from __future__ import annotations

import logging
import os
import shutil
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.brain_manager")

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_proc: Optional[subprocess.Popen] = None
_proc_lock = threading.Lock()
_current_model_path: Optional[Path] = None
_start_time: float = 0.0

_status: dict = {
    "running": False,
    "model": None,
    "model_path": None,
    "pid": None,
    "port": 8080,
    "started_at": None,
    "error": None,
    "gpu_layers": 99,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_status() -> dict:
    """Return current brain server status."""
    global _proc
    with _proc_lock:
        if _proc is not None:
            # Check if still alive
            if _proc.poll() is not None:
                # Process died
                _status["running"] = False
                _status["pid"] = None
                _status["error"] = f"llama-server exited (code {_proc.returncode})"
                _proc = None
            else:
                _status["running"] = True
                _status["pid"] = _proc.pid
        return dict(_status)


def start(model_path: Path, config: dict = None) -> bool:
    """Start llama-server with the given GGUF model.

    All layers loaded to GPU (-ngl 99). Model stays hot in VRAM.
    Returns True if started successfully.
    """
    global _proc, _current_model_path, _start_time

    config = config or {}
    port = config.get("llama", {}).get("port", 8080)
    context = config.get("llama", {}).get("context_size", 8192)
    gpu_layers = config.get("llama", {}).get("gpu_layers", 99)
    threads = config.get("llama", {}).get("threads", os.cpu_count() or 8)

    if not model_path.exists():
        _status["error"] = f"Model not found: {model_path}"
        log.error("[brain] Model not found: %s", model_path)
        return False

    # Find llama-server binary
    binary = _find_binary()
    if not binary:
        _status["error"] = "llama-server not found in PATH. Install llama.cpp first."
        log.error("[brain] llama-server not found in PATH")
        return False

    with _proc_lock:
        # Kill any existing process
        _stop_locked()

        cmd = [
            binary,
            "--model", str(model_path),
            "--port", str(port),
            "--host", "127.0.0.1",
            "--ctx-size", str(context),
            "--n-gpu-layers", str(gpu_layers),  # ALL layers on GPU
            "--keep", "-1",                      # Keep all tokens in KV cache
            "--threads", str(threads),
            "--no-mmap",                         # Load fully into memory
            "--flash-attn",                    # Flash attention (requires compatible GPU)
        ]

        # Disable thinking for small models (< 3B) — they waste tokens on garbage
        model_name = model_path.name.lower()
        if re.search(r'[-_\.](0\.5b|0\.6b|1b|1\.5b|2b)[-_\.]', model_name):
            cmd.extend(["--reasoning-budget", "0"])
            log.info("[brain] Small model detected, disabling thinking mode")

        # Auto-detect chat template from model name
        if "qwen" in model_name:
            cmd.extend(["--chat-template", "chatml"])
            log.info("[brain] Qwen model detected — using chatml template")
        elif "llama" in model_name or "meta" in model_name:
            cmd.extend(["--chat-template", "llama3"])
            log.info("[brain] Llama model detected — using llama3 template")
        elif "mistral" in model_name:
            cmd.extend(["--chat-template", "mistral-v7"])
            log.info("[brain] Mistral model detected — using mistral-v7 template")
        elif "gemma" in model_name:
            cmd.extend(["--chat-template", "gemma"])
            log.info("[brain] Gemma model detected — using gemma template")
        elif "phi" in model_name:
            cmd.extend(["--chat-template", "chatml"])
            log.info("[brain] Phi model detected — using chatml template")
        # else: let llama-server auto-detect from GGUF metadata

        log.info("[brain] Starting llama-server: %s", " ".join(cmd))

        try:
            # Start process, redirect output to log
            kwargs = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            # Hide console window on Windows
            import sys
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            _proc = subprocess.Popen(cmd, **kwargs)
            _current_model_path = model_path
            _start_time = time.time()

            _status.update({
                "running": True,
                "model": model_path.stem,
                "model_path": str(model_path),
                "pid": _proc.pid,
                "port": port,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": None,
                "gpu_layers": gpu_layers,
            })

            # Background thread to forward llama-server logs
            threading.Thread(
                target=_tail_logs, args=(_proc,),
                daemon=True, name="brain-logs"
            ).start()

            # Wait up to 8s for server to be ready
            if _wait_ready(port, timeout=8):
                log.info("[brain] ✓ llama-server ready on port %d (pid=%d)", port, _proc.pid)
                return True
            else:
                log.warning("[brain] llama-server started but not responding yet on :%d — continuing", port)
                return True  # Still return True, it may still be loading

        except FileNotFoundError:
            _status["error"] = f"Binary not found: {binary}"
            log.error("[brain] Binary not found: %s", binary)
            return False
        except Exception as e:
            _status["error"] = str(e)
            log.error("[brain] Failed to start: %s", e)
            return False


def stop() -> None:
    """Stop the running llama-server process."""
    with _proc_lock:
        _stop_locked()


def switch_model(model_path: Path, config: dict = None) -> bool:
    """Switch to a different model. Kills old process, starts new one."""
    log.info("[brain] Switching model to: %s", model_path)
    return start(model_path, config)


def auto_start(config: dict, base_dir: Path) -> bool:
    """Called at Bifrost startup. Finds configured model and starts it.

    Model resolution order:
      1. ~/.fireside/onboarding.json → brain field
      2. valhalla.yaml → node.model_path
      3. ~/.fireside/models/ → newest .gguf file
    """
    model_path = _resolve_model(config, base_dir)

    if model_path is None:
        log.info("[brain] No model configured — skipping auto-start. "
                 "Use the Brain Lab to download and activate a model.")
        _status["error"] = "No model configured. Download one from the Brain Lab."
        return False

    log.info("[brain] Auto-starting with model: %s", model_path)
    return start(model_path, config)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _stop_locked() -> None:
    """Stop process. Must be called with _proc_lock held."""
    global _proc
    if _proc is not None and _proc.poll() is None:
        log.info("[brain] Stopping llama-server (pid=%d)", _proc.pid)
        try:
            _proc.terminate()
            try:
                _proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _proc.kill()
                _proc.wait()
        except Exception as e:
            log.warning("[brain] Error stopping process: %s", e)
        _proc = None
        _status.update({"running": False, "pid": None})


def _find_binary() -> Optional[str]:
    """Find llama-server binary in PATH or common install locations."""
    # Try PATH first
    binary = shutil.which("llama-server")
    if binary:
        return binary
    binary = shutil.which("llama-server.exe")
    if binary:
        return binary

    # Fireside/OpenClaw installer locations (most likely for end users)
    home = Path.home()
    installer_paths = [
        home / ".openclaw" / "llama-server" / "llama-server.exe",
        home / ".openclaw" / "llama-server" / "llama-server",
        home / ".fireside" / "bin" / "llama-server.exe",
        home / ".fireside" / "bin" / "llama-server",
    ]
    for p in installer_paths:
        if p.exists():
            return str(p)

    # Common manual install locations
    common = [
        home / "llama.cpp" / "llama-server.exe",
        home / "llama.cpp" / "build" / "bin" / "llama-server.exe",
        Path("C:/") / "llama.cpp" / "llama-server.exe",
        Path("C:/") / "Program Files" / "llama.cpp" / "llama-server.exe",
        Path("C:/") / "tools" / "llama-server.exe",
    ]
    for p in common:
        if p.exists():
            return str(p)

    return None


def _resolve_model(config: dict, base_dir: Path) -> Optional[Path]:
    """Find the configured GGUF model file."""
    import json

    models_dir = Path.home() / ".fireside" / "models"

    # 1. Check onboarding.json for selected model filename
    try:
        ob_path = Path.home() / ".fireside" / "onboarding.json"
        if ob_path.exists():
            ob = json.loads(ob_path.read_text(encoding="utf-8"))
            model_file = ob.get("model_file") or ob.get("brain_path")
            if model_file:
                p = Path(model_file)
                if not p.is_absolute():
                    p = models_dir / model_file
                if p.exists():
                    return p
    except Exception:
        pass

    # 2. valhalla.yaml → node.model_path
    model_path_cfg = config.get("node", {}).get("model_path")
    if model_path_cfg:
        p = Path(model_path_cfg)
        if p.exists():
            return p

    # 3. Scan ~/.fireside/models/ for any .gguf — use the newest
    if models_dir.exists():
        ggufs = sorted(models_dir.glob("*.gguf"), key=lambda f: f.stat().st_mtime, reverse=True)
        if ggufs:
            log.info("[brain] Found GGUF in models dir: %s", ggufs[0])
            return ggufs[0]

    # 4. Scan base_dir/models/
    local_models = base_dir / "models"
    if local_models.exists():
        ggufs = sorted(local_models.glob("*.gguf"), key=lambda f: f.stat().st_mtime, reverse=True)
        if ggufs:
            return ggufs[0]

    return None


def _wait_ready(port: int, timeout: float = 8.0) -> bool:
    """Poll until llama-server responds on the given port."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            url = f"http://127.0.0.1:{port}/health"
            with urllib.request.urlopen(url, timeout=1):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def _tail_logs(proc: subprocess.Popen) -> None:
    """Forward llama-server stdout to Valhalla log."""
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log.debug("[llama-server] %s", line)
    except Exception:
        pass

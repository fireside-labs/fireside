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
        # Detect externally started llama-server (e.g. manual terminal launch)
        if not _status["running"]:
            port = _status.get("port", 8080)
            if _is_port_open(port):
                _status["running"] = True
                _status["error"] = None
                if not _status.get("model"):
                    _status["model"] = "(external_or_loading)"
                # Critical fix: DO NOT make synchronous HTTP requests here to query the model name.
                # When a large model (like 35B) is loading into VRAM, llama-server accepts TCP connections 
                # but hangs on HTTP requests. Doing this inside get_status() while the dashboard
                # is rapidly polling `/api/v1/brains/status` exhausts all FastAPI worker threads and
                # completely deadlocks Bifrost.
        return dict(_status)


def start(model_path: Path, config: dict = None) -> bool:
    """Start llama-server with the given GGUF model.

    Uses graceful degradation — if the first launch fails, retries with
    progressively safer flags so it works on any hardware:
      Attempt 1: Full GPU + flash-attn + no-mmap  (fastest, needs modern GPU)
      Attempt 2: Full GPU, no flash-attn           (works on older CUDA GPUs)
      Attempt 3: Full GPU, no flash-attn, no no-mmap (less RAM needed)
      Attempt 4: Half GPU layers                    (fallback for low VRAM)
      Attempt 5: CPU only                           (absolute last resort)
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

    model_name = model_path.name.lower()

    # Disable thinking for small models (< 3B) — they waste tokens on garbage
    extra_flags = []
    if re.search(r'[-_\.](0\.5b|0\.6b|1b|1\.5b|2b)[-_\.]', model_name):
        extra_flags.extend(["--reasoning-budget", "0"])
        log.info("[brain] Small model detected, disabling thinking mode")

    # --jinja is REQUIRED for tool/function calling — always include it.
    # Do NOT add --chat-template when --jinja is active (they conflict).
    extra_flags.append("--jinja")
    log.info("[brain] --jinja active — using GGUF-embedded template (supports tool calling)")

    # ── Degradation ladder: try aggressive → safe ──
    attempts = [
        {
            "label": "Full GPU + flash-attn",
            "ngl": gpu_layers,
            "flags": ["--no-mmap", "--flash-attn"],
        },
        {
            "label": "Full GPU (no flash-attn)",
            "ngl": gpu_layers,
            "flags": ["--no-mmap"],
        },
        {
            "label": "Full GPU (mmap enabled)",
            "ngl": gpu_layers,
            "flags": [],
        },
        {
            "label": "Half GPU layers",
            "ngl": max(1, gpu_layers // 2),
            "flags": [],
        },
        {
            "label": "CPU only (last resort)",
            "ngl": 0,
            "flags": [],
        },
    ]

    for i, attempt in enumerate(attempts):
        with _proc_lock:
            _stop_locked()

            cmd = [
                binary,
                "--model", str(model_path),
                "--port", str(port),
                "--host", "127.0.0.1",
                "--ctx-size", str(context),
                "--n-gpu-layers", str(attempt["ngl"]),
                "--keep", "-1",
                "--threads", str(threads),
            ] + attempt["flags"] + extra_flags

            log.info("[brain] Attempt %d/%d: %s — %s",
                     i + 1, len(attempts), attempt["label"], " ".join(cmd))

            try:
                kwargs = dict(
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
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
                    "gpu_layers": attempt["ngl"],
                })

                # Background thread to forward llama-server logs
                threading.Thread(
                    target=_tail_logs, args=(_proc,),
                    daemon=True, name="brain-logs"
                ).start()

                # Wait for the server to become ready.
                # Larger models need more time — scale timeout with model size.
                model_size_mb = model_path.stat().st_size / (1024 * 1024)
                timeout = max(15, min(120, model_size_mb / 200))  # 15s–120s
                log.info("[brain] Waiting up to %.0fs for server (model=%.0f MB)...",
                         timeout, model_size_mb)

                if _wait_ready(port, timeout=timeout):
                    log.info("[brain] ✓ llama-server ready on port %d (pid=%d, %s)",
                             port, _proc.pid, attempt["label"])
                    return True

                # Check if process crashed during startup
                if _proc.poll() is not None:
                    exit_code = _proc.returncode
                    log.warning("[brain] llama-server crashed (exit=%d) on attempt %d (%s)",
                                exit_code, i + 1, attempt["label"])
                    _proc = None
                    _status["running"] = False
                    _status["pid"] = None

                    if i < len(attempts) - 1:
                        log.info("[brain] Retrying with safer config...")
                        time.sleep(1)  # Brief pause before retry
                        continue
                    else:
                        _status["error"] = (
                            f"All {len(attempts)} startup attempts failed. "
                            f"Last exit code: {exit_code}. "
                            f"Check GPU drivers or try a smaller model."
                        )
                        return False
                else:
                    # Process is alive but not responding yet — give it more time
                    log.warning("[brain] llama-server started but slow on :%d — continuing", port)
                    return True

            except FileNotFoundError:
                _status["error"] = f"Binary not found: {binary}"
                log.error("[brain] Binary not found: %s", binary)
                return False
            except Exception as e:
                _status["error"] = str(e)
                log.error("[brain] Failed to start (attempt %d): %s", i + 1, e)
                if i < len(attempts) - 1:
                    continue
                return False

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

    # Fireside installer locations (most likely for end users)
    home = Path.home()
    installer_paths = [
        home / ".fireside" / "bin" / "llama-server.exe",
        home / ".fireside" / "bin" / "llama-server",
        # Legacy fallback — existing installs may have it here
        home / ".openclaw" / "llama-server" / "llama-server.exe",
        home / ".openclaw" / "llama-server" / "llama-server",
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
    """Find the configured GGUF model file.

    Resolution order:
      1. onboarding.json → explicit model_file path
      2. valhalla.yaml → node.model_path
      3. Scan known model directories for .gguf files (prefer largest = most capable)
    """
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

    # 3. Scan known model directories — prefer largest file (= most capable)
    scan_dirs = [
        models_dir,                                  # ~/.fireside/models/
        base_dir / "models",                         # project-local models/
    ]

    all_ggufs: list[Path] = []
    for d in scan_dirs:
        if d.exists():
            all_ggufs.extend(d.glob("*.gguf"))

    if all_ggufs:
        # Sort by file size descending — largest model is usually the most capable
        best = sorted(all_ggufs, key=lambda f: f.stat().st_size, reverse=True)[0]
        log.info("[brain] Auto-selected model: %s (%.1f GB, from %s)",
                 best.name, best.stat().st_size / (1024**3), best.parent)
        return best

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


def _is_port_open(port: int) -> bool:
    """Quick check if something is listening on a port."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def _query_model_name(port: int) -> Optional[str]:
    """Query running llama-server for its loaded model name."""
    import urllib.request
    import json as _json
    try:
        url = f"http://127.0.0.1:{port}/v1/models"
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = _json.loads(resp.read())
            models = data.get("data", [])
            if models:
                model_id = models[0].get("id", "")
                # Clean up the model ID (often a file path)
                if "/" in model_id or "\\" in model_id:
                    model_id = Path(model_id).stem
                return model_id or None
    except Exception:
        pass
    return None


def _tail_logs(proc: subprocess.Popen) -> None:
    """Forward llama-server stdout to Valhalla log."""
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log.debug("[llama-server] %s", line)
    except Exception:
        pass

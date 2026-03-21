"""
bifrost.py — Valhalla Mesh V2 Entry Point.

Plugin-based Bifrost server built on FastAPI.
Replaces the V1 http.server monolith.

Usage:
    python bifrost.py                    # default: reads valhalla.yaml
    python bifrost.py --config alt.yaml  # custom config path
"""
from __future__ import annotations

import argparse
import logging
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-5s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("valhalla.bifrost")


def create_app(config_path: str | None = None) -> FastAPI:
    """Build and return the FastAPI application.

    This factory function:
      1. Loads config via config_loader
      2. Creates the FastAPI app
      3. Loads plugins via plugin_loader
      4. Mounts the API v1 router
    """
    from config_loader import get_config
    from plugin_loader import load_plugins
    from api.v1 import init_api

    # 1. Config
    config = get_config(config_path)
    node_name = config.get("node", {}).get("name", "unknown")
    node_role = config.get("node", {}).get("role", "unknown")

    log.info("═══════════════════════════════════════════════")
    log.info("  Valhalla Bifrost V2")
    log.info("  Node: %s (%s)", node_name, node_role)
    log.info("═══════════════════════════════════════════════")

    # 2. mDNS / Zeroconf — broadcast on local network so mobile can find us
    zc_instance = None
    zc_info = None
    try:
        from zeroconf import Zeroconf, ServiceInfo
        local_ip = _get_local_ip()
        svc_port = config.get("node", {}).get("port", 8765)
        zc_info = ServiceInfo(
            "_fireside._tcp.local.",
            f"{node_name}._fireside._tcp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=svc_port,
            properties={
                "node": node_name,
                "role": node_role,
                "version": "2.0.0",
            },
        )
        zc_instance = Zeroconf()
        log.info("mDNS: will broadcast as %s on %s:%d", node_name, local_ip, svc_port)
    except ImportError:
        log.info("mDNS: zeroconf not installed — skipping auto-discovery (pip install zeroconf)")
    except Exception as e:
        log.warning("mDNS: failed to prepare: %s", e)

    # Lifecycle: register/unregister mDNS on startup/shutdown
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # ── Brain: auto-start llama-server ──────────────────────────────
        try:
            from bot.brain_manager import auto_start as brain_auto_start
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, brain_auto_start, config, Path("."))
        except Exception as e:
            log.warning("Brain auto-start failed (non-fatal): %s", e)

        # ── mDNS ────────────────────────────────────────────────────────
        if zc_instance and zc_info:
            zc_instance.register_service(zc_info)
            log.info("mDNS: broadcasting _fireside._tcp.local.")
        yield
        if zc_instance and zc_info:
            zc_instance.unregister_service(zc_info)
            zc_instance.close()
            log.info("mDNS: stopped broadcasting")

        # ── Brain: clean shutdown ────────────────────────────────────────
        try:
            from bot.brain_manager import stop as brain_stop
            brain_stop()
            log.info("Brain: llama-server stopped")
        except Exception as e:
            log.warning("Brain stop failed: %s", e)


    # 3. FastAPI app
    app = FastAPI(
        title=f"Valhalla Bifrost — {node_name}",
        description="Valhalla Mesh V2 API",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS — allow all origins. Bifrost binds to 127.0.0.1 only,
    # so only local processes can reach it. No security risk.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # credentials not needed for local
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3a. Rate limiter middleware (Heimdall Sprint 2)
    try:
        from middleware.rate_limiter import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware, config=config)
        log.info("Rate limiter enabled")
    except Exception as e:
        log.warning("Rate limiter not available: %s", e)

    # 3b. Store config on app for auth dependency access
    app.state.config = config

    # 4. Health endpoint (always available, no plugin needed)
    @app.get("/health")
    async def health():
        return {"status": "ok", "node": node_name, "version": "2.0.0"}

    # 5. Load plugins (through sandbox)
    plugins = load_plugins(app, config)
    log.info("Plugins loaded: %d", len(plugins))

    # 6. Mount API v1
    api_router = init_api(config)
    app.include_router(api_router)
    log.info("API v1 mounted at /api/v1/")

    return app


def _get_local_ip() -> str:
    """Get the machine's local network IP (not 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _clear_port(port: int, timeout: int = 30) -> None:
    """Kill any zombie process holding our port so startup doesn't fail.

    This fixes the 'Errno 10048: address already in use' crash that occurs
    when a previous bifrost instance died but left the socket open (zombie
    state). Without this, the exe's restart loop cascades into multiple
    TIME_WAIT sockets and the user has to manually kill processes.
    """
    import subprocess
    import sys
    import time as _time

    def _find_pid_on_port() -> int | None:
        """Find PID listening on the given port. Returns None if free."""
        try:
            if sys.platform == "win32":
                out = subprocess.check_output(
                    ["netstat", "-ano"], text=True, creationflags=0x08000000
                )
                for line in out.splitlines():
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        return int(parts[-1])
            else:
                out = subprocess.check_output(
                    ["lsof", "-ti", f":{port}"], text=True
                ).strip()
                if out:
                    return int(out.splitlines()[0])
        except Exception:
            pass
        return None

    pid = _find_pid_on_port()
    if pid is None:
        return  # Port is free, nothing to do

    # Don't kill ourselves
    if pid == os.getpid():
        return

    log.warning("[startup] Port %d is held by PID %d — killing zombie process", port, pid)
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, creationflags=0x08000000,
            )
        else:
            os.kill(pid, 9)
    except Exception as e:
        log.warning("[startup] Could not kill PID %d: %s", pid, e)

    # Wait for the port to actually free up (TIME_WAIT can linger)
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        if _find_pid_on_port() is None:
            # Also check we can actually bind
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.bind(("127.0.0.1", port))
                test_sock.close()
                log.info("[startup] Port %d is now free", port)
                return
            except OSError:
                pass  # Still in TIME_WAIT
        _time.sleep(2)

    log.warning("[startup] Port %d did not free after %ds — attempting bind anyway", port, timeout)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Valhalla Bifrost V2")
    parser.add_argument("--config", "-c", default=None,
                        help="Path to valhalla.yaml (default: ./valhalla.yaml)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=None,
                        help="Bind port (default: from config, fallback 8765)")
    args = parser.parse_args()

    app = create_app(args.config)

    # Determine port: CLI arg > config > 8765
    port = args.port
    if port is None:
        from config_loader import get_config
        port = get_config().get("node", {}).get("port", 8765)

    # ── Auto-cleanup: kill any zombie process hogging our port ──────────
    _clear_port(port)

    import uvicorn
    log.info("Starting Bifrost on %s:%d", args.host, port)
    uvicorn.run(app, host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()

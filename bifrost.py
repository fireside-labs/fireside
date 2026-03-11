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
import sys
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

    # 2. FastAPI app
    app = FastAPI(
        title=f"Valhalla Bifrost — {node_name}",
        description="Valhalla Mesh V2 API",
        version="2.0.0",
    )

    # CORS — allow dashboard to connect
    dash_cfg = config.get("dashboard", {})
    cors_origins = dash_cfg.get("cors_origins", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
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


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Valhalla Bifrost V2")
    parser.add_argument("--config", "-c", default=None,
                        help="Path to valhalla.yaml (default: ./valhalla.yaml)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", "-p", type=int, default=None,
                        help="Bind port (default: from config, fallback 8765)")
    args = parser.parse_args()

    app = create_app(args.config)

    # Determine port: CLI arg > config > 8765
    port = args.port
    if port is None:
        from config_loader import get_config
        port = get_config().get("node", {}).get("port", 8765)

    import uvicorn
    log.info("Starting Bifrost on %s:%d", args.host, port)
    uvicorn.run(app, host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()

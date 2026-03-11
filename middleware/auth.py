"""
middleware/auth.py -- Heimdall's authentication & input-sanitization layer.

Provides:
    verify_node_token(handler, config)      -> str | None
    verify_dashboard_key(handler, config)   -> bool
    require_auth(handler, config, ...)      -> bool
    sanitize_path(user_path, allowed_root)  -> Path | None

Reads auth credentials from:
    1. valhalla.yaml  (V2) — mesh.auth_token, dashboard.auth_key
    2. config.json    (V1) — mesh_auth_token, dashboard_auth_key

If no credentials are configured, operates in WARNING MODE: logs every
unauthenticated request but allows it through. This prevents breaking
V1 nodes during the transition to V2.

Usage in a BifrostHandler method:

    from middleware.auth import require_auth, sanitize_path

    def _handle_fetch_file(self, body):
        if not require_auth(self, CONFIG, allow_node=True, allow_dashboard=False):
            return  # already sent 401
        safe = sanitize_path(body["path"], WORKSPACE_ROOT)
        if safe is None:
            self._respond(403, {"error": "path outside allowed root"})
            return
        ...
"""

import hmac
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("heimdall.auth")

# ---------------------------------------------------------------------------
# Sentinel values — if the user hasn't changed these, reject + warn
# ---------------------------------------------------------------------------

_PLACEHOLDER_TOKENS = frozenset({
    "change-me-to-a-long-random-string",
    "change-me-dashboard-key",
    "openclaw-mesh-default-change-me",
    "",
})

# ---------------------------------------------------------------------------
# Config readers
# ---------------------------------------------------------------------------

def _get_mesh_token(config: dict) -> Optional[str]:
    """Read the mesh auth token from config (V2 then V1 fallback)."""
    # V2: mesh.auth_token in valhalla.yaml (loaded as nested dict)
    mesh = config.get("mesh", {})
    if isinstance(mesh, dict):
        token = mesh.get("auth_token")
        if token:
            return str(token)
    # V1: flat key in config.json
    token = config.get("mesh_auth_token")
    if token:
        return str(token)
    return None


def _get_dashboard_key(config: dict) -> Optional[str]:
    """Read the dashboard API key from config."""
    # V2
    dash = config.get("dashboard", {})
    if isinstance(dash, dict):
        key = dash.get("auth_key")
        if key:
            return str(key)
    # V1
    key = config.get("dashboard_auth_key")
    if key:
        return str(key)
    return None


def _is_placeholder(value: Optional[str]) -> bool:
    """True if the value is a known placeholder that should be changed."""
    if value is None:
        return True
    return value.strip().lower() in _PLACEHOLDER_TOKENS


# ---------------------------------------------------------------------------
# Core verification
# ---------------------------------------------------------------------------

def verify_node_token(handler, config: dict) -> Optional[str]:
    """
    Verify the Authorization: Bearer <token> header.

    Returns the sender description on success, None on failure.
    On failure, sends a 401 response.
    """
    expected = _get_mesh_token(config)

    # Warning mode: no token configured
    if expected is None:
        log.warning("[auth] No mesh.auth_token configured — allowing request "
                    "(warning mode, set mesh.auth_token in valhalla.yaml)")
        return "unknown (no-auth)"

    # Placeholder check
    if _is_placeholder(expected):
        log.warning("[auth] mesh.auth_token is a placeholder — rejecting request. "
                    "Set a real token in valhalla.yaml!")
        _send_401(handler, "mesh.auth_token is a placeholder — configure a real token")
        return None

    auth_header = _get_header(handler, "Authorization")
    if not auth_header:
        _send_401(handler, "missing Authorization header")
        return None

    if not auth_header.startswith("Bearer "):
        _send_401(handler, "Authorization header must use Bearer scheme")
        return None

    provided = auth_header[len("Bearer "):]

    if not hmac.compare_digest(provided.encode(), expected.encode()):
        _send_401(handler, "invalid bearer token")
        _audit_failure(handler, "node_token", "invalid token")
        return None

    # Identify sender from optional header
    sender = _get_header(handler, "X-Bifrost-Node") or "authenticated-node"
    log.debug("[auth] Node token verified for %s", sender)
    return sender


def verify_dashboard_key(handler, config: dict) -> bool:
    """
    Verify the X-Dashboard-Key header.

    Returns True on success, False on failure (sends 401).
    """
    expected = _get_dashboard_key(config)

    # Warning mode: no key configured
    if expected is None:
        log.warning("[auth] No dashboard.auth_key configured — allowing request "
                    "(warning mode, set dashboard.auth_key in valhalla.yaml)")
        return True

    # Placeholder check
    if _is_placeholder(expected):
        log.warning("[auth] dashboard.auth_key is a placeholder — rejecting. "
                    "Set a real key in valhalla.yaml!")
        _send_401(handler, "dashboard.auth_key is a placeholder — configure a real key")
        return False

    # Check localhost bypass
    dash_cfg = config.get("dashboard", {})
    if isinstance(dash_cfg, dict) and dash_cfg.get("allow_localhost", False):
        client_ip = _get_client_ip(handler)
        if client_ip in ("127.0.0.1", "::1", "localhost"):
            log.debug("[auth] Dashboard localhost bypass for %s", client_ip)
            return True

    provided = _get_header(handler, "X-Dashboard-Key")
    if not provided:
        _send_401(handler, "missing X-Dashboard-Key header")
        return False

    if not hmac.compare_digest(provided.encode(), expected.encode()):
        _send_401(handler, "invalid dashboard key")
        _audit_failure(handler, "dashboard_key", "invalid key")
        return False

    log.debug("[auth] Dashboard key verified")
    return True


def require_auth(handler, config: dict, *,
                 allow_node: bool = True,
                 allow_dashboard: bool = True) -> bool:
    """
    Gate a route behind authentication.

    Tries node token first (if allow_node), then dashboard key (if
    allow_dashboard). Returns True if any auth succeeds. On failure,
    sends 401 and returns False.

    Usage:
        if not require_auth(self, CONFIG, allow_node=True, allow_dashboard=True):
            return  # 401 already sent
    """
    if allow_node:
        # Try node auth (Bearer token)
        auth_header = _get_header(handler, "Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            result = verify_node_token(handler, config)
            return result is not None

    if allow_dashboard:
        # Try dashboard auth (X-Dashboard-Key)
        dash_key = _get_header(handler, "X-Dashboard-Key")
        if dash_key:
            return verify_dashboard_key(handler, config)

    # Neither auth header present — check if we're in warning mode
    mesh_token = _get_mesh_token(config)
    dash_key_cfg = _get_dashboard_key(config)

    if mesh_token is None and dash_key_cfg is None:
        log.warning("[auth] No auth tokens configured — allowing request (warning mode)")
        return True

    _send_401(handler, "authentication required — provide Authorization: Bearer <token> "
              "or X-Dashboard-Key: <key>")
    return False


# ---------------------------------------------------------------------------
# Path sanitization
# ---------------------------------------------------------------------------

def sanitize_path(user_path: str, allowed_root: Path) -> Optional[Path]:
    """
    Resolve user_path against allowed_root and verify containment.

    Returns the resolved Path if it's under allowed_root.
    Returns None if path traversal is detected (including via symlinks).

    Examples:
        sanitize_path("docs/readme.md", Path("/workspace"))
            -> Path("/workspace/docs/readme.md")
        sanitize_path("../../etc/passwd", Path("/workspace"))
            -> None
    """
    if not user_path:
        return None

    try:
        # Reject absolute paths outright — they should never be user-supplied
        if user_path.startswith("/") or user_path.startswith("\\"):
            log.warning("[auth] Absolute path rejected: %s", user_path[:100])
            return None
        # Windows drive letters (C:\, D:\, etc.)
        if len(user_path) >= 2 and user_path[1] == ":" and user_path[0].isalpha():
            log.warning("[auth] Windows absolute path rejected: %s", user_path[:100])
            return None

        clean = user_path

        # Reject obvious traversal before even resolving
        if ".." in clean.split("/") or ".." in clean.split("\\"):
            log.warning("[auth] Path traversal blocked: %s", user_path[:100])
            return None

        resolved = (allowed_root / clean).resolve()
        root_resolved = allowed_root.resolve()

        if resolved == root_resolved or _is_subpath(resolved, root_resolved):
            return resolved

        log.warning("[auth] Path escape blocked: %s -> %s (root: %s)",
                    user_path[:100], resolved, root_resolved)
        return None

    except (ValueError, OSError) as e:
        log.warning("[auth] Path sanitization error: %s — %s", user_path[:100], e)
        return None


def _is_subpath(path: Path, root: Path) -> bool:
    """Check if path is under root (works on Python 3.9+)."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Model ID validation
# ---------------------------------------------------------------------------

_VALID_MODEL_PATTERN = re.compile(r'^[a-zA-Z0-9/_.:@-]{1,128}$')


def validate_model_id(model_id: str) -> bool:
    """
    Validate a model identifier for safe use in subprocess calls.

    Allows: alphanumeric, slashes, underscores, dots, colons, @, hyphens.
    Max length: 128 characters.
    """
    if not model_id:
        return False
    return bool(_VALID_MODEL_PATTERN.match(model_id))


# ---------------------------------------------------------------------------
# Regex validation (for antibody injection)
# ---------------------------------------------------------------------------

_MAX_ANTIBODY_PATTERN_LEN = 256


def validate_regex_pattern(pattern: str) -> Optional[str]:
    """
    Validate a regex pattern for safe injection into prompt_guard.

    Returns None if valid, or an error message if dangerous.
    """
    if not pattern:
        return "empty pattern"

    if len(pattern) > _MAX_ANTIBODY_PATTERN_LEN:
        return f"pattern too long ({len(pattern)} > {_MAX_ANTIBODY_PATTERN_LEN})"

    # Check for catastrophic backtracking indicators
    # (nested quantifiers like (a+)+ or (a*)*b)
    if re.search(r'\([^)]*[+*][^)]*\)[+*]', pattern):
        log.warning("[auth] ReDoS pattern blocked: %s", pattern[:60])
        return "potential ReDoS (nested quantifiers)"

    try:
        re.compile(pattern)
    except re.error as e:
        return f"invalid regex: {e}"

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_header(handler, name: str) -> Optional[str]:
    """Safely get a header from an HTTP handler."""
    try:
        return handler.headers.get(name)
    except Exception:
        return None


def _get_client_ip(handler) -> str:
    """Extract client IP from handler."""
    try:
        return handler.client_address[0]
    except Exception:
        return "unknown"


def _send_401(handler, message: str):
    """Send a 401 Unauthorized JSON response."""
    try:
        body = json.dumps({"error": "unauthorized", "detail": message}).encode()
        handler.send_response(401)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("WWW-Authenticate", "Bearer")
        handler.end_headers()
        handler.wfile.write(body)
        log.warning("[auth] 401 → %s: %s", _get_client_ip(handler), message)
    except Exception as e:
        log.error("[auth] Failed to send 401: %s", e)


def _audit_failure(handler, auth_type: str, reason: str):
    """Log auth failure for audit trail."""
    try:
        client_ip = _get_client_ip(handler)
        path = getattr(handler, 'path', 'unknown')
        log.warning("[audit] AUTH_FAILURE type=%s ip=%s path=%s reason=%s",
                    auth_type, client_ip, path, reason)
    except Exception:
        pass

"""
signing.py -- HMAC-SHA256 message signing for the Bifrost mesh.

All inter-node POSTs add:
    X-Bifrost-Sig: sha256=<hmac_hex>
    X-Bifrost-Node: <sender_node_name>

Thor verifies this on every incoming request to sensitive routes.
Unsigned requests from unknown sources are rejected with 401.

Config (config.json):
    "mesh_secret": "some-long-random-string"   # shared across all nodes

Usage — sign an outgoing request body:
    from signing import sign_body, make_signed_request
    headers = sign_body(b'{"text": "..."}', config)

Usage — verify an incoming handler:
    from signing import verify_request, SignatureError
    try:
        verify_request(handler, body_bytes, config)
    except SignatureError as e:
        _json_respond(handler, 401, {"error": str(e)})
        return
"""

import hashlib
import hmac
import logging
import socket

log = logging.getLogger("signing")

_DEFAULT_SECRET = "openclaw-mesh-default-change-me"


class SignatureError(Exception):
    pass


def _get_secret(config: dict) -> bytes:
    secret = config.get("mesh_secret", _DEFAULT_SECRET)
    if secret == _DEFAULT_SECRET:
        log.warning("[signing] Using default mesh_secret — set 'mesh_secret' in config.json!")
    return secret.encode()


def sign_body(body: bytes, config: dict) -> dict:
    """
    Compute HMAC-SHA256 over body and return headers dict to attach to request.
    Returns: {"X-Bifrost-Sig": "sha256=<hex>", "X-Bifrost-Node": "<node>"}
    """
    secret = _get_secret(config)
    mac    = hmac.new(secret, body, hashlib.sha256).hexdigest()
    node   = config.get("node_name", socket.gethostname().lower().split(".")[0])
    return {
        "X-Bifrost-Sig":  f"sha256={mac}",
        "X-Bifrost-Node": node,
    }


def verify_request(handler, body: bytes, config: dict,
                   strict: bool = True) -> str:
    """
    Verify X-Bifrost-Sig on an incoming request.
    Returns sender node name on success.
    Raises SignatureError on failure (caller should 401).

    strict=False: log warning but allow through (for gradual rollout).
    """
    sig_header = handler.headers.get("X-Bifrost-Sig", "")
    sender     = handler.headers.get("X-Bifrost-Node", "unknown")

    if not sig_header:
        msg = f"Missing X-Bifrost-Sig from {sender}"
        if strict:
            raise SignatureError(msg)
        log.warning("[signing] %s (strict=False, allowing)", msg)
        return sender

    if not sig_header.startswith("sha256="):
        raise SignatureError(f"Unsupported signature scheme: {sig_header[:20]}")

    provided = sig_header[len("sha256="):]
    secret   = _get_secret(config)
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(provided, expected):
        raise SignatureError(f"Invalid signature from node '{sender}'")

    log.debug("[signing] Verified signature from %s", sender)
    return sender


def make_signed_headers(body: bytes, config: dict,
                        extra: dict = None) -> dict:
    """
    Build a complete header dict for an outbound signed request.
    Merges sign_body() result with Content-Type and any extra headers.
    """
    headers = {
        "Content-Type": "application/json",
        **sign_body(body, config),
    }
    if extra:
        headers.update(extra)
    return headers


def verify_or_log(handler, body: bytes, config: dict) -> str:
    """
    Soft-verify: never raises, just logs and returns sender.
    Use for transitional rollout while other nodes upgrade.
    """
    try:
        return verify_request(handler, body, config, strict=False)
    except SignatureError as e:
        log.warning("[signing] Verification failed (soft): %s", e)
        return handler.headers.get("X-Bifrost-Node", "unknown")

"""
middleware/mtls.py — Optional mutual TLS for Valhalla node-to-node communication.

For production deployments where Tailscale is not available, this module
provides mTLS (mutual TLS) so nodes authenticate each other via X.509
certificates signed by a shared CA.

Usage:
    1. Generate a CA + per-node certs:
         python3 -m middleware.mtls generate-ca
         python3 -m middleware.mtls generate-cert --node odin
         python3 -m middleware.mtls generate-cert --node thor

    2. Add to valhalla.yaml:
         tls:
           enabled: true
           ca_cert: certs/ca.pem
           node_cert: certs/odin.pem
           node_key: certs/odin-key.pem

    3. bifrost.py reads this config and starts uvicorn with SSL context.

This module provides:
    - Certificate generation helpers (CLI)
    - SSLContext builder for both server and client sides
    - Verification of peer certificates
"""
from __future__ import annotations

import logging
import os
import ssl
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger("heimdall.mtls")

_BASE_DIR = Path(__file__).parent.parent
_CERTS_DIR = _BASE_DIR / "certs"


# ---------------------------------------------------------------------------
# SSL Context builders
# ---------------------------------------------------------------------------

def build_server_ssl_context(
    ca_cert: str,
    node_cert: str,
    node_key: str,
) -> ssl.SSLContext:
    """Build an SSL context for the Bifrost server (uvicorn).

    Requires client certificate verification (mutual TLS).
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile=node_cert, keyfile=node_key)
    ctx.load_verify_locations(cafile=ca_cert)
    ctx.verify_mode = ssl.CERT_REQUIRED  # mTLS: client must present cert
    ctx.check_hostname = False  # Tailscale IPs don't match cert hostnames
    log.info("[mtls] Server SSL context created (mTLS enabled)")
    return ctx


def build_client_ssl_context(
    ca_cert: str,
    node_cert: str,
    node_key: str,
) -> ssl.SSLContext:
    """Build an SSL context for outgoing requests to other nodes.

    Presents our node certificate and verifies server's certificate.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile=node_cert, keyfile=node_key)
    ctx.load_verify_locations(cafile=ca_cert)
    ctx.check_hostname = False  # Tailscale IPs
    ctx.verify_mode = ssl.CERT_REQUIRED
    log.info("[mtls] Client SSL context created")
    return ctx


# ---------------------------------------------------------------------------
# Certificate generation (using openssl CLI)
# ---------------------------------------------------------------------------

def generate_ca(
    certs_dir: Optional[Path] = None,
    days: int = 3650,
    org: str = "Valhalla Mesh",
) -> tuple:
    """Generate a self-signed CA certificate + key.

    Returns (ca_cert_path, ca_key_path).
    """
    d = certs_dir or _CERTS_DIR
    d.mkdir(parents=True, exist_ok=True)

    ca_key = d / "ca-key.pem"
    ca_cert = d / "ca.pem"

    # Generate CA private key
    subprocess.run([
        "openssl", "genrsa", "-out", str(ca_key), "4096"
    ], check=True, capture_output=True)

    # Generate self-signed CA certificate
    subprocess.run([
        "openssl", "req", "-new", "-x509",
        "-key", str(ca_key),
        "-out", str(ca_cert),
        "-days", str(days),
        "-subj", f"/O={org}/CN=Valhalla Mesh CA",
    ], check=True, capture_output=True)

    # Restrict permissions
    os.chmod(ca_key, 0o600)
    os.chmod(ca_cert, 0o644)

    log.info("[mtls] CA generated: %s", ca_cert)
    return ca_cert, ca_key


def generate_node_cert(
    node_name: str,
    ca_cert: Optional[Path] = None,
    ca_key: Optional[Path] = None,
    certs_dir: Optional[Path] = None,
    days: int = 365,
    org: str = "Valhalla Mesh",
) -> tuple:
    """Generate a node certificate signed by the CA.

    Returns (node_cert_path, node_key_path).
    """
    d = certs_dir or _CERTS_DIR
    d.mkdir(parents=True, exist_ok=True)

    ca_c = ca_cert or d / "ca.pem"
    ca_k = ca_key or d / "ca-key.pem"

    if not ca_c.exists() or not ca_k.exists():
        raise FileNotFoundError(
            f"CA files not found at {ca_c} / {ca_k}. Run generate_ca() first."
        )

    node_key = d / f"{node_name}-key.pem"
    node_cert_path = d / f"{node_name}.pem"
    node_csr = d / f"{node_name}.csr"

    # Generate node private key
    subprocess.run([
        "openssl", "genrsa", "-out", str(node_key), "2048"
    ], check=True, capture_output=True)

    # Generate CSR
    subprocess.run([
        "openssl", "req", "-new",
        "-key", str(node_key),
        "-out", str(node_csr),
        "-subj", f"/O={org}/CN={node_name}",
    ], check=True, capture_output=True)

    # Sign with CA
    subprocess.run([
        "openssl", "x509", "-req",
        "-in", str(node_csr),
        "-CA", str(ca_c),
        "-CAkey", str(ca_k),
        "-CAcreateserial",
        "-out", str(node_cert_path),
        "-days", str(days),
    ], check=True, capture_output=True)

    # Cleanup CSR, restrict key permissions
    node_csr.unlink(missing_ok=True)
    os.chmod(node_key, 0o600)
    os.chmod(node_cert_path, 0o644)

    log.info("[mtls] Node cert generated: %s (signed by CA)", node_cert_path)
    return node_cert_path, node_key


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------

def get_ssl_config(config: dict) -> Optional[dict]:
    """Extract TLS config from valhalla.yaml, returning None if not enabled.

    Returns dict with keys: ca_cert, node_cert, node_key (absolute paths).
    """
    tls = config.get("tls", {})
    if not tls.get("enabled", False):
        return None

    base = Path(config.get("_meta", {}).get("base_dir", "."))

    result = {}
    for key in ("ca_cert", "node_cert", "node_key"):
        path = tls.get(key, "")
        if not path:
            log.error("[mtls] Missing tls.%s in config", key)
            return None
        p = Path(path)
        if not p.is_absolute():
            p = base / p
        if not p.exists():
            log.error("[mtls] File not found: tls.%s = %s", key, p)
            return None
        result[key] = str(p)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="Valhalla mTLS certificate manager")
    sub = parser.add_subparsers(dest="cmd")

    ca_parser = sub.add_parser("generate-ca", help="Generate CA certificate")
    ca_parser.add_argument("--dir", default=str(_CERTS_DIR))
    ca_parser.add_argument("--days", type=int, default=3650)

    cert_parser = sub.add_parser("generate-cert", help="Generate node certificate")
    cert_parser.add_argument("--node", required=True, help="Node name (e.g. odin)")
    cert_parser.add_argument("--dir", default=str(_CERTS_DIR))
    cert_parser.add_argument("--days", type=int, default=365)

    args = parser.parse_args()

    if args.cmd == "generate-ca":
        ca, key = generate_ca(Path(args.dir), args.days)
        print(f"✓ CA certificate: {ca}")
        print(f"✓ CA key: {key}")
    elif args.cmd == "generate-cert":
        cert, key = generate_node_cert(args.node, certs_dir=Path(args.dir), days=args.days)
        print(f"✓ Node certificate: {cert}")
        print(f"✓ Node key: {key}")
    else:
        parser.print_help()

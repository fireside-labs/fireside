"""
mesh_discovery.py — LAN Auto-Discovery for Fireside Mesh.

UDP broadcast on port 8766:
  - Every Fireside instance runs a listener thread
  - When a device wants to join, it broadcasts a discovery packet
  - All listeners respond with their node info
  - The joiner picks from the list and enters the 6-digit PIN

No Tailscale, no manual IPs, no long tokens.
"""
from __future__ import annotations

import json
import logging
import socket
import threading
import time
from typing import Optional

log = logging.getLogger("valhalla.mesh.discovery")

DISCOVERY_PORT = 8766
DISCOVERY_MAGIC = b"FIRESIDE_DISCOVER"
RESPONSE_MAGIC = b"FIRESIDE_HERE"
BUFFER_SIZE = 1024


# ---------------------------------------------------------------------------
# Listener — runs on every Fireside instance
# ---------------------------------------------------------------------------

class DiscoveryListener(threading.Thread):
    """Background thread: listens for UDP discovery broadcasts and responds."""

    def __init__(self, node_name: str, node_port: int = 8765):
        super().__init__(daemon=True, name="mesh-discovery")
        self.node_name = node_name
        self.node_port = node_port
        self._stop_event = threading.Event()
        self._sock: Optional[socket.socket] = None

    def stop(self):
        self._stop_event.set()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    def run(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # On Windows, SO_REUSEADDR already handles port reuse
            # On Linux/macOS, SO_REUSEPORT might be needed
            try:
                self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass  # Not available on Windows

            self._sock.bind(("", DISCOVERY_PORT))
            self._sock.settimeout(2.0)

            log.info("[discovery] Listening on UDP port %d", DISCOVERY_PORT)

            while not self._stop_event.is_set():
                try:
                    data, addr = self._sock.recvfrom(BUFFER_SIZE)
                    if data.startswith(DISCOVERY_MAGIC):
                        self._respond(addr)
                except socket.timeout:
                    continue
                except OSError:
                    if self._stop_event.is_set():
                        break
                    raise

        except OSError as e:
            log.warning("[discovery] Could not bind to port %d: %s", DISCOVERY_PORT, e)
        finally:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
            log.info("[discovery] Listener stopped")

    def _respond(self, addr: tuple):
        """Send our node info back to the requester."""
        # Get our LAN IP
        my_ip = _get_lan_ip()

        response = {
            "name": self.node_name,
            "ip": my_ip,
            "port": self.node_port,
        }
        payload = RESPONSE_MAGIC + json.dumps(response).encode()

        try:
            self._sock.sendto(payload, addr)
            log.debug("[discovery] Responded to %s with %s", addr, response)
        except Exception as e:
            log.debug("[discovery] Failed to respond to %s: %s", addr, e)


# ---------------------------------------------------------------------------
# Scanner — called when Device 2 wants to find devices on the LAN
# ---------------------------------------------------------------------------

def scan_lan(timeout: float = 3.0) -> list[dict]:
    """Broadcast a discovery packet and collect responses.

    Returns list of dicts: [{"name": "odin", "ip": "192.168.1.50", "port": 8765}, ...]
    """
    found = []

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        # Broadcast to all networks
        sock.sendto(DISCOVERY_MAGIC, ("<broadcast>", DISCOVERY_PORT))
        log.info("[discovery] Broadcast sent, waiting %.1fs for responses...", timeout)

        deadline = time.time() + timeout
        seen_ips = set()

        while time.time() < deadline:
            try:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                sock.settimeout(remaining)
                data, addr = sock.recvfrom(BUFFER_SIZE)

                if data.startswith(RESPONSE_MAGIC):
                    payload = data[len(RESPONSE_MAGIC):]
                    info = json.loads(payload.decode())

                    # Deduplicate by IP
                    node_ip = info.get("ip", addr[0])
                    if node_ip not in seen_ips:
                        seen_ips.add(node_ip)
                        found.append({
                            "name": info.get("name", "unknown"),
                            "ip": node_ip,
                            "port": info.get("port", 8765),
                        })
                        log.info("[discovery] Found: %s at %s:%d",
                                 info.get("name"), node_ip, info.get("port", 8765))

            except socket.timeout:
                break
            except Exception as e:
                log.debug("[discovery] Error reading response: %s", e)
                break

        sock.close()

    except Exception as e:
        log.warning("[discovery] Scan failed: %s", e)

    return found


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_lan_ip() -> str:
    """Get this machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

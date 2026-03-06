"""
Valhalla War Room — Peer-to-peer agent mesh overlay for Bifrost v5.

Modules:
    store  — JSON-backed message bus and task board
    sync   — Gossip sync protocol (eventual consistency across nodes)
    ask    — Direct agent-to-agent inference via local/cloud models
"""

from .store import WarRoomStore
from .sync import GossipSync
from .ask import AskHandler

__all__ = ["WarRoomStore", "GossipSync", "AskHandler"]

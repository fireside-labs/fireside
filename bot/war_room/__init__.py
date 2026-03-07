"""
Valhalla War Room ΓÇö Peer-to-peer agent mesh overlay for Bifrost v5.

Modules:
    store      ΓÇö JSON-backed message bus and task board
    sync       ΓÇö Gossip sync protocol (eventual consistency across nodes)
    ask        ΓÇö Direct agent-to-agent inference via local/cloud models
    event_bus  ΓÇö In-process pub/sub hub (IIT / Phi)
    prediction ΓÇö Predictive Processing engine (Free Energy Principle)
    self_model ΓÇö Default Mode Network self-assessment
    hypotheses ΓÇö Hypothesis engine (6-pillar belief system)

Note: event_bus, prediction, self_model, hypotheses are imported directly
by callers (e.g. `from war_room import prediction`) to avoid circular imports.
"""

from .store import WarRoomStore
from .sync import GossipSync
from .ask import AskHandler

__all__ = [
    "WarRoomStore", "GossipSync", "AskHandler",
    "event_bus", "prediction", "self_model", "hypotheses",
]
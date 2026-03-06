"""
pheromone_chains.py — Symbiotic Pheromone Chain Reactions.

When a reliable pheromone is dropped on a path, this module automatically
triggers a chain reaction: adjacent nodes in the mesh get an amplified
signal that propagates the positive reinforcement further.

Similarly, danger pheromones trigger chain warnings to connected nodes.

Chains are bounded (max 2 hops) to prevent runaway amplification.

Chain rules:
  reliable -> amplify same resource at 60% intensity (1 hop only)
  danger   -> warn adjacent nodes at 50% intensity (1 hop only)

The chain runs in a background thread and calls _pheromone.drop() directly.
"""

import logging
import threading
import time

log = logging.getLogger("war-room.chains")

# Maximum chain hops to prevent cascade loops
MAX_HOPS = 1

# Intensity decay per hop
RELIABLE_DECAY = 0.60
DANGER_DECAY   = 0.50

# Minimum intensity to continue chaining (avoid noise)
MIN_INTENSITY  = 0.15

# Track recent chain drops to prevent feedback loops
# { resource: last_chain_ts }
_chain_cooldown: dict = {}
_COOLDOWN_SEC = 30
_lock = threading.Lock()


def _extract_nodes(resource: str) -> tuple:
    """Parse 'nodeA->nodeB' resource string."""
    if "->" in resource:
        parts = resource.split("->", 1)
        return parts[0].strip(), parts[1].strip()
    return resource, resource


def _in_cooldown(resource: str) -> bool:
    now = time.time()
    with _lock:
        last = _chain_cooldown.get(resource, 0)
        if now - last < _COOLDOWN_SEC:
            return True
        _chain_cooldown[resource] = now
        return False


def trigger_chain(
    pheromone_mod,        # the _pheromone module reference
    resource: str,
    pheromone_type: str,
    intensity: float,
    source_node: str,
    hop: int = 0,
) -> None:
    """
    Fire a background chain pheromone drop.
    Called after the original pheromone is already committed.
    """
    if hop >= MAX_HOPS:
        return
    if intensity < MIN_INTENSITY:
        return
    if _in_cooldown(f"chain:{resource}:{pheromone_type}"):
        return

    def _fire():
        try:
            src, dst = _extract_nodes(resource)
            if pheromone_type == "reliable":
                # Amplify: drop on the reverse path + broadcast
                chain_resource = f"{dst}->{src}"
                chain_intensity = round(intensity * RELIABLE_DECAY, 3)
                pheromone_mod.drop(
                    resource       = chain_resource,
                    pheromone_type = "reliable",
                    intensity      = chain_intensity,
                    dropped_by     = "chain-reaction",
                    reason         = f"symbiotic amplification from {resource} (hop {hop+1})"
                )
                log.debug("[chain] reliable chain: %s -> %s (%.2f)",
                          resource, chain_resource, chain_intensity)

            elif pheromone_type == "danger":
                # Propagate warning to source's own internal path
                chain_resource = f"{src}->mesh"
                chain_intensity = round(intensity * DANGER_DECAY, 3)
                pheromone_mod.drop(
                    resource       = chain_resource,
                    pheromone_type  = "danger",
                    intensity      = chain_intensity,
                    dropped_by     = "chain-reaction",
                    reason         = f"danger propagation from {resource} (hop {hop+1})"
                )
                log.debug("[chain] danger chain: %s -> %s (%.2f)",
                          resource, chain_resource, chain_intensity)
        except Exception as ex:
            log.debug("[chain] chain drop error: %s", ex)

    threading.Thread(target=_fire, daemon=True).start()

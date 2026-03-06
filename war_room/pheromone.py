"""
pheromone.py — Freya's Stigmergy layer.

Agents leave metadata traces ("pheromones") on resources before using them.
Other agents smell them and adjust behavior — zero-overhead coordination.

Storage: JSON file (pheromones.json next to memory.db).
No embeddings needed — lookup is by resource_path (exact or prefix match).

Decay model:
  effective_intensity = stored_intensity * exp(-λ * age_days)
  λ = 0.02/day for "danger"  (lingers ~35 days at 0.5)
  λ = 0.05/day for all else  (fades ~14 days at 0.5)

Reinforcement:
  Same resource + same pheromone_type from any agent → intensity stacks,
  capped at 1.0. Consensus amplifies the signal.

Pruning:
  On every write, pheromones with effective_intensity < 0.01 are removed.
"""

import json
import logging
import math
import os
import time
import urllib.parse
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.pheromone")

# Storage next to memory.db
_DEFAULT_PATH = str(Path(__file__).parent.parent / "pheromones.json")
PHEROMONE_PATH = os.environ.get("BIFROST_PHEROMONE_FILE", _DEFAULT_PATH)

VALID_TYPES = {"danger", "slow", "reliable", "deprecated", "experimental"}

# Decay lambdas (per day)
_LAMBDA = {
    "danger":       0.02,   # 35-day half-life — dangers linger
    "default":      0.05,   # 14-day half-life
}

_MIN_INTENSITY = 0.01   # below this → pruned


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _load() -> dict:
    """Load all pheromones from disk. Returns {resource_path: [pheromone, ...]}."""
    try:
        if os.path.exists(PHEROMONE_PATH):
            return json.loads(open(PHEROMONE_PATH, encoding="utf-8").read())
    except Exception as e:
        log.error("Failed to load pheromones: %s", e)
    return {}


def _save(data: dict) -> None:
    """Atomic write via temp file."""
    try:
        tmp = PHEROMONE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, PHEROMONE_PATH)
    except Exception as e:
        log.error("Failed to save pheromones: %s", e)


# ---------------------------------------------------------------------------
# Decay helpers
# ---------------------------------------------------------------------------

def _lambda(ptype: str) -> float:
    return _LAMBDA.get(ptype, _LAMBDA["default"])


def _effective(p: dict, now: Optional[float] = None) -> float:
    """Compute time-decayed intensity."""
    now = now or time.time()
    age_days = (now - p.get("ts", now)) / 86400.0
    lam = _lambda(p.get("pheromone_type", "default"))
    return p.get("intensity", 0.0) * math.exp(-lam * age_days)


def _prune(data: dict, now: float) -> dict:
    """Remove pheromones that have fully decayed."""
    pruned = {}
    removed = 0
    for resource, pheros in data.items():
        alive = [p for p in pheros if _effective(p, now) >= _MIN_INTENSITY]
        removed += len(pheros) - len(alive)
        if alive:
            pruned[resource] = alive
    if removed:
        log.info("[pheromone] Pruned %d expired pheromones", removed)
    return pruned


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def drop(resource: str, pheromone_type: str, intensity: float,
         dropped_by: str, reason: str = "") -> dict:
    """
    Drop a pheromone on a resource.

    If the same resource + type already exists from any agent, stack intensity.
    Capped at 1.0. Saves immediately.
    """
    pheromone_type = pheromone_type.lower()
    if pheromone_type not in VALID_TYPES:
        return {"error": f"invalid pheromone_type, must be one of {sorted(VALID_TYPES)}"}

    intensity = max(0.0, min(1.0, float(intensity)))
    now = time.time()
    data = _load()
    data = _prune(data, now)

    pheros = data.get(resource, [])

    # Find existing same-type pheromone (from any agent — consensus stacks)
    existing_idx = None
    for i, p in enumerate(pheros):
        if p.get("pheromone_type") == pheromone_type:
            existing_idx = i
            break

    if existing_idx is not None:
        old = pheros[existing_idx]
        old_eff = _effective(old, now)
        stacked = min(1.0, old_eff + intensity)
        pheros[existing_idx] = {
            "resource_path":   resource,
            "pheromone_type":  pheromone_type,
            "intensity":       stacked,
            "dropped_by":      dropped_by,     # last dropper recorded
            "reason":          reason or old.get("reason", ""),
            "ts":              now,
            "stacked":         True,
        }
        action = "stacked"
        final_intensity = stacked
    else:
        pheros.append({
            "resource_path":  resource,
            "pheromone_type": pheromone_type,
            "intensity":      intensity,
            "dropped_by":     dropped_by,
            "reason":         reason,
            "ts":             now,
            "stacked":        False,
        })
        action = "created"
        final_intensity = intensity

    data[resource] = pheros
    _save(data)

    log.info("[pheromone] %s %s on '%s' (intensity=%.2f, by=%s)",
             action, pheromone_type, resource, final_intensity, dropped_by)
    return {
        "action":     action,
        "resource":   resource,
        "type":       pheromone_type,
        "intensity":  round(final_intensity, 4),
        "dropped_by": dropped_by,
    }


def smell(resource: str) -> dict:
    """
    Return all live pheromones on a resource, sorted by effective intensity desc.
    Exact match on resource_path.
    """
    now = time.time()
    data = _load()
    pheros = data.get(resource, [])

    results = []
    for p in pheros:
        eff = _effective(p, now)
        if eff < _MIN_INTENSITY:
            continue
        age_days = (now - p.get("ts", now)) / 86400.0
        results.append({
            "resource_path":  p["resource_path"],
            "pheromone_type": p["pheromone_type"],
            "intensity":      round(eff, 4),
            "raw_intensity":  round(p.get("intensity", 0.0), 4),
            "dropped_by":     p.get("dropped_by", "?"),
            "reason":         p.get("reason", ""),
            "age_days":       round(age_days, 2),
            "stacked":        p.get("stacked", False),
        })

    results.sort(key=lambda x: x["intensity"], reverse=True)

    # Dominant signal
    dominant = results[0] if results else None
    summary = None
    if dominant:
        ptype = dominant["pheromone_type"]
        intensity = dominant["intensity"]
        if ptype == "danger":
            summary = f"⚠️ DANGER (intensity={intensity:.2f}) — {dominant.get('reason', '')}"
        elif ptype == "slow":
            summary = f"🐢 slow resource (intensity={intensity:.2f})"
        elif ptype == "reliable":
            summary = f"✅ reliable (intensity={intensity:.2f})"
        elif ptype == "deprecated":
            summary = f"🚫 deprecated (intensity={intensity:.2f})"
        elif ptype == "experimental":
            summary = f"🧪 experimental (intensity={intensity:.2f})"

    return {
        "resource":   resource,
        "pheromones": results,
        "count":      len(results),
        "summary":    summary,
    }


def smell_prefix(prefix: str) -> dict:
    """
    Return all pheromones on resources that start with `prefix`.
    Useful for broad queries like smell_prefix("numpy") or smell_prefix("/api").
    """
    now = time.time()
    data = _load()
    all_results = []

    for resource, pheros in data.items():
        if not resource.startswith(prefix):
            continue
        for p in pheros:
            eff = _effective(p, now)
            if eff < _MIN_INTENSITY:
                continue
            all_results.append({
                "resource_path":  resource,
                "pheromone_type": p["pheromone_type"],
                "intensity":      round(eff, 4),
                "dropped_by":     p.get("dropped_by", "?"),
                "reason":         p.get("reason", ""),
            })

    all_results.sort(key=lambda x: x["intensity"], reverse=True)
    return {
        "prefix":     prefix,
        "pheromones": all_results,
        "count":      len(all_results),
    }


def stats() -> dict:
    """Return pheromone store health metrics."""
    now = time.time()
    data = _load()
    total, alive, by_type = 0, 0, {}
    for pheros in data.values():
        for p in pheros:
            total += 1
            eff = _effective(p, now)
            if eff >= _MIN_INTENSITY:
                alive += 1
                t = p.get("pheromone_type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1

    return {
        "status":         "ok",
        "total_stored":   total,
        "alive":          alive,
        "expired":        total - alive,
        "resources":      len(data),
        "by_type":        by_type,
        "store_path":     PHEROMONE_PATH,
    }


# ---------------------------------------------------------------------------
# HTTP handlers (called from bifrost_local.py)
# ---------------------------------------------------------------------------

def handle_drop(body: dict) -> tuple:
    """
    POST /pheromone
    Body: {"node":"thor", "resource":"numpy.linalg.svd",
           "type":"reliable", "intensity":0.9, "reason":"..."}
    """
    resource = (body.get("resource") or "").strip()
    ptype    = (body.get("type") or "").strip()
    intensity = float(body.get("intensity", 0.5))
    node     = (body.get("node") or body.get("dropped_by") or "unknown").strip()
    reason   = (body.get("reason") or "").strip()

    if not resource:
        return 400, {"error": "resource is required"}
    if not ptype:
        return 400, {"error": "type is required"}

    result = drop(resource, ptype, intensity, node, reason)
    code   = 400 if "error" in result else 200
    return code, result


def handle_smell(path: str) -> tuple:
    """
    GET /pheromone?resource=<path>[&prefix=1]
    """
    parsed = urllib.parse.urlparse(path)
    params = urllib.parse.parse_qs(parsed.query)

    resource = params.get("resource", [None])[0]
    use_prefix = params.get("prefix", ["0"])[0] in ("1", "true", "yes")

    if not resource:
        # No resource = return stats
        return 200, stats()

    if use_prefix:
        return 200, smell_prefix(resource)

    return 200, smell(resource)

"""
metabolic.py — Node metabolic rate tracker.

Tracks how hard Freya is working per hour:

    metabolic_rate = (tasks_completed + memories_written + asks_served) / hours_running

A rate near 0 = idle or stuck.
A high rate = actively contributing to the mesh.
Exposes GET /metabolic-rate — one number, instant observability.

Also tracks per-activity rates so callers can see the breakdown:
    - asks/hr      — inference requests served
    - memories/hr  — memory writes received
    - tasks/hr     — task:complete hooks fired
    - hook_events/hr — total hook events processed
"""

import threading
import time

_lock = threading.Lock()

# Counters — incremented by bifrost hooks / route patches
_counters = {
    "asks_served":     0,
    "memories_written": 0,
    "tasks_completed": 0,
    "hook_events":     0,
}

# Session start time
_started_at: float = time.time()


# ---------------------------------------------------------------------------
# Public increment API — called by bifrost_local patches
# ---------------------------------------------------------------------------

def record_ask() -> None:
    """Call when /ask succeeds."""
    with _lock:
        _counters["asks_served"] += 1


def record_memory_write(count: int = 1) -> None:
    """Call when /memory-sync upserts memories."""
    with _lock:
        _counters["memories_written"] += count


def record_task_complete() -> None:
    """Call when task:complete hook fires."""
    with _lock:
        _counters["tasks_completed"] += 1


def record_hook_event() -> None:
    """Call for any hook event emitted."""
    with _lock:
        _counters["hook_events"] += 1


# ---------------------------------------------------------------------------
# Rate computation
# ---------------------------------------------------------------------------

def _hours_running() -> float:
    elapsed = time.time() - _started_at
    return max(elapsed / 3600, 1 / 3600)   # minimum 1 second to avoid /0


def get_rate() -> dict:
    """Compute and return current metabolic stats."""
    with _lock:
        snap = dict(_counters)

    hrs = _hours_running()
    total_work = snap["asks_served"] + snap["memories_written"] + snap["tasks_completed"]
    rate = round(total_work / hrs, 2)

    # Assess vitality
    if rate == 0:
        vitality = "dormant"
    elif rate < 10:
        vitality = "resting"
    elif rate < 50:
        vitality = "active"
    elif rate < 200:
        vitality = "busy"
    else:
        vitality = "surging"

    return {
        "metabolic_rate":   rate,
        "unit":             "work_units/hr",
        "vitality":         vitality,
        "uptime_hours":     round(hrs, 3),
        "uptime_seconds":   round(time.time() - _started_at, 1),
        "totals": {
            "asks_served":     snap["asks_served"],
            "memories_written": snap["memories_written"],
            "tasks_completed": snap["tasks_completed"],
            "hook_events":     snap["hook_events"],
            "total_work_units": total_work,
        },
        "rates_per_hour": {
            "asks":      round(snap["asks_served"] / hrs, 2),
            "memories":  round(snap["memories_written"] / hrs, 2),
            "tasks":     round(snap["tasks_completed"] / hrs, 2),
            "hooks":     round(snap["hook_events"] / hrs, 2),
        },
    }

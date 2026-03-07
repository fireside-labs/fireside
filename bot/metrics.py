"""
metrics.py -- Per-route request latency tracking for the Bifrost mesh.

Tracks p50 / p95 / p99 latency on instrumented routes.
Thread-safe, bounded ring buffer (last 1000 samples per route).

Usage — wrap a handler:
    from metrics import record

    t0 = time.monotonic()
    # ... do work ...
    record("/critique", time.monotonic() - t0)

GET /metrics exposes: per-route percentiles + call counts + GPU stats.
"""

import statistics
import threading
import time
import logging
from collections import deque

log = logging.getLogger("metrics")

_lock    = threading.Lock()
_MAX_SAMPLES = 1000

# {route: deque([latency_ms, ...])}
_samples: dict[str, deque] = {}

# Call counters: {route: {"calls": int, "errors": int}}
_counters: dict[str, dict] = {}

_start_time = time.time()


def record(route: str, elapsed_s: float, error: bool = False):
    """Record one request's latency (in seconds) for a route."""
    ms = elapsed_s * 1000.0
    with _lock:
        if route not in _samples:
            _samples[route]  = deque(maxlen=_MAX_SAMPLES)
            _counters[route] = {"calls": 0, "errors": 0}
        _samples[route].append(ms)
        _counters[route]["calls"] += 1
        if error:
            _counters[route]["errors"] += 1


def _percentile(data: list, pct: float) -> float:
    if not data:
        return 0.0
    data_sorted = sorted(data)
    idx = max(0, int(len(data_sorted) * pct / 100) - 1)
    return round(data_sorted[idx], 2)


def _gpu_stats() -> dict:
    """Best-effort VRAM stats via nvidia-smi."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            parts = [p.strip() for p in result.stdout.strip().split(",")]
            return {
                "gpu_util_pct":   int(parts[0]),
                "vram_used_mb":   int(parts[1]),
                "vram_total_mb":  int(parts[2]),
                "vram_used_pct":  round(int(parts[1]) / int(parts[2]) * 100, 1),
            }
    except Exception:
        pass
    return {}


def snapshot() -> dict:
    """Return full metrics snapshot for GET /metrics."""
    with _lock:
        routes = {}
        for route, buf in _samples.items():
            data = list(buf)
            cnt  = _counters.get(route, {})
            routes[route] = {
                "calls":   cnt.get("calls", 0),
                "errors":  cnt.get("errors", 0),
                "p50_ms":  _percentile(data, 50),
                "p95_ms":  _percentile(data, 95),
                "p99_ms":  _percentile(data, 99),
                "avg_ms":  round(statistics.mean(data), 2) if data else 0.0,
                "max_ms":  round(max(data), 2) if data else 0.0,
                "samples": len(data),
            }

    return {
        "uptime_s":  round(time.time() - _start_time),
        "node":      "thor",
        "routes":    routes,
        "gpu":       _gpu_stats(),
        "ts":        time.time(),
    }

# -*- coding: utf-8 -*-
"""
perf_metrics.py -- Performance metrics with percentile tracking.

Ring buffer per metric, computes p50/p95/p99 on demand.
@timed decorator for wrapping functions.
Optional GPU metrics via nvidia-smi.

Usage:
    from perf_metrics import timed, get_metrics
    
    @timed("ask_pipeline")
    def handle_ask(...): ...

    stats = get_metrics().snapshot()
"""

import functools
import json
import logging
import subprocess
import threading
import time
from collections import deque

log = logging.getLogger("bifrost")

_RING_SIZE = 1000  # samples per metric


class MetricsCollector:
    def __init__(self, ring_size: int = _RING_SIZE):
        self._ring_size = ring_size
        self._metrics: dict = {}  # name -> deque of (ts, duration_ms)
        self._counters: dict = {}  # name -> int
        self._lock = threading.Lock()

    def record(self, name: str, duration_ms: float):
        """Record a timing sample."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = deque(maxlen=self._ring_size)
            self._metrics[name].append((time.time(), duration_ms))

    def increment(self, name: str, amount: int = 1):
        """Increment a counter."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def _percentile(self, values: list, pct: float) -> float:
        if not values:
            return 0.0
        sorted_v = sorted(values)
        idx = int(len(sorted_v) * pct / 100)
        idx = min(idx, len(sorted_v) - 1)
        return sorted_v[idx]

    def get_metric(self, name: str) -> dict:
        """Get stats for a single metric."""
        with self._lock:
            ring = self._metrics.get(name)
            if not ring:
                return {"name": name, "samples": 0}
            durations = [d for _, d in ring]

        n = len(durations)
        avg = sum(durations) / n if n else 0
        return {
            "name": name,
            "samples": n,
            "mean_ms": round(avg, 2),
            "p50_ms": round(self._percentile(durations, 50), 2),
            "p95_ms": round(self._percentile(durations, 95), 2),
            "p99_ms": round(self._percentile(durations, 99), 2),
            "min_ms": round(min(durations), 2) if durations else 0,
            "max_ms": round(max(durations), 2) if durations else 0,
        }

    def snapshot(self) -> dict:
        """Full metrics snapshot including GPU if available."""
        with self._lock:
            metric_names = list(self._metrics.keys())
            counters = dict(self._counters)

        timings = {}
        for name in metric_names:
            timings[name] = self.get_metric(name)

        gpu = self._gpu_status()

        return {
            "timings": timings,
            "counters": counters,
            "gpu": gpu,
            "ring_size": self._ring_size,
        }

    def _gpu_status(self) -> dict:
        """Query nvidia-smi for GPU metrics. Returns empty on failure."""
        try:
            result = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return {"available": False}
            line = result.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                return {
                    "available": True,
                    "name": parts[0],
                    "memory_used_mb": int(parts[1]),
                    "memory_total_mb": int(parts[2]),
                    "utilization_pct": int(parts[3]),
                    "temperature_c": int(parts[4]),
                    "power_draw_w": float(parts[5]),
                    "memory_pct": round(int(parts[1]) / max(1, int(parts[2])) * 100, 1),
                }
        except Exception:
            pass
        return {"available": False}


# Global instance
_collector = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _collector


def timed(metric_name: str):
    """Decorator to time a function and record the metric."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start) * 1000
                _collector.record(metric_name, elapsed_ms)
        return wrapper
    return decorator


class TimerContext:
    """Context manager for timing code blocks.
    
    Usage:
        with TimerContext("my_operation"):
            do_something()
    """
    def __init__(self, metric_name: str):
        self.name = metric_name
        self.start = 0.0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        elapsed_ms = (time.time() - self.start) * 1000
        _collector.record(self.name, elapsed_ms)

"""
philosopher-stone plugin — Nightly wisdom distillation.

Ported from V1 bot/philosopher_stone.py (208 lines).

Queries memory stores for:
  - Top CRISPR patterns (skill-transfer memories)
  - Golden Facts (mesh consensus truths)
  - Immune Vaccines (known error cures)
  - Mesh health from Heimdall

Outputs: philosopher_prompt.md — injected at session start.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger("valhalla.philosopher-stone")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_BASE_DIR = Path(".")
_MESH_NODES: dict = {}
_SCHEDULE_HOUR = 3
_MIN_REBUILD_INTERVAL = 3600 * 6
_last_built: float = 0


def _publish(topic: str, payload: dict) -> None:
    try:
        from plugin_loader import emit_event
        emit_event(topic, payload)
    except Exception:
        pass


def _get_json(url: str, timeout: int = 10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _output_path() -> Path:
    return _BASE_DIR / "war_room_data" / "philosopher_prompt.md"


def _fetch_memories(base_url: str, tags: list, min_importance: float, limit: int) -> list:
    """Query a memory store for specific memory types."""
    try:
        query = " ".join(tags)
        url = f"{base_url}/memory-query?q={urllib.parse.quote(query)}&limit={limit * 2}"
        results = _get_json(url)
        if not results:
            return []

        filtered = []
        for m in (results if isinstance(results, list) else []):
            m_tags = m.get("tags", [])
            if m.get("importance", 0) < min_importance:
                continue
            if any(t in m_tags for t in tags):
                filtered.append(m)
        return filtered[:limit]
    except Exception:
        return []


def _fetch_health(base_url: str) -> list:
    """Pull patterns + high-severity events from Heimdall."""
    lines = []
    patterns = _get_json(f"{base_url}/patterns")
    if isinstance(patterns, list):
        for p in patterns[:5]:
            desc = p.get("description") or p.get("pattern") or str(p)
            conf = p.get("confidence", "")
            conf_str = f" (confidence: {conf:.2f})" if isinstance(conf, float) else ""
            lines.append(f"- [pattern] {desc}{conf_str}")

    events = _get_json(f"{base_url}/audit?severity=high&limit=10&since=24h")
    if isinstance(events, list):
        for ev in events[:5]:
            msg = ev.get("message") or ev.get("event") or str(ev)
            lines.append(f"- [alert] {msg}")
    return lines


def build_wisdom() -> str:
    """Force a wisdom rebuild. Returns the prompt content."""
    global _last_built

    log.info("[philosopher-stone] Building wisdom prompt...")
    sections = []

    # Find Freya (memory node) and Heimdall (security node)
    freya_url = None
    heimdall_url = None
    for name, info in _MESH_NODES.items():
        ip = info.get("ip", "")
        port = info.get("port", 8765)
        role = info.get("role", "")
        if role == "memory" or name == "freya":
            freya_url = f"http://{ip}:{port}"
        if role == "security" or name == "heimdall":
            heimdall_url = f"http://{ip}:{port}"

    # Fallback to localhost
    if not freya_url:
        freya_url = "http://127.0.0.1:8765"

    # 1. CRISPR patterns
    crispr = _fetch_memories(freya_url, ["crispr", "skill-transfer"], 0.85, 20)
    if crispr:
        lines = [f"- {m.get('content', '').strip()}" for m in crispr if m.get("content")]
        if lines:
            sections.append("## Patterns (CRISPR-distilled skills)\n" + "\n".join(lines[:20]))

    # 2. Golden Facts
    facts = _fetch_memories(freya_url, ["golden-fact"], 0.9, 10)
    if facts:
        lines = [f"- {m.get('content', '').strip()}" for m in facts if m.get("content")]
        if lines:
            sections.append("## Golden Facts (mesh consensus)\n" + "\n".join(lines[:10]))

    # 3. Immune Vaccines
    vaccines = _fetch_memories(freya_url, ["vaccine", "immune"], 0.8, 5)
    if vaccines:
        lines = [f"- {m.get('content', '').strip()}" for m in vaccines if m.get("content")]
        if lines:
            sections.append("## Immune Vaccines (known error cures)\n" + "\n".join(lines[:5]))

    # 4. Mesh Health
    if heimdall_url:
        health = _fetch_health(heimdall_url)
        if health:
            sections.append("## Mesh Health (Heimdall)\n" + "\n".join(health))

    if not sections:
        log.warning("[philosopher-stone] No wisdom found — nodes offline or empty")
        return ""

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prompt = (
        f"# Philosopher's Stone — Mesh Wisdom\n"
        f"*Distilled {now}*\n"
        f"*Read this. It represents what the entire mesh has learned. Apply it.*\n\n"
        + "\n\n".join(sections)
        + "\n\n---\n*End of distilled wisdom. Resume normal session.*\n"
    )

    output = _output_path()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(prompt, encoding="utf-8")
    _last_built = time.time()

    _publish("wisdom.rebuilt", {"sections": len(sections), "chars": len(prompt)})

    log.info("[philosopher-stone] Built: %d sections, %d chars", len(sections), len(prompt))
    return prompt


def read_wisdom() -> str:
    """Read current wisdom prompt."""
    out = _output_path()
    if out.exists():
        age = time.time() - out.stat().st_mtime
        if age < 86400 * 2:
            return out.read_text(encoding="utf-8")
    return build_wisdom()


def _scheduler():
    """Background scheduler for nightly rebuilds."""
    time.sleep(60)
    # Initial build if no file
    if not _output_path().exists():
        build_wisdom()
    while True:
        now = datetime.now()
        if (now.hour == _SCHEDULE_HOUR and now.minute < 10
                and (time.time() - _last_built) > _MIN_REBUILD_INTERVAL):
            build_wisdom()
        time.sleep(300)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict) -> None:
    global _BASE_DIR, _MESH_NODES, _SCHEDULE_HOUR

    _BASE_DIR = Path(config.get("_meta", {}).get("base_dir", "."))
    _MESH_NODES = config.get("mesh", {}).get("nodes", {})
    ps_cfg = config.get("philosopher_stone", {})
    _SCHEDULE_HOUR = ps_cfg.get("schedule_hour", 3)

    router = APIRouter(tags=["philosopher-stone"])

    @router.post("/api/v1/philosopher-stone/build")
    async def api_build():
        content = build_wisdom()
        return {"ok": bool(content), "chars": len(content)}

    @router.get("/api/v1/philosopher-stone/prompt")
    async def api_read():
        content = read_wisdom()
        return {
            "prompt": content,
            "chars": len(content),
            "last_built": _last_built,
            "schedule_hour": _SCHEDULE_HOUR,
        }

    app.include_router(router)

    t = threading.Thread(target=_scheduler, daemon=True, name="philosopher-stone")
    t.start()

    log.info("[philosopher-stone] Plugin loaded. Rebuilds at %02d:00", _SCHEDULE_HOUR)

"""
philosopher_stone.py — The Philosopher's Stone

Nightly aggregator that distills the mesh's best knowledge into a
high-density wisdom prompt. Queries Freya for:
  - Top 20 CRISPR patterns (skill-transfer memories, importance >= 0.9)
  - Top 10 Golden Facts (waggle-dance approved truths)
  - Top 5 immune vaccines (known error cures)

Output: bot/philosopher_prompt.md — injected at session start.
Agents that load this start every session with accumulated mesh wisdom
instead of cold inference.
"""
import json
import logging
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("philosopher-stone")

FREYA_BASE = "http://100.102.105.3:8765"
HEIMDALL_BASE = "http://100.108.153.23:8765"
OUTPUT_PATH = Path(__file__).parent / "philosopher_prompt.md"
SCHEDULE_HOUR = 3  # 3 AM daily
MIN_REBUILD_INTERVAL = 3600 * 6  # Never rebuild more than once per 6h


class PhilosopherStone:
    """Distills mesh wisdom into a session-injectable prompt."""

    def __init__(self, freya_base: str = FREYA_BASE, heimdall_base: str = HEIMDALL_BASE, output: Path = OUTPUT_PATH):
        self.freya = freya_base
        self.heimdall = heimdall_base
        self.output = output
        self._thread = None
        self._last_built = 0.0

    def start(self):
        """Start as background daemon thread."""
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="philosopher-stone"
        )
        self._thread.start()
        log.info("[philosopher-stone] Daemon started (rebuilds at %02d:00)", SCHEDULE_HOUR)

    def build_now(self) -> str:
        """Force a rebuild and return the prompt content."""
        log.info("[philosopher-stone] Building wisdom prompt...")
        sections = []

        crispr = self._fetch_memories(
            tags=["crispr", "skill-transfer"],
            min_importance=0.85,
            limit=20,
        )
        if crispr:
            lines = [f"- {m.get('content', '').strip()}" for m in crispr if m.get("content")]
            sections.append("## Patterns (CRISPR-distilled skills)\n" + "\n".join(lines[:20]))

        facts = self._fetch_memories(
            tags=["golden-fact"],
            min_importance=0.9,
            limit=10,
        )
        if facts:
            lines = [f"- {m.get('content', '').strip()}" for m in facts if m.get("content")]
            sections.append("## Golden Facts (mesh consensus)\n" + "\n".join(lines[:10]))

        vaccines = self._fetch_memories(
            tags=["vaccine", "immune"],
            min_importance=0.8,
            limit=5,
        )
        if vaccines:
            lines = [f"- {m.get('content', '').strip()}" for m in vaccines if m.get("content")]
            sections.append("## Immune Vaccines (known error cures)\n" + "\n".join(lines[:5]))

        # --- Heimdall: Mesh Health ---
        health_lines = self._fetch_heimdall_health()
        if health_lines:
            sections.append("## Mesh Health (last 24h from Heimdall)\n" + "\n".join(health_lines))

        if not sections:
            log.warning("[philosopher-stone] No wisdom found — Freya offline or empty corpus")
            return ""

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        prompt = (
            f"# Philosopher's Stone — Mesh Wisdom\n"
            f"*Distilled {now} from CRISPR patterns, Golden Facts, immune vaccines, Heimdall mesh health.*\n"
            f"*Read this. It represents what the entire mesh has learned. Apply it.*\n\n"
            + "\n\n".join(sections)
            + "\n\n---\n*End of distilled wisdom. Resume normal session.*\n"
        )

        self.output.write_text(prompt, encoding="utf-8")
        self._last_built = time.time()
        log.info(
            "[philosopher-stone] Built: %d sections, %d chars → %s",
            len(sections), len(prompt), self.output.name,
        )
        return prompt

    def read(self) -> str:
        """Read the current prompt (rebuild if stale or missing)."""
        if not self.output.exists():
            return self.build_now()
        age = time.time() - self.output.stat().st_mtime
        if age > 86400 * 2:  # >48h stale → rebuild
            return self.build_now()
        return self.output.read_text(encoding="utf-8")

    # ------------------------------------------------------------------ #

    def _fetch_memories(
        self, tags: list, min_importance: float, limit: int
    ) -> list:
        """Query Freya's memory store for specific memory types."""
        try:
            # Use a broad query — Freya ranks by vector similarity + importance
            query = " ".join(tags)
            url = f"{self.freya}/memory-query?q={urllib.parse.quote(query)}&limit={limit * 2}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as r:
                results = json.loads(r.read())

            # Filter by tag and importance
            filtered = []
            for m in results:
                m_tags = m.get("tags", [])
                m_importance = m.get("importance", 0)
                if m_importance < min_importance:
                    continue
                if any(t in m_tags for t in tags):
                    filtered.append(m)

            return filtered[:limit]
        except Exception as e:
            log.debug("[philosopher-stone] Fetch failed (%s tags): %s", tags, e)
            return []

    def _fetch_heimdall_health(self) -> list:
        """Pull learned patterns + high-severity audit events from Heimdall."""
        lines = []
        try:
            url = f"{self.heimdall}/patterns"
            with urllib.request.urlopen(urllib.request.Request(url), timeout=8) as r:
                patterns = json.loads(r.read())
            if isinstance(patterns, list):
                for p in patterns[:5]:
                    desc = p.get("description") or p.get("pattern") or str(p)
                    conf = p.get("confidence", "")
                    conf_str = f" (confidence: {conf:.2f})" if isinstance(conf, float) else ""
                    lines.append(f"- [pattern] {desc}{conf_str}")
        except Exception as e:
            log.debug("[philosopher-stone] Heimdall /patterns unavailable: %s", e)

        try:
            url = f"{self.heimdall}/audit?severity=high&limit=10&since=24h"
            with urllib.request.urlopen(urllib.request.Request(url), timeout=8) as r:
                events = json.loads(r.read())
            if isinstance(events, list):
                for ev in events[:5]:
                    msg = ev.get("message") or ev.get("event") or str(ev)
                    ts = ev.get("timestamp", "")[:16]  # YYYY-MM-DDTHH:MM
                    lines.append(f"- [alert {ts}] {msg}")
        except Exception as e:
            log.debug("[philosopher-stone] Heimdall /audit unavailable: %s", e)

        return lines

    def _loop(self):
        # Initial build on startup (after 60s delay)
        time.sleep(60)
        if not self.output.exists():
            self.build_now()

        while True:
            now = datetime.now()
            # Rebuild at scheduled hour if enough time has passed
            if (
                now.hour == SCHEDULE_HOUR
                and now.minute < 10
                and (time.time() - self._last_built) > MIN_REBUILD_INTERVAL
            ):
                self.build_now()
            time.sleep(300)  # Check every 5 minutes


# Module-level instance
_stone = None


def get_stone() -> PhilosopherStone:
    global _stone
    if _stone is None:
        _stone = PhilosopherStone()
    return _stone


def get_prompt() -> str:
    """Get the current philosopher prompt (used at session start)."""
    return get_stone().read()

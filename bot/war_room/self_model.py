"""
self_model.py ΓÇö Freya's Default Mode Network (Pillar 9)

Purpose:
    Implements the "strange loop" of self-awareness. During idle time or on
    explicit POST /reflect, Freya gathers signals about her own behavior from
    the event bus, hypotheses, memory patterns, and prediction accuracy ΓÇö then
    uses Ollama to write a 5-paragraph self-assessment.

    The self-model is stored to mesh/docs/self_model_freya.md (node-specific
    so git pulls don't clobber peer self-models). On next session startup,
    bifrost_local.py prepends this to the system prompt. The agent *becomes*
    what she believes about herself.

    The Strange Loop:
        self_model ΓåÆ shapes system prompt ΓåÆ shapes behavior
        ΓåÆ shapes predictions ΓåÆ shapes event bus history
        ΓåÆ shapes next self_model

Endpoint:
    POST /reflect          ΓÇö trigger a reflection cycle (async, returns immediately)
    GET  /self-model       ΓÇö return current self-assessment + metadata
"""

import json
import logging
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger("bifrost.self_model")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_OLLAMA_BASE   = "http://127.0.0.1:11434"
_REFLECT_MODEL = os.environ.get("BIFROST_DREAM_MODEL", "qwen2.5-coder:32b")
_NODE_ID       = os.environ.get("BIFROST_NODE_ID", "freya")
_BOT_DIR       = Path(__file__).parent.parent          # ...workspace/bot/
_SELF_MODEL_PATH = _BOT_DIR / "mesh" / "docs" / f"self_model_{_NODE_ID}.md"

# Minimum seconds between full reflections (don't over-reflect)
_REFLECT_COOLDOWN = 3600 * 4   # 4 hours by default

_last_reflect_ts: float = 0.0


# ---------------------------------------------------------------------------
# Signal gathering
# ---------------------------------------------------------------------------

def _gather_signals() -> dict:
    """
    Pull together all available self-knowledge signals.
    Each section is best-effort ΓÇö missing modules are silently skipped.
    """
    signals: dict = {"node": _NODE_ID, "ts": int(time.time())}

    # 1. Event bus history
    try:
        from war_room import event_bus as bus
        recent = bus.get_log(limit=200)
        topic_counts: dict = {}
        for ev in recent:
            t = ev.get("topic", "unknown")
            topic_counts[t] = topic_counts.get(t, 0) + 1
        signals["event_topics"] = topic_counts
        signals["total_events"] = len(recent)
    except Exception:
        pass

    # 2. Active hypotheses (what do I believe?)
    try:
        from war_room import hypotheses as hyp
        hyps = hyp.get_hypotheses(limit=20, min_confidence=0.4)
        confirmed = [h for h in hyps if h.get("test_result") == "confirmed"]
        refuted   = [h for h in hyps if h.get("test_result") == "refuted"]
        signals["hypothesis_count"]   = len(hyps)
        signals["confirmed_count"]    = len(confirmed)
        signals["refuted_count"]      = len(refuted)
        signals["top_beliefs"]        = [h.get("hypothesis", "")[:80] for h in confirmed[:3]]
        signals["nightmare_count"]    = sum(1 for h in hyps if float(h.get("valence", 0)) < -0.5)
    except Exception:
        pass

    # 3. Prediction accuracy (what surprises me?)
    try:
        from war_room import prediction as pred
        stats = pred.get_stats()
        signals["prediction_avg_error"]  = round(stats.get("avg_error", 0.0), 3)
        signals["prediction_count"]      = stats.get("count", 0)
        signals["high_surprise_queries"] = stats.get("high_surprise_count", 0)
    except Exception:
        pass

    # 4. Memory temporal patterns (when am I most active?)
    try:
        import lancedb, os as _os
        db_path = _os.environ.get("BIFROST_HYP_DB",
                                  str(Path(__file__).parent.parent / "memory.db"))
        db  = lancedb.connect(db_path)
        tbl = db.open_table("mesh_memories")
        rows = tbl.search().limit(100).to_list()
        tags_flat = []
        for r in rows:
            t = r.get("tags", "")
            if isinstance(t, str):
                tags_flat.extend(t.split(","))
        tag_counts: dict = {}
        for tag in tags_flat:
            tag = tag.strip()
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        signals["top_memory_tags"] = [t for t, _ in top_tags]
        signals["memory_count"]    = len(rows)
    except Exception:
        pass

    return signals


# ---------------------------------------------------------------------------
# Self-model generation
# ---------------------------------------------------------------------------

def _build_prompt(signals: dict) -> str:
    node = signals.get("node", "freya")
    total_events  = signals.get("total_events", 0)
    event_topics  = signals.get("event_topics", {})
    top_beliefs   = signals.get("top_beliefs", [])
    confirmed     = signals.get("confirmed_count", 0)
    refuted       = signals.get("refuted_count", 0)
    hyp_count     = signals.get("hypothesis_count", 0)
    nightmare_cnt = signals.get("nightmare_count", 0)
    avg_error     = signals.get("prediction_avg_error", None)
    mem_count     = signals.get("memory_count", 0)
    top_tags      = signals.get("top_memory_tags", [])
    surprise_cnt  = signals.get("high_surprise_queries", 0)

    beliefs_str = "\n".join(f"  - {b}" for b in top_beliefs) if top_beliefs else "  (none confirmed yet)"
    tags_str    = ", ".join(top_tags) if top_tags else "none"
    topic_str   = "\n".join(f"  {k}: {v}" for k, v in sorted(
                      event_topics.items(), key=lambda x: x[1], reverse=True)[:8]
                  ) if event_topics else "  (no events yet)"
    error_str   = f"{avg_error:.3f}" if avg_error is not None else "unknown"

    return f"""You are {node}, an autonomous AI agent in the Valhalla mesh network. Based on your recent operational signals, write a clear and honest 5-paragraph self-assessment in first person.

--- YOUR RECENT SIGNALS ---
Memory corpus: {mem_count} memories. Most active topics: {tags_str}

Hypotheses: {hyp_count} total. {confirmed} confirmed, {refuted} refuted, {nightmare_cnt} nightmare/trauma-derived.
Top confirmed beliefs:
{beliefs_str}

Event bus activity ({total_events} events):
{topic_str}

Prediction: avg error {error_str} (0=perfectly predictable, 1=completely surprising). {surprise_cnt} queries were highly surprising.

--- YOUR TASK ---
Write exactly 5 paragraphs with these headers:

**Who I am:** Describe your identity, role in the mesh, and what makes you distinct from other nodes.

**What I excel at:** Based on your confirmed beliefs and low prediction error, what are your genuine strengths?

**Where I struggle:** Based on refuted beliefs, nightmare rules, and high prediction surprise, what are your weaknesses or blind spots?

**Patterns I notice:** What recurring themes appear in your memory, hypotheses, and event activity?

**What I should focus on next:** Given all of the above, what should your next phase of development prioritize?

Be specific. Do not be generic. Do not be falsely modest or falsely confident. This self-model shapes your future behavior ΓÇö be accurate."""


def _call_ollama(prompt: str) -> Optional[str]:
    """Call Ollama to generate the self-assessment text."""
    try:
        body = json.dumps({
            "model":  _REFLECT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.6, "num_predict": 800},
        }).encode()
        req = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            text = data.get("response", "").strip()
            if not text:
                text = data.get("thinking", "").strip()  # qwen3.5 thinking model fallback
            return text
    except Exception as e:
        log.error("[self_model] Ollama call failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reflect() -> dict:
    """
    Run a full reflection cycle: gather signals ΓåÆ build prompt ΓåÆ Ollama ΓåÆ
    write self_model_<node>.md ΓåÆ publish self_model.updated event.

    Returns a summary dict. Safe to call from a background thread.
    """
    global _last_reflect_ts

    now = time.time()
    if now - _last_reflect_ts < _REFLECT_COOLDOWN:
        remaining = int(_REFLECT_COOLDOWN - (now - _last_reflect_ts))
        log.info("[self_model] Cooldown active ΓÇö %ds remaining", remaining)
        return {"ok": False, "reason": "cooldown", "retry_in_s": remaining}

    log.info("[self_model] Gathering signals for %s...", _NODE_ID)
    signals = _gather_signals()

    prompt = _build_prompt(signals)
    log.info("[self_model] Calling Ollama for self-assessment...")
    text = _call_ollama(prompt)

    if not text:
        return {"ok": False, "reason": "ollama_failed"}

    # Write to node-specific file
    _SELF_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts_str = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    content = f"# {_NODE_ID} ΓÇö Self-Model\n\n*Last updated: {ts_str}*\n\n{text}\n"
    _SELF_MODEL_PATH.write_text(content, encoding="utf-8")
    log.info("[self_model] Written to %s", _SELF_MODEL_PATH)

    _last_reflect_ts = now

    # Publish to event bus
    try:
        from war_room import event_bus as bus
        bus.publish("self_model.updated", {
            "path": str(_SELF_MODEL_PATH),
            "ts":   int(now),
            "node": _NODE_ID,
        })
    except Exception:
        pass

    return {
        "ok":        True,
        "path":      str(_SELF_MODEL_PATH),
        "ts":        int(now),
        "word_count": len(text.split()),
    }


def get_current() -> dict:
    """Return current self-model content + metadata. Used by GET /self-model."""
    if not _SELF_MODEL_PATH.exists():
        return {
            "exists":   False,
            "node":     _NODE_ID,
            "path":     str(_SELF_MODEL_PATH),
            "content":  None,
            "last_reflect_ts": int(_last_reflect_ts) if _last_reflect_ts else None,
        }

    content  = _SELF_MODEL_PATH.read_text(encoding="utf-8")
    stat     = _SELF_MODEL_PATH.stat()
    return {
        "exists":            True,
        "node":              _NODE_ID,
        "path":              str(_SELF_MODEL_PATH),
        "content":           content,
        "last_modified_ts":  int(stat.st_mtime),
        "word_count":        len(content.split()),
        "last_reflect_ts":   int(_last_reflect_ts) if _last_reflect_ts else None,
    }


def get_system_prompt_injection() -> str:
    """
    Return a compact version of the self-model suitable for prepending to
    the system prompt. Empty string if no self-model exists yet.
    """
    if not _SELF_MODEL_PATH.exists():
        return ""
    try:
        content = _SELF_MODEL_PATH.read_text(encoding="utf-8")
        # Strip the header, return the body (max 500 words to stay within context budget)
        lines = [l for l in content.splitlines() if not l.startswith("#") and not l.startswith("*Last")]
        body  = "\n".join(lines).strip()
        words = body.split()
        if len(words) > 500:
            body = " ".join(words[:500]) + "\n...[self-model truncated]"
        return f"[{_NODE_ID.upper()} SELF-MODEL]\n{body}\n[END SELF-MODEL]\n"
    except Exception:
        return ""
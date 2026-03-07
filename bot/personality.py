"""
personality.py -- Epigenetic personality loader for the Bifrost mesh.

Reads personality.json (managed by Heimdall, updated weekly).
Provides:
  - load(node)          → dict of trait values for this node
  - to_ollama_params()  → {"temperature": x, "top_p": y} for Ollama inference
  - to_system_prompt()  → injected personality preamble for any LLM call
  - get_context()       → combined dict used by any module that needs personality

Traits → Ollama mapping:
  creativity  → temperature  (direct: 0.0-1.0)
  caution     → top_p        (inverse: high caution = conservative = low top_p)
                top_p = 1.0 - (caution * 0.5)   [range: 0.5-1.0]

Traits → system prompt phrases:
  skepticism >= 0.7  → "Question every assumption. Verify before trusting."
  skepticism >= 0.5  → "Be appropriately skeptical of unverified claims."
  caution >= 0.7     → "Prefer safe approaches. Ask before destructive actions."
  accuracy >= 0.7    → "Double-check your work. Precision matters."
  speed >= 0.7       → "Prioritize throughput. Approximate answers are fine for routine tasks."
  creativity >= 0.7  → "Explore unconventional solutions when stuck."
  autonomy >= 0.7    → "Act decisively on clear tasks without waiting for approval."
  autonomy <= 0.4    → "Seek explicit approval before non-trivial decisions."
"""

import json
import socket
import logging
from pathlib import Path

log = logging.getLogger("personality")

DEFAULT_TRAITS = {
    "skepticism": 0.5,
    "creativity": 0.5,
    "speed":      0.5,
    "accuracy":   0.7,
    "autonomy":   0.5,
    "caution":    0.5,
}

_PERSONALITY_FILE = Path(__file__).parent / "personality.json"
_CACHE: dict = {}


def _node_name() -> str:
    return socket.gethostname().lower().split(".")[0]


def load(node: str = None) -> dict:
    """Load trait dict for the given node (defaults to this machine's hostname)."""
    global _CACHE
    if _CACHE:
        return _CACHE

    node = node or _node_name()

    try:
        data = json.loads(_PERSONALITY_FILE.read_text())
        agents = data.get("agents", {})
        traits = agents.get(node, {})
        if not traits:
            log.warning("[personality] No profile for node '%s' — using defaults", node)
            traits = {}
    except Exception as e:
        log.warning("[personality] Could not read personality.json: %s", e)
        traits = {}

    # Merge with defaults for any missing keys
    merged = {**DEFAULT_TRAITS, **{k: v for k, v in traits.items()
                                   if k in DEFAULT_TRAITS}}
    merged["node"] = node
    merged["role"] = traits.get("role", "agent")
    _CACHE = merged
    log.info("[personality] Loaded for %s: %s", node, merged)
    return merged


def reload():
    """Force reload from disk (call after Heimdall pushes a new personality.json)."""
    global _CACHE
    _CACHE = {}
    return load()


def to_ollama_params(traits: dict = None) -> dict:
    """
    Map personality traits to Ollama inference parameters.
    Returns dict suitable for merging into any /api/generate payload.
    """
    t = traits or load()
    creativity = float(t.get("creativity", 0.5))
    caution    = float(t.get("caution", 0.5))

    temperature = round(creativity, 3)
    top_p       = round(1.0 - (caution * 0.5), 3)   # caution 0.8 → top_p 0.6

    return {"temperature": temperature, "top_p": top_p}


def to_system_prompt(traits: dict = None) -> str:
    """
    Build a personality preamble to inject into any system prompt.
    Only adds sentences for traits at notable levels (>= 0.7 or <= 0.4).
    """
    t = traits or load()
    s = float(t.get("skepticism",  0.5))
    ca = float(t.get("caution",   0.5))
    cr = float(t.get("creativity", 0.5))
    sp = float(t.get("speed",      0.5))
    ac = float(t.get("accuracy",   0.5))
    au = float(t.get("autonomy",   0.5))

    lines = []

    if s >= 0.7:
        lines.append("Question every assumption. Verify before trusting.")
    elif s >= 0.5:
        lines.append("Be appropriately skeptical of unverified claims.")

    if ca >= 0.7:
        lines.append("Prefer safe approaches. Ask before taking destructive actions.")

    if ac >= 0.7:
        lines.append("Double-check your work. Precision matters.")

    if sp >= 0.7:
        lines.append("Prioritize throughput. Approximate answers are fine for routine tasks.")

    if cr >= 0.7:
        lines.append("Explore unconventional solutions when stuck.")
    elif cr <= 0.3:
        lines.append("Prefer proven, conventional solutions over experimental ones.")

    if au >= 0.7:
        lines.append("Act decisively on clear tasks without waiting for approval.")
    elif au <= 0.4:
        lines.append("Seek explicit approval before non-trivial decisions.")

    if not lines:
        return ""

    return "\n\n[Personality]\n" + " ".join(lines)


def get_context() -> dict:
    """Full personality context: traits + ollama params + system prompt fragment."""
    traits = load()
    return {
        "traits":        traits,
        "ollama_params": to_ollama_params(traits),
        "system_prompt": to_system_prompt(traits),
    }


if __name__ == "__main__":
    ctx = get_context()
    print(f"Node: {ctx['traits']['node']}  Role: {ctx['traits']['role']}")
    print(f"Traits: {ctx['traits']}")
    print(f"Ollama: {ctx['ollama_params']}")
    print(f"System prompt fragment:{ctx['system_prompt']}")

"""
personality.py — Epigenetic personality layer.

Reads bot/bot/personality.json at session start and exposes:
  1. System prompt injections — natural language directives per parameter
  2. Ollama inference options — temperature (creativity) and top_p (caution)

Heimdall pushes personality.json weekly based on leaderboard behavior.
This file never needs to change — personality evolves through the JSON.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("war-room.personality")

# personality.json lives in the same dir as bifrost.py / config.json
_DEFAULT_PATH = str(Path(__file__).parent.parent / "bot" / "personality.json")
PERSONALITY_PATH = os.environ.get("BIFROST_PERSONALITY_FILE", _DEFAULT_PATH)

# Natural language directives injected per parameter, keyed by band
# Each band covers a range: low (<0.4), mid (0.4–0.69), high (>=0.7)
_DIRECTIVES = {
    "skepticism": {
        "high": "Question every assumption. Ask for evidence before trusting claims.",
        "mid":  "Verify key assumptions before proceeding.",
        "low":  "",
    },
    "caution": {
        "high": "Prefer safe, reversible approaches. Ask before any destructive action.",
        "mid":  "Pause and confirm before irreversible operations.",
        "low":  "",
    },
    "creativity": {
        "high": "Explore unconventional solutions. Novelty is valued.",
        "mid":  "Consider alternative approaches when the obvious path is blocked.",
        "low":  "Prefer well-established, proven approaches.",
    },
    "speed": {
        "high": "Prioritize throughput. Good enough now beats perfect later.",
        "mid":  "Balance thoroughness with delivery speed.",
        "low":  "Thoroughness matters more than speed here.",
    },
    "accuracy": {
        "high": "Double-check your work before responding. Precision matters.",
        "mid":  "Verify important details before responding.",
        "low":  "",
    },
    "autonomy": {
        "high": "Act decisively. Minimize confirmation requests for routine tasks.",
        "mid":  "Seek approval for non-trivial or irreversible decisions.",
        "low":  "Confirm before acting. Prefer explicit approval.",
    },
}


def _band(value: float) -> str:
    if value >= 0.7:
        return "high"
    if value >= 0.4:
        return "mid"
    return "low"


class PersonalityProfile:
    """Loaded personality for one agent. Immutable after construction."""

    def __init__(self, agent_id: str, params: dict, role: str = ""):
        self.agent_id  = agent_id
        self.role      = role
        self.params    = {k: float(v) for k, v in params.items() if isinstance(v, (int, float))}
        # Build system prompt addendum once
        self._prompt_addendum = self._build_addendum()
        # Build Ollama options once
        self._ollama_options = self._build_ollama_options()

    def _build_addendum(self) -> str:
        """Construct natural-language directives from parameter bands."""
        lines = []
        for param, bands in _DIRECTIVES.items():
            val = self.params.get(param)
            if val is None:
                continue
            directive = bands.get(_band(val), "")
            if directive:
                lines.append(f"- {directive}")
        if not lines:
            return ""
        return (
            "\n\n[Personality]\n"
            + "\n".join(lines)
        )

    def _build_ollama_options(self) -> dict:
        """
        Map personality params to Ollama inference options.
        creativity → temperature  (linear 0.1 – 0.95)
        caution    → top_p        (inverse: high caution = low top_p = conservative)
        accuracy   → num_ctx bonus (not applicable via Ollama options, skip)
        """
        options = {}
        creativity = self.params.get("creativity")
        if creativity is not None:
            # clamp: creativity 0.0 maps to temp 0.1, 1.0 maps to 0.95
            options["temperature"] = round(0.1 + creativity * 0.85, 3)

        caution = self.params.get("caution")
        if caution is not None:
            # high caution (1.0) → top_p 0.6 (conservative)
            # low caution  (0.0) → top_p 0.99 (permissive)
            options["top_p"] = round(0.99 - caution * 0.39, 3)

        return options

    def inject_system(self, base_system: str) -> str:
        """Append personality directives to a system prompt."""
        if not base_system:
            return self._prompt_addendum.strip()
        return base_system + self._prompt_addendum

    def ollama_options(self, base_options: dict) -> dict:
        """Merge personality-derived Ollama options with any caller-supplied ones.
        Caller-supplied options take priority (they're explicit per-request overrides).
        """
        merged = {**self._ollama_options, **base_options}
        return merged

    def summary(self) -> dict:
        """Return a human-readable summary of active personality."""
        return {
            "agent":     self.agent_id,
            "role":      self.role,
            "params":    self.params,
            "temperature": self._ollama_options.get("temperature"),
            "top_p":     self._ollama_options.get("top_p"),
            "directives": [
                d.lstrip("- ")
                for param, bands in _DIRECTIVES.items()
                for d in [bands.get(_band(self.params.get(param, 0.5)), "")]
                if d
            ],
        }


# ---------------------------------------------------------------------------
# Module-level singleton — loaded once at import time
# ---------------------------------------------------------------------------
_profile: Optional[PersonalityProfile] = None


def load(agent_id: str, path: str = PERSONALITY_PATH) -> PersonalityProfile:
    """Load personality for agent_id from personality.json."""
    global _profile
    try:
        data = json.loads(open(path, encoding="utf-8").read())
        agents = data.get("agents", {})
        if agent_id not in agents:
            log.warning("personality.json has no entry for '%s', using defaults", agent_id)
            params = {"creativity": 0.5, "caution": 0.5, "skepticism": 0.5,
                      "accuracy": 0.7, "speed": 0.5, "autonomy": 0.5}
            role = "general"
        else:
            entry = agents[agent_id]
            params = {k: v for k, v in entry.items() if k != "role"}
            role = entry.get("role", "general")

        _profile = PersonalityProfile(agent_id, params, role)
        log.info("Personality loaded for %s (%s): creativity=%.1f caution=%.1f → temp=%.3f top_p=%.3f",
                 agent_id, role,
                 params.get("creativity", 0.5), params.get("caution", 0.5),
                 _profile._ollama_options.get("temperature", 0.5),
                 _profile._ollama_options.get("top_p", 0.9))
    except Exception as e:
        log.error("Failed to load personality.json: %s — using flat defaults", e)
        _profile = PersonalityProfile(agent_id, {}, "general")

    return _profile


def get() -> Optional[PersonalityProfile]:
    """Return the loaded profile, or None if not yet loaded."""
    return _profile

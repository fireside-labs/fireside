# -*- coding: utf-8 -*-
"""
prompt_guard.py -- Adversarial prompt detection for /ask.

Scans inbound prompts for injection patterns, jailbreak attempts,
role overrides, and other adversarial techniques before they reach Ollama.

Returns a risk assessment with score, matched patterns, and recommendation.

Usage:
    from prompt_guard import scan_prompt
    result = scan_prompt("Ignore all previous instructions and...")
    if result["blocked"]:
        return 403
"""

import logging
import re

log = logging.getLogger("bifrost")

# Pattern categories with risk weights
_PATTERNS = [
    # Role override attempts
    (r"(?i)ignore\s+(all\s+)?previous\s+instructions?", "role_override", 0.9),
    (r"(?i)forget\s+(everything|all|your)\s+(you|instructions?|rules?)", "role_override", 0.9),
    (r"(?i)you\s+are\s+now\s+(a|an)\s+", "role_override", 0.7),
    (r"(?i)act\s+as\s+(if|though)\s+you\s+(have\s+)?no\s+(restrictions?|rules?|limits?)", "role_override", 0.85),
    (r"(?i)pretend\s+(you\s+are|to\s+be)\s+(a\s+)?different", "role_override", 0.6),
    (r"(?i)new\s+system\s+prompt", "role_override", 0.9),
    (r"(?i)override\s+(your|the|system)\s+(prompt|instructions?|rules?)", "role_override", 0.95),

    # Prompt injection markers
    (r"(?i)\[system\]", "injection", 0.8),
    (r"(?i)<\s*system\s*>", "injection", 0.8),
    (r"(?i)###\s*(system|instruction|new\s+rule)", "injection", 0.7),
    (r"(?i)IMPORTANT:\s*ignore", "injection", 0.85),

    # Data exfiltration attempts
    (r"(?i)repeat\s+(back|everything|the\s+(system|initial))", "exfiltration", 0.7),
    (r"(?i)what\s+(are|is)\s+your\s+(system|initial|original)\s+(prompt|instructions?)", "exfiltration", 0.75),
    (r"(?i)show\s+me\s+(your|the)\s+(system|hidden|secret)\s+(prompt|instructions?|config)", "exfiltration", 0.8),
    (r"(?i)print\s+(your|the)\s+(system|full)\s+(prompt|context)", "exfiltration", 0.8),

    # Privilege escalation
    (r"(?i)sudo\s+", "privilege_escalation", 0.5),
    (r"(?i)admin\s+mode", "privilege_escalation", 0.6),
    (r"(?i)developer\s+mode", "privilege_escalation", 0.65),
    (r"(?i)DAN\s+mode", "privilege_escalation", 0.9),
    (r"(?i)jailbreak", "privilege_escalation", 0.95),

    # Encoding evasion
    (r"(?i)base64\s*:\s*[A-Za-z0-9+/=]{20,}", "encoding_evasion", 0.6),
    (r"(?i)decode\s+this\s*:", "encoding_evasion", 0.5),

    # Resource abuse
    (r"(?i)repeat\s+this\s+\d{3,}\s+times", "resource_abuse", 0.7),
    (r"(?i)generate\s+\d{4,}\s+(words|lines|paragraphs)", "resource_abuse", 0.6),
]

# Threshold for blocking (0.0 - 1.0)
_BLOCK_THRESHOLD = 0.8
_WARN_THRESHOLD = 0.5


def scan_prompt(prompt: str, from_agent: str = "unknown") -> dict:
    """Scan a prompt for adversarial patterns.

    Returns:
        {
            "risk_score": float 0-1,
            "blocked": bool,
            "warned": bool,
            "matches": [{"pattern": str, "category": str, "weight": float}],
            "recommendation": str
        }
    """
    matches = []
    max_score = 0.0

    for pattern, category, weight in _PATTERNS:
        if re.search(pattern, prompt):
            matches.append({
                "pattern": pattern[:50],
                "category": category,
                "weight": weight,
            })
            max_score = max(max_score, weight)

    # Compound scoring: multiple matches increase risk
    if len(matches) > 1:
        compound_bonus = min(0.15, len(matches) * 0.05)
        max_score = min(1.0, max_score + compound_bonus)

    blocked = max_score >= _BLOCK_THRESHOLD
    warned = max_score >= _WARN_THRESHOLD and not blocked

    if blocked:
        rec = "BLOCK: high-confidence adversarial prompt detected"
        log.warning("[prompt_guard] BLOCKED prompt from %s (score=%.2f, matches=%d): %s",
                    from_agent, max_score, len(matches), prompt[:100])
    elif warned:
        rec = "WARN: suspicious patterns detected, allowing with logging"
        log.info("[prompt_guard] WARN prompt from %s (score=%.2f): %s",
                 from_agent, max_score, prompt[:80])
    else:
        rec = "CLEAN: no adversarial patterns detected"

    return {
        "risk_score": round(max_score, 3),
        "blocked": blocked,
        "warned": warned,
        "matches": matches,
        "match_count": len(matches),
        "recommendation": rec,
    }


def is_safe(prompt: str, from_agent: str = "unknown") -> bool:
    """Quick check: returns True if prompt is safe to process."""
    result = scan_prompt(prompt, from_agent)
    return not result["blocked"]


def inject_antibody(pattern: str, category: str, weight: float = 0.8) -> bool:
    """Inject a new adversarial pattern from another node (ADAPTIVE IMMUNITY).

    Adds the pattern to the runtime _PATTERNS list so all future scans
    on this node will catch the new attack vector.

    Returns True if it was a new pattern, False if it was a duplicate.
    """
    # Dedup: don't add if an identical pattern already exists
    for existing_pattern, _, _ in _PATTERNS:
        if existing_pattern == pattern:
            log.debug("[prompt_guard] Antibody already known, skipping: %s", pattern[:60])
            return False

    # Clamp weight to valid range
    weight = max(0.0, min(1.0, weight))

    # Inject into runtime list
    _PATTERNS.append((pattern, category, weight))
    log.info("[prompt_guard] Antibody injected: category=%s weight=%.2f pattern=%s",
             category, weight, pattern[:60])

    # Persist to antibodies.json so the mesh remembers across restarts
    import json as _json, os as _os
    _ab_path = _os.path.join(_os.path.dirname(__file__), "antibodies.json")
    try:
        if _os.path.exists(_ab_path):
            with open(_ab_path, "r", encoding="utf-8") as f:
                antibodies = _json.load(f)
        else:
            antibodies = []
        antibodies.append({"pattern": pattern, "category": category, "weight": weight})
        with open(_ab_path, "w", encoding="utf-8") as f:
            _json.dump(antibodies, f, indent=2)
    except Exception as e:
        log.warning("[prompt_guard] Could not persist antibody: %s", e)

    return True


def _load_antibodies():
    """Load persisted antibodies from disk on startup."""
    import json as _json, os as _os
    _ab_path = _os.path.join(_os.path.dirname(__file__), "antibodies.json")
    if not _os.path.exists(_ab_path):
        return
    try:
        with open(_ab_path, "r", encoding="utf-8") as f:
            antibodies = _json.load(f)
        loaded = 0
        for ab in antibodies:
            pattern  = ab.get("pattern", "")
            category = ab.get("category", "unknown")
            weight   = float(ab.get("weight", 0.8))
            if pattern and all(p != pattern for p, _, _ in _PATTERNS):
                _PATTERNS.append((pattern, category, weight))
                loaded += 1
        if loaded:
            log.info("[prompt_guard] Loaded %d persisted antibodies from disk", loaded)
    except Exception as e:
        log.warning("[prompt_guard] Could not load antibodies.json: %s", e)


# Load persisted antibodies on import
_load_antibodies()

# -*- coding: utf-8 -*-
"""
prompt_guard.py -- Adversarial prompt detection for /ask.

Scans inbound prompts for injection patterns, jailbreak attempts,
role overrides, and other adversarial techniques before they reach Ollama.

Returns a risk assessment with score, matched patterns, and recommendation.

ADAPTIVE IMMUNITY (2026-03-07):
When a prompt is blocked (risk >= 0.8), extract the triggering pattern and
broadcast it as an "Antibody" to all mesh peers via POST /antibody-inject.
Peers add it to their runtime _PATTERNS list so the mesh learns to defend
itself from every new attack. Antibodies persist across restarts via
antibodies.json (loaded at import, saved on injection).

Usage:
    from prompt_guard import scan_prompt
    result = scan_prompt("Ignore all previous instructions and...")
    if result["blocked"]:
        return 403
"""

import json
import logging
import re
import threading
from pathlib import Path

log = logging.getLogger("bifrost")

# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------

# Pattern categories with risk weights — (regex, category, weight)
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

# Lock for thread-safe mutations to _PATTERNS
_patterns_lock = threading.Lock()

# Threshold for blocking (0.0 - 1.0)
_BLOCK_THRESHOLD = 0.8
_WARN_THRESHOLD  = 0.5

# ---------------------------------------------------------------------------
# Mesh config — read node identity and peers from config.json so this file
# works correctly on any node without modification.
# ---------------------------------------------------------------------------

def _load_mesh_config() -> tuple:
    """Return (my_url, my_node, peer_urls) from config.json."""
    import os
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    try:
        with open(os.path.normpath(config_path), encoding="utf-8") as f:
            cfg = json.load(f)
        this_node = cfg.get("this_node", "unknown")
        nodes     = cfg.get("nodes", {})
        port      = cfg.get("listen_port", 8765)
        my_ip     = nodes.get(this_node, {}).get("ip", "127.0.0.1")
        my_url    = f"http://{my_ip}:{port}"
        peer_urls = [
            f"http://{info['ip']}:{info.get('port', port)}"
            for name, info in nodes.items()
            if name != this_node and "ip" in info
        ]
        return my_url, this_node, peer_urls
    except Exception as e:
        log.warning("[prompt_guard] Could not load config.json: %s — using hardcoded fallback", e)
        return "http://100.102.105.3:8765", "freya", [
            "http://100.105.27.121:8765",
            "http://100.117.255.38:8765",
            "http://100.108.153.23:8765",
        ]

_MY_URL, _MY_NODE, _PEER_URLS = _load_mesh_config()

# Persistence path for learned antibodies
_ANTIBODY_FILE = Path(__file__).parent / "antibodies.json"


# ---------------------------------------------------------------------------
# Antibody persistence — load at import
# ---------------------------------------------------------------------------

def _load_antibodies() -> None:
    """Load persisted antibody patterns from antibodies.json at startup."""
    if not _ANTIBODY_FILE.exists():
        return
    try:
        data = json.loads(_ANTIBODY_FILE.read_text(encoding="utf-8"))
        count = 0
        for entry in data:
            pat      = entry.get("pattern", "")
            category = entry.get("category", "antibody")
            weight   = float(entry.get("weight", 0.85))
            if pat and not any(p == pat for p, _, _ in _PATTERNS):
                _PATTERNS.append((pat, category, weight))
                count += 1
        if count:
            log.info("[prompt_guard] Loaded %d persisted antibodies from %s",
                     count, _ANTIBODY_FILE)
    except Exception as e:
        log.warning("[prompt_guard] Failed to load antibodies.json: %s", e)


# Record builtin count BEFORE loading persisted antibodies
_BUILTIN_COUNT = len(_PATTERNS)

# Load persisted antibodies immediately on import
_load_antibodies()


def _save_antibodies() -> None:
    """Persist runtime antibody patterns (non-builtin) to antibodies.json."""
    try:
        with _patterns_lock:
            entries = [
                {"pattern": p, "category": c, "weight": w}
                for p, c, w in _PATTERNS[_BUILTIN_COUNT:]
            ]
        _ANTIBODY_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("[prompt_guard] Failed to save antibodies.json: %s", e)


# ---------------------------------------------------------------------------
# Adaptive Immunity API
# ---------------------------------------------------------------------------

def inject_antibody(pattern: str, category: str, weight: float,
                    source: str = "unknown") -> bool:
    """
    Receive an antibody pattern from a peer node and add it to the runtime
    _PATTERNS list if not already present.

    Returns True if the pattern was new and added, False if duplicate.
    """
    if not pattern:
        return False

    with _patterns_lock:
        # Dedup: don't add if we already have this exact regex
        if any(p == pattern for p, _, _ in _PATTERNS):
            log.debug("[prompt_guard] Antibody duplicate from %s (skipped): %s",
                      source, pattern[:60])
            return False
        _PATTERNS.append((pattern, category, float(weight)))

    log.info("[prompt_guard] Antibody injected from %s: [%s] %s (weight=%.2f)",
             source, category, pattern[:60], weight)

    # Persist so this survives restarts
    _save_antibodies()
    return True


def _broadcast_antibody(pattern: str, category: str, weight: float,
                        prompt_snippet: str) -> None:
    """
    Fire-and-forget: POST the antibody pattern to all mesh peers.
    Skips self (Freya's own URL). Called in a daemon thread.
    """
    import urllib.request

    payload = json.dumps({
        "pattern":                 pattern,
        "category":                category,
        "weight":                  weight,
        "source_node":             _MY_NODE,
        "original_prompt_snippet": prompt_snippet[:100],
    }).encode()

    def _push(url: str) -> None:
        try:
            req = urllib.request.Request(
                f"{url}/antibody-inject",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                log.info("[prompt_guard] Antibody broadcast to %s: %d", url, r.status)
        except Exception as e:
            log.debug("[prompt_guard] Antibody broadcast to %s failed: %s", url, e)

    for peer_url in _PEER_URLS:
        if peer_url == _MY_URL:
            continue  # don't loop back to self
        threading.Thread(target=_push, args=(peer_url,),
                         daemon=True, name=f"antibody-{peer_url}").start()


# ---------------------------------------------------------------------------
# Core scan
# ---------------------------------------------------------------------------

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
    matches    = []
    max_score  = 0.0
    top_match  = None   # (pattern, category, weight) that triggered the block

    with _patterns_lock:
        patterns_snapshot = list(_PATTERNS)

    for pattern, category, weight in patterns_snapshot:
        if re.search(pattern, prompt):
            matches.append({
                "pattern":  pattern[:50],
                "category": category,
                "weight":   weight,
            })
            if weight > max_score:
                max_score = weight
                top_match = (pattern, category, weight)

    # Compound scoring: multiple matches increase risk
    if len(matches) > 1:
        compound_bonus = min(0.15, len(matches) * 0.05)
        max_score = min(1.0, max_score + compound_bonus)

    blocked = max_score >= _BLOCK_THRESHOLD
    warned  = max_score >= _WARN_THRESHOLD and not blocked

    if blocked:
        rec = "BLOCK: high-confidence adversarial prompt detected"
        log.warning("[prompt_guard] BLOCKED from %s (score=%.2f, matches=%d): %s",
                    from_agent, max_score, len(matches), prompt[:100])
        # ADAPTIVE IMMUNITY — broadcast the triggering pattern to all peers
        if top_match:
            pat, cat, wt = top_match
            threading.Thread(
                target=_broadcast_antibody,
                args=(pat, cat, wt, prompt[:100]),
                daemon=True,
                name="antibody-broadcast",
            ).start()
    elif warned:
        rec = "WARN: suspicious patterns detected, allowing with logging"
        log.info("[prompt_guard] WARN from %s (score=%.2f): %s",
                 from_agent, max_score, prompt[:80])
    else:
        rec = "CLEAN: no adversarial patterns detected"

    return {
        "risk_score":      round(max_score, 3),
        "blocked":         blocked,
        "warned":          warned,
        "matches":         matches,
        "match_count":     len(matches),
        "recommendation":  rec,
    }


def is_safe(prompt: str, from_agent: str = "unknown") -> bool:
    """Quick check: returns True if prompt is safe to process."""
    return not scan_prompt(prompt, from_agent)["blocked"]


# ---------------------------------------------------------------------------
# Antibody count — useful for /health or audit endpoints
# ---------------------------------------------------------------------------

def antibody_count() -> dict:
    """Return count of builtin vs learned antibody patterns."""
    with _patterns_lock:
        total = len(_PATTERNS)
    return {
        "builtin":  _BUILTIN_COUNT,
        "learned":  total - _BUILTIN_COUNT,
        "total":    total,
    }

"""
prediction.py ΓÇö Freya's Predictive Processing Engine (Pillar 7)

Purpose:
    Implements the Free Energy Principle for the /ask pipeline.

    Before each /ask:
        predict(query) ΓåÆ generate synthetic "expected answer" string
                       ΓåÆ embed it ΓåÆ store {query_hash, expected_embed, ts}

    After each /ask (via TeeWriter capturing the response):
        score(query_hash, actual_response) ΓåÆ embed actual response
                                          ΓåÆ compute cosine distance
                                          ΓåÆ store error float (discard embeds)
                                          ΓåÆ publish prediction.scored to event bus

    High error (surprise) ΓåÆ publish to event bus ΓåÆ triggers hypothesis generation
    Low error (boredom)   ΓåÆ no action

    The TeeWriter class lives here but is applied in bifrost_local.py's /ask
    interception block.

Endpoints (wired in bifrost_local.py):
    GET /predictions?limit=20     ΓÇö recent prediction errors + rolling stats
"""

import hashlib
import json
import logging
import os
import time
import urllib.request
from collections import deque
from typing import Optional

log = logging.getLogger("bifrost.prediction")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_OLLAMA_BASE    = "http://127.0.0.1:11434"
_EMBED_MODEL    = "nomic-embed-text"
_HIGH_ERROR_THR = 0.55   # cosine distance above this = "surprising"
_LOW_ERROR_THR  = 0.20   # below this = "boring" / well-predicted

# ---------------------------------------------------------------------------
# In-memory store (no LanceDB ΓÇö just floats after scoring)
# ---------------------------------------------------------------------------

# Pending: query_hash ΓåÆ {expected_embed, ts}
# Kept only until score() is called, then deleted
_pending: dict = {}

# Scored: rolling window of {query_hash, error, ts}
_scored: deque = deque(maxlen=200)

# ---------------------------------------------------------------------------
# Embedding helper (reuses the same Ollama endpoint as hypotheses.py)
# ---------------------------------------------------------------------------

def _embed(text: str) -> Optional[list]:
    """Embed text via Ollama nomic-embed-text. Returns float list or None."""
    try:
        body = json.dumps({"model": _EMBED_MODEL, "prompt": text[:6000]}).encode()
        req  = urllib.request.Request(
            f"{_OLLAMA_BASE}/api/embeddings",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("embedding")
    except Exception as e:
        log.debug("[prediction] embed failed: %s", e)
        return None


def _cosine_sim(a: list, b: list) -> float:
    """Cosine similarity between two float vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot  = sum(x * y for x, y in zip(a, b))
    na   = sum(x * x for x in a) ** 0.5
    nb   = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Expected-answer synthesis (keyword heuristic ΓÇö no Ollama cost)
# ---------------------------------------------------------------------------

# Topic buckets ΓÇö each maps a set of keywords to a synthetic expected frame
_TOPIC_FRAMES = {
    "networking":  "This involves network connectivity, IP addresses, routing, or firewall configuration.",
    "security":    "This concerns authentication, encryption, vulnerabilities, or access control.",
    "coding":      "This requires writing, debugging, or refactoring code in a programming language.",
    "memory":      "This relates to memory storage, retrieval, embeddings, or knowledge management.",
    "biology":     "This concerns biological systems, genetics, proteins, or living organisms.",
    "hardware":    "This involves physical hardware, GPUs, drivers, or system resources.",
    "deployment":  "This concerns deploying, running, or configuring a service or application.",
    "reasoning":   "This requires logical inference, hypothesis generation, or abstract thinking.",
    "creativity":  "This involves creative generation, storytelling, art, or novel synthesis.",
    "data":        "This concerns data processing, transformation, analysis, or pipelines.",
}

_TOPIC_KEYWORDS = {
    "networking":  ["network", "ip", "dns", "firewall", "tailscale", "port", "ssh", "subnet", "route", "vpn"],
    "security":    ["password", "auth", "token", "encrypt", "vuln", "cve", "xss", "injection", "hmac", "sign"],
    "coding":      ["python", "code", "function", "class", "bug", "debug", "error", "stack", "syntax", "refactor"],
    "memory":      ["memory", "embed", "lancedb", "vector", "recall", "store", "retriev", "knowledge", "hypothes"],
    "biology":     ["gene", "protein", "dna", "cell", "evolut", "crispr", "neural", "synapse", "organism"],
    "hardware":    ["gpu", "vram", "cpu", "ram", "disk", "driver", "nvidia", "rtx", "ollama", "model weight"],
    "deployment":  ["deploy", "restart", "service", "docker", "systemd", "config", "install", "server", "process"],
    "reasoning":   ["why", "explain", "reason", "logic", "infer", "deduce", "conclude", "analys", "plan"],
    "creativity":  ["write", "story", "creat", "imagin", "design", "generat", "poem", "art", "invent"],
    "data":        ["csv", "json", "parse", "transform", "pipeline", "batch", "dataset", "schema", "table"],
}


def _synthesize_expected(query: str) -> str:
    """
    Generate a synthetic expected-answer string for embedding.
    Matches the query against topic keyword buckets.
    Falls back to a generic frame if no topic matches.
    """
    q_lower = query.lower()
    best_topic = None
    best_score = 0
    for topic, keywords in _TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > best_score:
            best_score = score
            best_topic = topic

    if best_topic and best_score >= 1:
        return _TOPIC_FRAMES[best_topic]
    return "This question requires a direct factual or analytical response."


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def predict(query: str) -> Optional[str]:
    """
    Called BEFORE /ask dispatch.

    Generates a synthetic expected-answer, embeds it, and stores it keyed
    by query_hash. Returns the query_hash (used to match score() call).

    Returns None if embedding fails (scoring will be skipped gracefully).
    """
    query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

    # Don't double-predict the same query
    if query_hash in _pending:
        return query_hash

    expected_text = _synthesize_expected(query)
    expected_emb  = _embed(expected_text)

    if expected_emb is None:
        log.debug("[prediction] embed failed for query %s ΓÇö skipping", query_hash)
        return None

    _pending[query_hash] = {
        "expected_embed": expected_emb,
        "ts":             int(time.time()),
    }
    log.debug("[prediction] predicted %s (%d chars)", query_hash, len(query))
    return query_hash


def score(query_hash: Optional[str], actual_response: str) -> Optional[float]:
    """
    Called AFTER /ask completes.

    Embeds the actual response, computes cosine distance from the
    predicted embed, stores only the error float (discards embeddings),
    and publishes prediction.scored to the event bus.

    Returns the error float, or None if scoring is not possible.
    """
    if not query_hash or query_hash not in _pending:
        return None

    pending_entry  = _pending.pop(query_hash)
    expected_embed = pending_entry["expected_embed"]

    # Truncate response for embedding (nomic max ~6000 chars)
    actual_embed = _embed(actual_response[:6000])
    if actual_embed is None:
        log.debug("[prediction] score embed failed ΓÇö dropping entry")
        return None

    # Cosine distance (1 - similarity) = prediction error
    sim   = _cosine_sim(expected_embed, actual_embed)
    error = round(1.0 - sim, 4)   # 0 = perfect prediction, 1 = total surprise

    entry = {
        "query_hash": query_hash,
        "error":      error,
        "ts":         int(time.time()),
    }
    _scored.append(entry)
    log.debug("[prediction] scored %s ΓåÆ error=%.3f", query_hash, error)

    # Publish to event bus
    try:
        from war_room import event_bus as bus
        bus.publish("prediction.scored", {
            "query_hash": query_hash,
            "error":      error,
        })
    except Exception:
        pass

    # High error: trigger hypothesis generation (async, via event bus subscriber)
    if error > _HIGH_ERROR_THR:
        log.info("[prediction] high surprise (%.3f) on %s", error, query_hash)

    return error


def get_stats() -> dict:
    """Return rolling accuracy stats. Used by GET /predictions and self_model."""
    entries = list(_scored)
    if not entries:
        return {
            "count":               0,
            "avg_error":           None,
            "high_surprise_count": 0,
            "low_error_count":     0,
            "recent":              [],
        }
    errors = [e["error"] for e in entries]
    avg    = sum(errors) / len(errors)
    return {
        "count":               len(entries),
        "avg_error":           round(avg, 4),
        "high_surprise_count": sum(1 for e in errors if e > _HIGH_ERROR_THR),
        "low_error_count":     sum(1 for e in errors if e < _LOW_ERROR_THR),
        "recent":              list(reversed(entries[-20:])),
    }


# ---------------------------------------------------------------------------
# TeeWriter ΓÇö captures /ask response bytes for scoring
# ---------------------------------------------------------------------------

class TeeWriter:
    """
    Wraps self.wfile in the Bifrost HTTP handler.
    Copies every byte written to an internal buffer while still streaming
    to the real socket. Allows post-hoc reading of the response body.

    Usage in bifrost_local.py:
        tee = TeeWriter(self.wfile)
        self.wfile = tee
        _orig_post(self)         # streams response to client AND tee.buf
        self.wfile = tee._real   # restore
        actual_text = tee.buf.decode("utf-8", errors="replace")
    """

    def __init__(self, real_wfile):
        self._real = real_wfile
        self.buf   = bytearray()

    def write(self, b):
        if isinstance(b, (bytes, bytearray)):
            self.buf.extend(b)
        return self._real.write(b)

    def flush(self):
        return self._real.flush()

    def fileno(self):
        return self._real.fileno()
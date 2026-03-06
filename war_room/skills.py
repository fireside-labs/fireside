"""
skills.py — Freya's Skill Marketplace.

A living catalog of every capability the Freya mesh exposes.
Queryable by category to let agents (and humans) discover what's available.

GET /skills              → all skills
GET /skills?category=memory → filtered by category

Categories:
  memory        — Storage, retrieval, decay, health
  cognition     — Reasoning, analysis, insight generation
  coordination  — Multi-node orchestration, stigmergy, healing
  observability — Monitoring endpoints, dashboards, analytics
  intelligence  — Autonomous learning and adaptation systems
"""

import datetime

# ---------------------------------------------------------------------------
# Skill catalog — one entry per capability
# ---------------------------------------------------------------------------

_SKILLS = [
    # ── Memory ──────────────────────────────────────────────────────────────
    {
        "id":          "memory.upsert",
        "name":        "Memory Upsert",
        "category":    "memory",
        "description": "Write memories to the shared LanceDB semantic store with auto-embedding via Ollama.",
        "endpoint":    "POST /memory-sync",
        "status":      "active",
        "since":       "v1.0",
    },
    {
        "id":          "memory.query",
        "name":        "Semantic Memory Query",
        "category":    "memory",
        "description": "Vector similarity search over mesh memories with tag/node/importance filters.",
        "endpoint":    "GET /memory-query?q=",
        "status":      "active",
        "since":       "v1.0",
    },
    {
        "id":          "memory.health",
        "name":        "Memory Decay Dashboard",
        "category":    "memory",
        "description": "Full decay analysis: importance histogram, at-risk memories, valence breakdown, mesh health score 0-100.",
        "endpoint":    "GET /memory-health",
        "status":      "active",
        "since":       "v2.0",
    },
    {
        "id":          "memory.info",
        "name":        "Memory Info",
        "category":    "memory",
        "description": "Quick memory system status: count, DB path, embed model.",
        "endpoint":    "GET /memory-info",
        "status":      "active",
        "since":       "v1.0",
    },
    {
        "id":          "memory.contradiction",
        "name":        "Contradiction Detection",
        "category":    "memory",
        "description": "Flags conflicting memories on upsert using semantic similarity + valence gap + 34 keyword opposition pairs.",
        "endpoint":    "POST /memory-sync (response field: contradictions)",
        "status":      "active",
        "since":       "v2.1",
    },
    {
        "id":          "memory.seasonal",
        "name":        "Seasonal Memory Tagging",
        "category":    "memory",
        "description": "Auto-tags every memory with temporal context: time_of_day, day, season. Enables time-aware retrieval.",
        "endpoint":    "POST /memory-sync (auto-applied)",
        "status":      "active",
        "since":       "v2.2",
    },
    # ── Cognition ────────────────────────────────────────────────────────────
    {
        "id":          "cognition.valence",
        "name":        "Emotional Valence Detection",
        "category":    "cognition",
        "description": "Auto-detects positive/negative sentiment in memory content. Returns triumph/positive/neutral/negative/failure labels.",
        "endpoint":    "POST /memory-sync (auto-applied) + GET /memory-query (valence field)",
        "status":      "active",
        "since":       "v1.5",
    },
    {
        "id":          "cognition.attention",
        "name":        "Attention Gradient",
        "category":    "cognition",
        "description": "Tracks mesh cognitive focus from rolling 1-hour query window. Shannon entropy score + focus phrase.",
        "endpoint":    "GET /attention",
        "status":      "active",
        "since":       "v2.0",
    },
    {
        "id":          "cognition.plasticity",
        "name":        "Neural Plasticity Score",
        "category":    "cognition",
        "description": "0-100 learning rate synthesized from memory velocity, healing rate, contradiction churn, attention entropy, metabolic rate.",
        "endpoint":    "GET /plasticity",
        "status":      "active",
        "since":       "v2.2",
    },
    {
        "id":          "cognition.confidence",
        "name":        "Confidence Calibration",
        "category":    "cognition",
        "description": "Per-node trust scores computed from importance avg, decay health, valence stability, and memory volume.",
        "endpoint":    "GET /confidence",
        "status":      "active",
        "since":       "v2.2",
    },
    {
        "id":          "cognition.explain",
        "name":        "Memory Explain",
        "category":    "cognition",
        "description": "Natural language explanation of why a specific memory is relevant to a query.",
        "endpoint":    "POST /explain",
        "status":      "active",
        "since":       "v1.2",
    },
    # ── Coordination ─────────────────────────────────────────────────────────
    {
        "id":          "coordination.mycelium",
        "name":        "Mycelium Self-Healing",
        "category":    "coordination",
        "description": "Background process that senses stressed nodes and silently ships relevant memories to heal them. Immune memory vaccination.",
        "endpoint":    "GET /mycelium (status)",
        "status":      "active",
        "since":       "v1.3",
    },
    {
        "id":          "coordination.pheromone",
        "name":        "Stigmergic Pheromones",
        "category":    "coordination",
        "description": "Slime-mold inspired indirect coordination. Nodes drop reliable/danger pheromone trails that guide routing decisions.",
        "endpoint":    "POST /pheromone (drop), GET /pheromone (smell)",
        "status":      "active",
        "since":       "v1.4",
    },
    {
        "id":          "coordination.pheromone_auto",
        "name":        "Pheromone Auto-Drop",
        "category":    "coordination",
        "description": "Automatically drops pheromones on /ask success/failure and hook events (task:complete, node:error, ask:success).",
        "endpoint":    "Automatic — fires on /ask + hook events",
        "status":      "active",
        "since":       "v2.1",
    },
    {
        "id":          "coordination.circuit",
        "name":        "Circuit Breaker",
        "category":    "coordination",
        "description": "Prevents cascade failures by tracking per-node failure rates and opening circuits when thresholds are exceeded.",
        "endpoint":    "GET /circuit-status",
        "status":      "active",
        "since":       "v1.1",
    },
    # ── Observability ────────────────────────────────────────────────────────
    {
        "id":          "observability.metabolic",
        "name":        "Metabolic Rate",
        "category":    "observability",
        "description": "Real-time work-units/hour counter. Tracks asks served, memory writes, task completions, hook events.",
        "endpoint":    "GET /metabolic-rate",
        "status":      "active",
        "since":       "v2.0",
    },
    {
        "id":          "observability.dream_journal",
        "name":        "Dream Journal",
        "category":    "observability",
        "description": "Persistent JSONL audit log of significant mesh events: milestones, consolidations, healings, stresses, contradictions.",
        "endpoint":    "GET /dream-journal?limit=N&event=<type>",
        "status":      "active",
        "since":       "v2.0",
    },
    {
        "id":          "observability.health",
        "name":        "Node Health",
        "category":    "observability",
        "description": "Basic liveness check.",
        "endpoint":    "GET /health",
        "status":      "active",
        "since":       "v1.0",
    },
    {
        "id":          "observability.skills",
        "name":        "Skill Marketplace",
        "category":    "observability",
        "description": "This catalog — queryable by category to discover available capabilities.",
        "endpoint":    "GET /skills?category=<cat>",
        "status":      "active",
        "since":       "v2.2",
    },
    # ── Intelligence ─────────────────────────────────────────────────────────
    {
        "id":          "intelligence.immune",
        "name":        "Immune Memory (Vaccination)",
        "category":    "intelligence",
        "description": "Mycelium remembers successful cures via SHA1 symptom fingerprinting. Recurring errors are healed instantly.",
        "endpoint":    "GET /mycelium (vaccine_store stats)",
        "status":      "active",
        "since":       "v2.0",
    },
]

# Build index at load time
_BY_CATEGORY: dict = {}
for _s in _SKILLS:
    _BY_CATEGORY.setdefault(_s["category"], []).append(_s)


def get_skills(category: str = "") -> dict:
    """Return the skill catalog, optionally filtered by category."""
    if category:
        matched = _BY_CATEGORY.get(category.lower(), [])
    else:
        matched = _SKILLS

    categories = sorted(_BY_CATEGORY.keys())
    return {
        "total":         len(matched),
        "category":      category or "all",
        "available_categories": categories,
        "skills":        matched,
        "generated_at":  datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }

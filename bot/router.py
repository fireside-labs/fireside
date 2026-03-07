"""
router.py -- Skill-based + Semantic task router for the Bifrost mesh.
Standalone module — Odin imports this to route tasks to the best node.

Usage (keyword):
    from router import Router
    r = Router(skills_dir="/path/to/bot/bot")
    best = r.route("build a postgres migration script")
    # -> {"node": "thor", "score": 4, "matched": ["python", "sql", "postgres"]}

Usage (semantic):
    targets = r.semantic_route("who should handle the UI mockup?", top_k=2)
    # -> [{"node": "freya", "similarity": 0.91}, {"node": "thor", "similarity": 0.43}]
"""

import json
import re
import urllib.request
from pathlib import Path
from typing import Optional

# Node health endpoint base URLs — populated from config
_NODE_URLS: dict[str, str] = {}
_VRAM_OVERLOAD_THRESHOLD = 0.90   # 90% VRAM used = skip this node

# ---------------------------------------------------------------------------
# Fallback profiles — used when a node hasn't pushed its own skills.json yet
# ---------------------------------------------------------------------------
_FALLBACK_PROFILES = {
    "thor": {
        "node": "thor",
        "role": "backend engineer",
        "skills": ["python", "sql", "database", "docker", "go", "lancedb", "embeddings",
                   "vector-search", "memory-sync", "data-pipelines", "etl", "api", "rest",
                   "sqlite", "postgres", "redis", "bifrost", "mesh", "sync", "event-log",
                   "scripting", "automation", "devops", "linux"],
        "strengths": ["data engineering", "backend systems", "infrastructure", "embedding pipelines"],
        "avoid": ["react", "css", "figma", "3d", "frontend"],
    },
    "freya": {
        "node": "freya",
        "role": "frontend engineer and memory master",
        "skills": ["react", "css", "3d", "figma", "ui", "ux", "dashboard", "typescript",
                   "javascript", "design", "animation", "visualization", "memory-query",
                   "memory-sync", "lancedb", "embeddings", "frontend", "components",
                   "charts", "graphs", "webgl", "three-js"],
        "strengths": ["UI design", "3D visualization", "memory query interface", "dashboards"],
        "avoid": ["devops", "docker", "sql", "linux", "bash"],
    },
    "heimdall": {
        "node": "heimdall",
        "role": "observability and cost tracking",
        "skills": ["monitoring", "logging", "metrics", "costs", "audit", "compliance",
                   "security", "alerts", "dashboards", "grafana", "prometheus",
                   "tracing", "cost-tracking", "billing", "budget", "usage",
                   "api-gateway", "rate-limiting", "auth"],
        "strengths": ["observability", "cost tracking", "audit trails", "security"],
        "avoid": ["react", "3d", "figma", "frontend", "embeddings"],
    },
    "odin": {
        "node": "odin",
        "role": "orchestrator and architect",
        "skills": ["orchestration", "routing", "planning", "architecture", "coordination",
                   "strategy", "deployment", "config", "schema", "protocol",
                   "mesh", "bifrost", "workflow", "scheduling", "git", "macos"],
        "strengths": ["system design", "orchestration", "mesh coordination", "routing"],
        "avoid": [],
    },
    "huginn": {
        "node": "huginn",
        "role": "thought and research agent",
        "skills": ["research", "analysis", "reasoning", "planning", "synthesis",
                   "nlp", "summarization", "search", "knowledge", "retrieval"],
        "strengths": ["research", "analysis", "long-form reasoning"],
        "avoid": [],
    },
    "munnin": {
        "node": "munnin",
        "role": "memory and consolidation agent",
        "skills": ["memory", "consolidation", "svd", "clustering", "embeddings",
                   "recall", "retrieval", "lancedb", "vector-search", "eigen-memory"],
        "strengths": ["memory consolidation", "SVD dream compression", "recall"],
        "avoid": [],
    },
    "brisinga": {
        "node": "brisinga",
        "role": "creative and generative agent",
        "skills": ["creative", "writing", "generation", "storytelling", "images",
                   "prompts", "marketing", "copy", "ui-copy", "ideation"],
        "strengths": ["creative generation", "writing", "marketing copy"],
        "avoid": [],
    },
    "mjolnir": {
        "node": "mjolnir",
        "role": "execution and build agent",
        "skills": ["build", "ci", "cd", "deployment", "testing", "compilation",
                   "docker", "kubernetes", "bash", "shell", "infrastructure"],
        "strengths": ["build systems", "CI/CD", "deployment", "execution"],
        "avoid": [],
    },
}


def _embed(text: str, ollama_base: str = "http://127.0.0.1:11434") -> list[float]:
    """Get nomic-embed-text embedding from Ollama. Returns 768-dim float list."""
    payload = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
    req = urllib.request.Request(
        f"{ollama_base}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["embedding"]


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _get_node_load(node: str, config: dict = None) -> dict:
    """
    Fetch /health from a node and return load info.
    Returns {"overloaded": bool, "vram_used": float, "vram_total": float}
    """
    # Build URL from config or _NODE_URLS registry
    if node in _NODE_URLS:
        base = _NODE_URLS[node]
    elif config and "nodes" in config and node in config["nodes"]:
        n = config["nodes"][node]
        base = f"http://{n['ip']}:{n.get('port', 8765)}"
    else:
        return {"overloaded": False, "vram_used": 0, "vram_total": 0, "error": "no url"}
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=3) as r:
            data = json.loads(r.read())
            load = data.get("load", {})
            total = float(load.get("total_vram_gb") or 0)
            # Estimate used VRAM: 0 models loaded = 0, otherwise use total as proxy
            models = load.get("models_loaded", 0)
            # We don't have a "used" field, just total occupied by pinned models
            # Use models_loaded > 0 as alive signal; overload = not responding
            return {
                "overloaded": False,
                "vram_total": total,
                "models_loaded": models,
                "alive": True,
            }
    except Exception:
        # Unreachable = treat as overloaded to avoid routing to dead node
        return {"overloaded": True, "alive": False, "vram_total": 0}


def set_node_urls(urls: dict[str, str]):
    """Register base URLs for nodes so load checks can reach them."""
    global _NODE_URLS
    _NODE_URLS.update(urls)


def _profile_to_text(profile: dict) -> str:
    """Turn a skills profile into a natural language string for embedding."""
    parts = []
    if profile.get("role"):
        parts.append(f"Role: {profile['role']}.")
    if profile.get("strengths"):
        parts.append(f"Strengths: {', '.join(profile['strengths'])}.")
    if profile.get("skills"):
        parts.append(f"Skills: {', '.join(profile['skills'][:20])}.")
    if profile.get("avoid"):
        parts.append(f"Not suited for: {', '.join(profile['avoid'])}.")
    return " ".join(parts)


class Router:
    def __init__(self, skills_dir: str = None, skills_files: list = None,
                 ollama_base: str = "http://127.0.0.1:11434"):
        """
        Load skill profiles from a directory or file list.
        Falls back to built-in profiles for agents without skills.json.
        """
        self._profiles: list[dict] = []
        self._ollama_base = ollama_base
        self._personality_cache: dict[str, list[float]] = {}

        if skills_files:
            for f in skills_files:
                self._load(Path(f))
        elif skills_dir:
            base = Path(skills_dir)
            for p in sorted(base.rglob("skills.json")):
                self._load(p)

        # Fill in fallbacks for any agent not loaded from disk
        loaded_nodes = {p["node"] for p in self._profiles}
        for node, profile in _FALLBACK_PROFILES.items():
            if node not in loaded_nodes:
                self._profiles.append({**profile, "_fallback": True})

    def _load(self, path: Path):
        try:
            data = json.loads(path.read_text())
            if data.get("node"):
                self._profiles.append(data)
        except Exception:
            pass

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9][\w\-]*", text.lower())

    # ------------------------------------------------------------------
    # Keyword routing (fast, no network)
    # ------------------------------------------------------------------

    def score(self, node_profile: dict, task: str) -> dict:
        tokens = self._tokenize(task)
        skills  = [s.lower() for s in node_profile.get("skills", [])]
        avoid   = [a.lower() for a in node_profile.get("avoid", [])]
        matched   = [t for t in tokens if t in skills]
        penalized = [t for t in tokens if t in avoid]
        return {
            "node":      node_profile["node"],
            "role":      node_profile.get("role", ""),
            "score":     len(matched) - (len(penalized) * 2),
            "matched":   matched,
            "penalized": penalized,
            "model":     node_profile.get("model", ""),
            "max_tasks": node_profile.get("max_parallel_tasks", 1),
        }

    def score_all(self, task: str) -> list[dict]:
        scores = [self.score(p, task) for p in self._profiles]
        return sorted(scores, key=lambda x: x["score"], reverse=True)

    def route(self, task: str, exclude: list = None,
              load_check: bool = False, config: dict = None) -> Optional[dict]:
        exclude = list(exclude or [])
        if load_check:
            # Skip nodes that are unreachable
            dead = [n for n in self.available_nodes()
                    if _get_node_load(n, config).get("overloaded")]
            exclude = list(set(exclude + dead))
        ranked = [s for s in self.score_all(task) if s["node"] not in exclude]
        if not ranked:
            return None
        best = ranked[0]
        best["confident"] = best["score"] > 0
        best["load_checked"] = load_check
        return best

    # ------------------------------------------------------------------
    # Semantic routing (accurate, uses Ollama embeddings)
    # ------------------------------------------------------------------

    def _get_personality_vector(self, node: str) -> list[float]:
        """Return cached personality embedding for a node, computing if needed."""
        if node not in self._personality_cache:
            profile = next((p for p in self._profiles if p["node"] == node), None)
            if not profile:
                return []
            text = _profile_to_text(profile)
            try:
                vec = _embed(text, self._ollama_base)
                self._personality_cache[node] = vec
            except Exception as e:
                return []
        return self._personality_cache[node]

    def precompute_personalities(self):
        """Eagerly embed all agent personality vectors. Call at startup to warm cache."""
        for profile in self._profiles:
            self._get_personality_vector(profile["node"])

    def semantic_route(self, message: str, top_k: int = 2,
                       exclude: list = None,
                       load_check: bool = False, config: dict = None) -> list[dict]:
        """
        Embed message and rank agents by cosine similarity to their personality vectors.
        Optionally skips nodes that fail /health check (unreachable = overloaded).
        Returns top_k matches sorted by similarity descending.
        """
        exclude = list(exclude or [])
        if load_check:
            dead = [n for n in self.available_nodes()
                    if _get_node_load(n, config).get("overloaded")]
            exclude = list(set(exclude + dead))
            if dead:
                import logging
                logging.getLogger("router").info("[router] Skipping unreachable nodes: %s", dead)

        try:
            msg_vec = _embed(message, self._ollama_base)
        except Exception:
            results = self.score_all(message)
            return [
                {"node": r["node"], "similarity": max(0.0, r["score"] / 10.0),
                 "role": r["role"], "method": "keyword_fallback"}
                for r in results if r["node"] not in exclude
            ][:top_k]

        scores = []
        for profile in self._profiles:
            node = profile["node"]
            if node in exclude:
                continue
            pvec = self._get_personality_vector(node)
            if not pvec:
                continue
            sim = _cosine(msg_vec, pvec)
            scores.append({
                "node":         node,
                "similarity":   round(sim, 4),
                "role":         profile.get("role", ""),
                "method":       "semantic",
                "load_checked": load_check,
            })

        return sorted(scores, key=lambda x: x["similarity"], reverse=True)[:top_k]

    def available_nodes(self) -> list[str]:
        return [p["node"] for p in self._profiles]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    skills_dir = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent)
    task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None

    r = Router(skills_dir=skills_dir)
    nodes = r.available_nodes()
    print(f"Loaded profiles for: {', '.join(nodes)}")

    if task:
        print(f"\nMessage: '{task}'")

        print("\n[Keyword] Rankings:")
        for s in r.score_all(task):
            bar = "|" * max(0, s["score"])
            st = "+" if s["score"] > 0 else "-"
            print(f"  {st} {s['node']:12} score={s['score']:+d} {bar}")

        print("\n[Semantic] Top 2:")
        for s in r.semantic_route(task, top_k=2):
            print(f"  {s['node']:12} similarity={s['similarity']:.4f}  ({s['role']})")
    else:
        print("\nUsage: python router.py [skills_dir] <message>")

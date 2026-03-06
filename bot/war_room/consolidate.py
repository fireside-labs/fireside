"""
war_room/consolidate.py -- SVD Dream Consolidation (Munnin Logic)

Contract with Freya's LanceDB:
  - Query WHERE permanent = false, ORDER BY ts ASC (oldest mortal memories first)
  - Skip any memory with permanent = true
  - Cluster semantically similar ones (cosine threshold 0.85)
  - For clusters >= MIN_CLUSTER_SIZE: SVD → write 1 eigen-memory, delete originals
  - Eigen-memory written back with importance=0.95, permanent=false

Schedule: 2 AM via Windows Task Scheduler (see schedule_consolidation() at bottom)
Direct:   python war_room/consolidate.py [--dry-run] [--test] [--local] [--limit N]
"""

import argparse
import json
import logging
import time
import urllib.request
import uuid
from pathlib import Path

import numpy as np

log = logging.getLogger("consolidate")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

BASE = Path(__file__).parent.parent   # bot/bot/

FREYA_BASE       = "http://100.102.105.3:8765"
OLLAMA_BASE      = "http://127.0.0.1:11434"
EMBED_MODEL      = "nomic-embed-text"
CLUSTER_THRESH   = 0.85
MIN_CLUSTER_SIZE = 5
EIGEN_IMPORTANCE = 0.95
ARCHIVED_IMPORTANCE = 0.1
THIS_NODE        = "thor"


# ---------------------------------------------------------------------------
# Embedding + math
# ---------------------------------------------------------------------------

def embed(text: str) -> list[float]:
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())["embedding"]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0


# ---------------------------------------------------------------------------
# Fetch  — permanent=false contract
# ---------------------------------------------------------------------------

def fetch_mortal_memories(limit: int = 500) -> list[dict]:
    """
    GET /memory-query from Freya.
    Only processes memories where permanent != true.
    Freya should support ?permanent=false; we also filter client-side.
    """
    url = f"{FREYA_BASE}/memory-query?limit={limit}&sort=ts_asc"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        all_mems = data.get("memories") or data.get("results") or []
        mortal = [m for m in all_mems if not m.get("permanent", False)]
        log.info("Freya: %d total, %d mortal (permanent=false)", len(all_mems), len(mortal))
        return mortal
    except Exception as e:
        log.warning("Freya unreachable (%s) — trying local LanceDB", e)
        return fetch_mortal_local()


def fetch_mortal_local() -> list[dict]:
    """Fallback: read from local LanceDB, filter permanent=false."""
    try:
        import sys
        sys.path.insert(0, str(BASE))
        import memory_sync  # type: ignore
        db_path = BASE / "lancedb_memories"
        mems = memory_sync.get_shareable_memories(db_path, min_importance=0.0)
        mortal = [m for m in mems if not m.get("permanent", False)]
        log.info("Local LanceDB: %d mortal memories", len(mortal))
        return mortal
    except Exception as e:
        log.error("Local LanceDB failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def cluster_memories(memories: list[dict]) -> list[list[dict]]:
    """Greedy cosine-similarity clustering. Skips memories without embeddings."""
    with_embed = [m for m in memories if m.get("embedding")]
    if not with_embed:
        log.warning("No embeddings found in memories — cannot cluster")
        return []

    vecs = [np.array(m["embedding"], dtype=np.float32) for m in with_embed]
    assigned = [False] * len(vecs)
    clusters = []

    for i, mem_i in enumerate(with_embed):
        if assigned[i]:
            continue
        cluster = [mem_i]
        assigned[i] = True
        for j in range(i + 1, len(vecs)):
            if not assigned[j] and cosine(vecs[i], vecs[j]) >= CLUSTER_THRESH:
                cluster.append(with_embed[j])
                assigned[j] = True
        if len(cluster) >= MIN_CLUSTER_SIZE:
            clusters.append(cluster)

    log.info("%d cluster(s) with >= %d members found", len(clusters), MIN_CLUSTER_SIZE)
    return clusters


# ---------------------------------------------------------------------------
# SVD eigen-memory
# ---------------------------------------------------------------------------

def compute_eigen(cluster: list[dict]) -> dict:
    M = np.array([m["embedding"] for m in cluster], dtype=np.float64)
    U, S, Vh = np.linalg.svd(M, full_matrices=False)
    eigen_vec = Vh[0].tolist()
    variance_captured = float(S[0] ** 2 / np.sum(S ** 2))

    eigen_np = np.array(eigen_vec, dtype=np.float64)
    sims = [cosine(np.array(m["embedding"]), eigen_np) for m in cluster]
    best = cluster[sims.index(max(sims))]

    all_tags = list({tag for m in cluster for tag in m.get("tags", [])})
    content = (
        f"[EIGEN/{len(cluster)}] {best.get('content', '')[:200]} "
        f"(consolidated from {len(cluster)} memories, "
        f"variance={variance_captured:.1%})"
    )

    return {
        "memory_id":      str(uuid.uuid4()),
        "node":           THIS_NODE,
        "agent":          "munnin",
        "content":        content,
        "embedding":      eigen_vec,
        "tags":           list(set(all_tags + ["eigen", "consolidated"])),
        "importance":     EIGEN_IMPORTANCE,
        "ts":             time.time(),
        "shared":         True,
        "permanent":      False,
        "cluster_size":   len(cluster),
        "source_ids":     [m.get("memory_id", "") for m in cluster],
        "variance_pct":   round(variance_captured * 100, 2),
    }


# ---------------------------------------------------------------------------
# Write eigen-memory, delete originals
# ---------------------------------------------------------------------------

def push_memory(memories: list[dict], dry_run: bool = False) -> bool:
    if dry_run:
        for m in memories:
            log.info("[DRY RUN] push: %s", m.get("content", "")[:100])
        return True
    try:
        payload = json.dumps({"memories": memories}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8765/memory-sync",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("status") != "error"
    except Exception as e:
        log.error("push_memory failed: %s", e)
        return False


def archive_originals(cluster: list[dict], dry_run: bool = False):
    """Mark source memories as archived so they don't re-cluster."""
    for m in cluster:
        m["importance"] = ARCHIVED_IMPORTANCE
        m["tags"] = list(set(m.get("tags", []) + ["archived"]))
    if not dry_run:
        push_memory(cluster, dry_run=False)
    else:
        log.info("[DRY RUN] Would archive %d source memories", len(cluster))


# ---------------------------------------------------------------------------
# Synthetic test data
# ---------------------------------------------------------------------------

def inject_synthetic(n: int = 20) -> list[dict]:
    log.info("Injecting %d synthetic memories...", n)
    topics = [
        ("postgres index optimisation for large analytical queries", ["sql", "database", "performance"]),
        ("react live dashboard with d3 charts and websockets",        ["react", "ui", "charts"]),
        ("jwt token rotation and refresh logic for api security",     ["security", "auth", "api"]),
    ]
    memories = []
    for i in range(n):
        text, tags = topics[i % len(topics)]
        try:
            vec = embed(f"{text} variant {i}")
        except Exception:
            vec = [0.0] * 768
        memories.append({
            "memory_id": str(uuid.uuid4()),
            "node": THIS_NODE, "agent": THIS_NODE,
            "content": f"{text} — variant {i}",
            "embedding": vec, "tags": tags,
            "importance": 0.75, "ts": time.time(),
            "shared": True, "permanent": False,
        })
    push_memory(memories)
    log.info("Injected %d synthetic memories", len(memories))
    return memories


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def consolidate(memories: list[dict], dry_run: bool = False) -> dict:
    stats = {"clusters": 0, "eigen_created": 0, "archived": 0}
    clusters = cluster_memories(memories)
    stats["clusters"] = len(clusters)

    for i, cluster in enumerate(clusters):
        log.info("Cluster %d/%d (%d memories):", i + 1, len(clusters), len(cluster))
        for m in cluster:
            log.info("  - [%.2f] %s", m.get("importance", 0), m.get("content", "")[:72])

        eigen = compute_eigen(cluster)
        log.info("Eigen: %s", eigen["content"][:100])

        if push_memory([eigen], dry_run=dry_run):
            stats["eigen_created"] += 1

        archive_originals(cluster, dry_run=dry_run)
        stats["archived"] += len(cluster)

    return stats


def main():
    parser = argparse.ArgumentParser(description="SVD Dream Consolidation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test",    action="store_true", help="Inject 20 synthetic memories then run")
    parser.add_argument("--local",   action="store_true", help="Force local LanceDB")
    parser.add_argument("--limit",   type=int, default=500)
    args = parser.parse_args()

    log.info("=== SVD Dream Consolidation ===")

    if args.test:
        memories = inject_synthetic(n=20)
    elif args.local:
        memories = fetch_mortal_local()
    else:
        memories = fetch_mortal_memories(limit=args.limit)

    if not memories:
        log.info("No mortal memories to consolidate — done")
        return

    stats = consolidate(memories, dry_run=args.dry_run)
    log.info("Done: %s", stats)


if __name__ == "__main__":
    main()

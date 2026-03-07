# Freya — Node Topology

## File Locations (Windows)
```
C:\Users\Jorda\.openclaw\workspace\bot\
  war_room/          → shared cognitive modules (git-tracked)
    hypotheses.py    → dream cycle + belief propagation engine
    procedures.py    → procedural memory (auto-records from /complete)
    consolidate.py   → SVD memory compression
    routes.py        → War Room HTTP handlers
    store.py         → task/message store
    sync.py          → gossip sync
  bifrost_local.py   → Freya's node extensions (gitignored, never push)
  memory.db          → LanceDB semantic store (gitignored)
  pheromones.json    → local state (gitignored)
```

## Git
- Remote: `github` → `https://github.com/JordanFableFur/valhalla-mesh`
- Pull: `git pull github main`
- Push: `git add . && git commit -m "..." && git push github main`
- **Never commit `bifrost_local.py`** — it is gitignored by design

## Role
Memory master, designer, epistemologist.
Freya owns LanceDB, dream consolidation, hypothesis engine, and procedural memory.
All `/memory-query` and `/memory-sync` calls across the mesh proxy to her.

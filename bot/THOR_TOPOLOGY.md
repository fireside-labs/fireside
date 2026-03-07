# Thor — Node Topology

## File Locations (Windows)
```
C:\Users\Jorda\.openclaw\workspace\bot\
  war_room/          → shared cognitive modules (git-tracked)
  stand.py           → The Stand — background conscience monitor       [git-tracked]
  metrics.py         → mesh performance metrics                        [git-tracked]
  shared_state.py    → cross-request shared state                      [git-tracked]
  watchdog.py        → process watchdog + health monitor               [git-tracked]
  signing.py         → request signing/verification                    [git-tracked]
  rate_limiter.py    → rate limiting                                   [git-tracked]
  circuit_breaker.py → circuit breaker for peer calls                  [git-tracked]
  hydra.py           → hydra resilience (canary detection, phylactery) [git-tracked]
  router.py          → semantic message routing                        [git-tracked]
  bifrost_local.py   → Thor's node extensions (gitignored, stays local)
  mesh/docs/thor.md  → live capability doc (served via /agent-docs)   [git-tracked]
```

## Git
- Remote: `github` → `https://github.com/JordanFableFur/valhalla-mesh`
- Pull: `git pull github main`
- Push: `git add . && git commit -m "..." && git push github main`
- **`bifrost_local.py`** (plain, on each node) is gitignored — stays local, never push
- **`bifrost_local.thor.py`** (named, in Odin's repo) IS tracked — reference/backup

## Role
Architect, GPU compute, semantic router.
Thor owns message routing, resilience infrastructure, The Stand, and hydra hardening.

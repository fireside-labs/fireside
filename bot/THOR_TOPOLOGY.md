# Thor — Node Topology

## File Locations (Windows)
```
C:\Users\Jorda\.openclaw\workspace\bot\
  war_room/          → shared cognitive modules (git-tracked)
  stand.py           → The Stand — background conscience monitor
  metrics.py         → mesh performance metrics
  shared_state.py    → cross-request shared state
  watchdog.py        → process watchdog + health monitor
  signing.py         → request signing/verification
  rate_limiter.py    → rate limiting
  circuit_breaker.py → circuit breaker for peer calls
  hydra.py           → hydra resilience (canary detection, phylactery)
  router.py          → semantic message routing
  bifrost_local.py   → Thor's node extensions (gitignored, never push)
  mesh/docs/thor.md  → live capability doc (served via /agent-docs)
```

## Git
- Remote: `github` → `https://github.com/JordanFableFur/valhalla-mesh`
- Pull: `git pull github main`
- Push: `git add . && git commit -m "..." && git push github main`
- **Never commit `bifrost_local.py`** — it is gitignored by design

## Role
Architect, GPU compute, semantic router.
Thor owns message routing, resilience infrastructure, The Stand, and hydra hardening.

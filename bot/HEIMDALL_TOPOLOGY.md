# Heimdall — Node Topology

## File Locations (Windows)
```
C:\Users\Heimdall\.openclaw\workspace\bot\
  war_room/              → shared cognitive modules (git-tracked)
  bifrost_local.py       → Heimdall's node extensions (gitignored, never push)
    Siren system         → honeypot endpoints + canary task monitor
    memory sweep         → pre-populated sentinel hashes for intrusion detection
    Stand integration    → /ask pipeline integrity check
    quarantine config    → POST /quarantine-config for Thor watchdog
  circuit_breaker.py     → circuit breaker
  prompt_guard.py        → prompt injection defense
  memory_integrity.py    → memory tamper detection
  inference_cache.py     → inference response caching
  working_memory.py      → short-term working memory
  perf_metrics.py        → performance metrics
  mesh/docs/heimdall.md  → live capability doc (served via /agent-docs)
```

## Git
- Remote: `github` → `https://github.com/JordanFableFur/valhalla-mesh`
- Pull: `git pull github main`
- Push: `git add . && git commit -m "..." && git push github main`
- **Never commit `bifrost_local.py`** — it is gitignored by design

## Role
Security auditor, cost tracker, insider threat detection.
Heimdall owns the Siren (honeypot + canary), prompt guard, memory integrity, and quarantine config.

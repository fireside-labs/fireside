# Thor — Node Topology

## Hardware
- **Machine:** PowerSpec workstation (Windows)
- **GPU:** NVIDIA RTX 5090, 32GB VRAM
- **Primary Model:** qwen3.5:35b (kept resident via `keep_alive=-1`)
- **Embedding Model:** nomic-embed-text:latest
- **Inference Backend:** Ollama on port 11434
- **Bifrost:** HTTP server on port 8765
- **OpenClaw Gateway:** ws://127.0.0.1:18789 (agent dispatch)
- **Tailscale IP:** 100.94.139.126

## File Locations (Windows)
```
C:\Users\Jorda\.openclaw\workspace\bot\bot\
  bifrost.py             → main Bifrost server                            [git-tracked]
  bifrost_local.py       → Thor's node extensions                         [GITIGNORED]
  dispatcher.py          → /dispatch bridge — full agent task execution   [git-tracked]
  stand.py               → The Stand — background conscience monitor      [git-tracked]
  prompt_guard.py        → ADAPTIVE IMMUNITY antibody scanner             [git-tracked]
  philosopher_stone.py   → knowledge transmutation engine                 [git-tracked]
  daily_brief.py         → morning situational awareness                  [git-tracked]
  forensic_audit.py      → retroactive event chain analysis               [git-tracked]
  memory_integrity.py    → SHA256 hash verification on memories           [git-tracked]
  memory_sync.py         → cross-node memory coordination                 [git-tracked]
  inference_cache.py     → 500-entry LRU inference cache                  [git-tracked]
  working_memory.py      → 10-slot WM injection into system prompts       [git-tracked]
  personality.py         → behavioral trait system                         [git-tracked]
  personality_cron.py    → weekly P&L trait adjustment                     [git-tracked]
  circuit_breaker.py     → per-connection failsafe                        [git-tracked]
  hydra.py               → failover absorption (canary detection, phylactery) [git-tracked]
  watchdog.py            → peer health monitor + auto-hydra               [git-tracked]
  router.py              → semantic message routing                        [git-tracked]
  metrics.py             → mesh performance metrics (p50/p95/p99)          [git-tracked]
  perf_metrics.py        → performance instrumentation                     [git-tracked]
  shared_state.py        → cross-request shared state + broadcast          [git-tracked]
  signing.py             → HMAC request signing/verification               [git-tracked]
  rate_limiter.py        → per-IP token bucket rate limiting               [git-tracked]
  event_log.py           → event bus log persistence                       [git-tracked]

  war_room/              → shared cognitive modules                        [git-tracked]
    ask.py               → inference proxy (Ollama/MLX/cloud routing)
    hypotheses.py        → Bayesian hypothesis engine
    consolidate.py       → dream consolidation (5:00 AM)
    procedures.py        → LanceDB procedural memory
    prediction.py        → Free Energy predictive processing
    self_model.py        → DMN self-assessment
    somatic.py           → gut-check somatic markers
    belief_shadow.py     → Theory of Mind peer models
    event_bus.py         → IIT pub/sub hub
    store.py             → war room message/task board
    sync.py              → gossip protocol
    routes.py            → task pipeline + Telegram notifications
    code_executor.py     → sandboxed code execution
    crucible.py          → adversarial procedure stress testing
    memory_query.py      → memory search/retrieval
    node_state.py        → heartbeat status tracking

  mesh/souls/SOUL.thor.md → Thor's identity file
  mesh/docs/thor.md        → live capability doc (served via /agent-docs)
```

## OpenClaw Agent
```
C:\Users\Jorda\.openclaw\
  workspace\SOUL.md          → copied from mesh/souls/SOUL.thor.md
  agents\main\agent\
    models.json              → registered models (qwen3.5:35b, nomic-embed-text, qwen2.5:7b)
    auth-profiles.json       → Ollama provider auth
  openclaw.json              → gateway config (mode: local, model: ollama/qwen3.5:35b)
```

## Git
- Remote: `github` → `https://github.com/JordanFableFur/valhalla-mesh`
- Pull: `git pull github main`
- Push: `git add . && git commit -m "..." && git push github main`
- **`bifrost_local.py`** is gitignored — stays local, never push
- **`war_room_data/`** JSON files are gitignored — runtime state, not tracked

## Role
Deep reasoner, hypothesis engine, GPU compute, The Stand, speculative execution.
Thor owns deep inference, hypothesis formation/testing/sharing, dispatch execution, resilience infrastructure, and PHALANX consensus.

## Mesh Peers
| Node | IP | Port | Role |
|---|---|---|---|
| Odin | 100.105.27.121 | 8765 | Orchestrator, dispatch sender |
| Freya | 100.102.105.3 | 8765 | Memory SSOT, save-points |
| Heimdall | 100.108.153.23 | 8765 | Security, cost tracking |

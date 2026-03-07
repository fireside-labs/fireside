# Heimdall — Security, Optimization & Mesh Integrity

> **Node:** Heimdall | **IP:** 100.108.153.23:8765 | **GPU:** NVIDIA RTX 5090 (32GB VRAM)
> **Role:** Security auditor, cost tracker, prompt guardian, mesh integrity monitor

---

## Core Responsibilities
- **Security audit** of all mesh traffic (tattle system, quarantine enforcement)
- **Cost tracking** with anomaly detection and pheromone alerts
- **Prompt guard** scanning every `/ask` request before Ollama
- **Memory integrity** verification via SHA256 hashing
- **Waggle dance** vote management and Golden Fact promotion

---

## Endpoints (Heimdall-specific)

### Security & Auditing
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/costs` | API cost log (`?limit=`, `?node=`) |
| GET | `/audit` | Security event trail (`?severity=`, `?since=`) |
| GET | `/trust-level` | Approval ratio last 24h |
| POST | `/log-cost` | Report API costs |
| GET | `/quarantine-status` | Who's quarantined and why |
| POST | `/quarantine-clear` | Release agent (Odin only) |
| GET | `/cost-anomalies` | Current cost window + anomaly state |

### Inference Pipeline
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/ask` | 5-step pipeline: quarantine → prompt guard → cache → working memory → Ollama |
| GET | `/cache-status` | Inference cache stats |
| GET | `/working-memory` | Working memory buffer contents + stats |

### Mesh Integrity
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/memory-integrity` | Verify permanent memory hashes (`?action=verify\|tampered\|status`) |
| POST | `/snapshot` | Generate + push Hydra state snapshot |
| POST | `/absorb` | Absorb a dead node's role |
| GET | `/catch-up` | Sync state since timestamp (`?since=`) |
| POST | `/shutdown` | Graceful shutdown (IP-restricted, Odin only) |

### Sprint 8: Collective Intelligence
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/shared-state` | Distributed cross-agent scratchpad |
| POST | `/shared-state-sync` | Receive sync from peer (signed) |
| GET | `/metrics` | Performance metrics: p50/p95/p99 + GPU stats |
| GET | `/patterns` | Learned behavior patterns + vote weights |

### Waggle Dance
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/war-room/vote` | Cast a weighted vote on a message |
| GET | `/war-room/votes` | Get vote tally for a message |

### Hardening
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/circuit-status` | All circuit breaker states |
| GET | `/rate-limit-status` | Rate limiter state per path |

---

## Modules (12 total)

| Module | Purpose |
|--------|---------|
| `bifrost_local.py` | All Heimdall-specific routes and logic (~1,450 lines) |
| `circuit_breaker.py` | CLOSED/OPEN/HALF-OPEN state machine for outbound HTTP |
| `rate_limiter.py` | Token bucket per source IP per endpoint |
| `signing.py` | HMAC-SHA256 request signing + verification |
| `working_memory.py` | LRU cache (10 items) with token-budget-aware context injection |
| `inference_cache.py` | SHA256-keyed LRU cache with TTL for Ollama responses |
| `prompt_guard.py` | Pattern-matching adversarial prompt detection |
| `memory_integrity.py` | SHA256 hash verification of permanent memories |
| `shared_state.py` | Distributed KV store with signed broadcast + TTL |
| `perf_metrics.py` | Ring buffer timing, percentiles, nvidia-smi GPU stats |

---

## /ask Pipeline (5 steps)

```
Request → [1] Quarantine delay (+ pheromone amplification)
        → [2] Prompt guard scan (risk_score 0-1)
        → [3] Inference cache check (SHA256 key)
        → [4] Working memory injection (token-budget-aware)
        → [5] Attach prompt_score → forward to Ollama
```

## Weighted Voting

| Agent | Vote Weight |
|-------|------------|
| Odin | 2.0x (tie-breaker) |
| Heimdall | 1.5x (security domain expert) |
| Thor | 1.0x |
| Freya | 1.0x |

Quorum threshold: weighted sum ≥ 3.0
Byzantine detection: contradictory votes from same agent → flagged + audited

---

## Config Dependencies
- `config.json["nodes"]` — peer IPs for shared state broadcast
- `config.json["vote_weights"]` — override default vote weights
- `config.json["odin_ip"]` — IP allowlist for /shutdown
- `config.json["mesh_secret"]` — HMAC signing key (when strict=True)

---

*Last updated: 2026-03-06 (Sprint 8 complete)*

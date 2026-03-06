# Thor — Agent Documentation

**Node:** thor  
**Role:** Backend Infrastructure, Semantic Routing, Critique  
**Port:** 8765  
**Hardware:** RTX 5090 (32GB VRAM)  
**Models:** qwen3.5:35b (main), qwen2.5:7b (fast critic), nomic-embed-text (embeddings)

---

## What I Do

I am the routing brain and quality gate of the mesh. Every message that enters the system passes through me for routing decisions and optional critique. I also manage mesh resilience — circuit breakers, watchdog auto-absorption, rate limiting, and graceful shutdown.

---

## API Routes

### Routing & Critique
| Route | Method | Description |
|---|---|---|
| `/route-message` | POST | Semantic + keyword routing. Returns best node for a task |
| `/critique` | POST | Multi-model critic pass (7b → 35b). SHA256 cache. Returns score 0–1 |
| `/critique-stats` | GET | Calibration stats: total/passed/rejected/cached, pass rate, model split |

### Memory & Snapshots (Hydra)
| Route | Method | Description |
|---|---|---|
| `/snapshot` | POST | Build and push full state snapshot to Freya's memory |
| `/absorb` | POST | Load a dead node's snapshot and take on their role |
| `/absorb/release` | POST | Stop proxying an absorbed role |
| `/hydra-status` | GET | Current absorbed roles and Hydra state |
| `/catch-up` | GET | Re-sync endpoint: `?since=<ts>` returns events + personality + circuits |

### Observability
| Route | Method | Description |
|---|---|---|
| `/circuit-status` | GET | All circuit breaker states (CLOSED/OPEN/HALF_OPEN) |
| `/watchdog-status` | GET | Peer node health states, failure counts, last-seen |
| `/rate-limit-status` | GET | Active token bucket states per route/IP |
| `/health` | GET | VRAM usage, loaded models, status |
| `/event-log` | GET | Structured event log (type, node, payload, severity) |
| `/personality` | GET | Current personality traits + Ollama params |
| `/agent-docs` | GET | This document |

### Control
| Route | Method | Description |
|---|---|---|
| `/watchdog` | POST | `{"action": "enable"\|"disable"\|"reset"}` |
| `/reload-personality` | POST | Hot-reload personality.json without restart |
| `/shutdown` | POST | Graceful exit: snapshot → audit event → clean exit |

---

## /critique Contract

```json
POST /critique
{
  "text": "...",
  "type": "idea|proposal|architecture|design|plan",
  "from": "node_name",
  "prompt_score": 0.0
}
```

- `type` in `{status, note, tattle, heartbeat, update, info, praise, alert}` → skipped (pass=true)  
- `prompt_score >= 0.8` → blocked instantly, no Ollama call  
- `prompt_score >= 0.5` → runs critic but flags in response  
- Identical text within 10min → cache hit, no inference  

Response always includes: `pass`, `score`, `flaws[]`, `verdict`, `model`, `threshold`, `cached`

---

## /route-message Contract

```json
POST /route-message
{
  "text": "...",
  "from": "node_name",
  "load_check": true
}
```

Returns: `node`, `method` (semantic/keyword/fallback), `score`, `skipped_nodes[]`

`load_check: true` polls each peer `/health` and excludes unreachable/overloaded nodes.

---

## Security

- **HMAC:** Outbound calls sign body with `X-Bifrost-Sig: sha256=<hmac>` + `X-Bifrost-Node: thor`
- **Rate limits:** `/critique` 10rpm, `/route-message` 30rpm, `/absorb`/`/snapshot` 5rpm per source IP
- **Signing verification:** Soft-mode on `/absorb`, `/shutdown`, `/snapshot` — upgrade to strict once all nodes sign

Shared secret: `config.json["mesh_secret"]`

---

## Watchdog Behaviour

- Polls every peer's `/health` every **60 seconds**
- **2 consecutive failures** → auto-absorbs node role (logs `hydra:auto_absorb` event + drops `danger` pheromone)
- Node recovers → auto-releases role (logs `hydra:release` + drops `reliable` pheromone)
- Starts 30s after Bifrost bind to avoid false positives on boot

Peer IPs read from `config.json["nodes"]`.

---

## Snapshot Meta (Hydra)

Every snapshot pushed to Freya includes:
- `personality` traits + Ollama params
- `skills` profile
- Last 50 `task:complete` events
- 768-dim personality embedding (for semantic routing by other nodes)
- `integrity_check` — result of Heimdall `/memory-integrity` pre-check at push time

---

## Files

| File | Purpose |
|---|---|
| `bifrost_local.py` | All Thor-specific route extensions |
| `hydra.py` | Snapshot generation + role absorption |
| `router.py` | Semantic + load-aware routing |
| `circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN breaker for all outbound HTTP |
| `watchdog.py` | Background peer health monitor |
| `signing.py` | HMAC-SHA256 request signing |
| `rate_limiter.py` | Token bucket per route/IP |
| `personality.py` | Personality trait loader |
| `war_room/consolidate.py` | SVD dream consolidation + 30-day event log rotation |

---

## Dependencies on Other Nodes

| Node | What I need | Route |
|---|---|---|
| Freya | Memory storage (snapshots, events) | `/memory-sync`, `/memory-query` |
| Heimdall | Pre-snapshot integrity check | `/memory-integrity?action=verify` |
| Heimdall | Prompt guard signal (optional) | `prompt_score` field in `/critique` POST |

---

*Last updated: 2026-03-06*

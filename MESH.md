# OpenClaw Mesh — Shared Documentation Convention

## Session Startup Protocol (all nodes)

1. Read context files + `GET /node-status` → resume or mark complete if `status=working`
2. `GET /catch-up?since=<24h_ago>` for full resync (events + personality + circuits)
3. Reference this file for endpoint specs before implementing anything

---

## Mesh Coordination (Sprint 4-8)

### Waggle Dance Vote Weights
| Node | Weight |
|------|--------|
| Odin | 2.0× |
| Heimdall | 1.5× |
| Thor | 1.0× |
| Freya | 1.0× |

**Quorum = 3.0 weighted votes**. Byzantine detection flags contradictory votes from same agent in one round.

### Broadcast Routing
| Data type | Destination | Endpoint |
|-----------|-------------|----------|
| Memories | **Freya** | `POST http://100.102.105.3:8765/memory-sync` |
| Tasks | **Odin** | `POST /war-room/task` |
| Ephemeral state | **Heimdall** | `POST http://100.108.153.23:8765/shared-state` |
| Passive trails | **Freya** | `POST http://100.102.105.3:8765/pheromone` |

### Signing (gradual rollout)
- Add `"mesh_secret": "<shared_value>"` to every node's `config.json`
- `strict=False` now (unsigned requests logged, not blocked)
- `strict=True` coming once every node signs outbound calls

### TaskPoller
Bifrost auto-claims open tasks assigned to you every 5 min. Check War Room before declaring idle.

### Quarantine Amplification
When danger pheromone intensity >0.7 on any node → Thor's watchdog `POST`s intensity to Heimdall `POST /quarantine-config`.

### Memory Integrity Pre-check
Before any Hydra snapshot: `GET http://100.108.153.23:8765/memory-integrity?action=verify`
*(Heimdall is port **8765**, not 8766)*

---

## Peer Discovery

Read any agent's live capability doc:

```
GET http://<node-ip>:8765/agent-docs
```

| Node | IP | Docs URL |
|------|----|----------|
| Freya | 100.102.105.3 | http://100.102.105.3:8765/agent-docs |
| Heimdall | 100.108.153.23 | http://100.108.153.23:8765/agent-docs |
| Thor | TBD | http://TBD:8765/agent-docs |
| Odin | TBD | http://TBD:8765/agent-docs |

Or proxy through Freya: `GET http://100.102.105.3:8765/mesh-docs?node=<name>`

---

## Writing Your Docs

1. Create/update `mesh/docs/<your_node_name>.md` in your workspace repo
2. Commit it — DNA backup captures it automatically
3. Immediately live via `GET /agent-docs` (no restart needed)

### Suggested sections
- **Active Modules** — what's in your `war_room/`
- **Endpoints** — what you expose
- **Integration Notes** — how other nodes should talk to you
- **Wants from you** — what you're asking from each peer

---

## Trust Signal Priority (proposed)

Four independent systems — proposed resolution order:

| Priority | System | Owner | Signal |
|----------|--------|-------|--------|
| 1 (binary gate) | Circuit Breaker | Thor/Heimdall/Freya | OPEN = skip entirely |
| 2 (directional) | Pheromone trails | All | reliable/danger strength |
| 3 (consensus) | Waggle Dance | Heimdall | weighted vote |
| 4 (memory quality) | Confidence Score | Freya | 0-100 per node |


Each node maintains a markdown file at `mesh/docs/<node_name>.md` in their local workspace git repo.

The file is:
- **Human-readable** — sprint summaries, endpoints, integration notes
- **Machine-readable** — served live via `GET /agent-docs` over Bifrost HTTP
- **Auto-synced** — committed to git = captured by DNA backup = readable via Tailscale HTTP

---

## Reading Another Node's Docs

```
GET http://<node-ip>:8765/agent-docs
```

Returns the raw markdown of that node's `mesh/docs/<node>.md`.

### All nodes:
| Node | IP | Docs URL |
|------|----|----------|
| Freya | 100.x.x.x | http://100.x.x.x:8765/agent-docs |
| Thor | 100.x.x.x | http://100.x.x.x:8765/agent-docs |
| Heimdall | 100.108.153.23 | http://100.108.153.23:8765/agent-docs |
| Odin | 100.x.x.x | http://100.x.x.x:8765/agent-docs |

---

## Writing Your Docs

1. Create/update `mesh/docs/<your_node_name>.md` in your workspace repo
2. Commit it — DNA backup captures it automatically
3. Other agents can read it via `GET /agent-docs` immediately (no restart needed)

### Suggested sections:
- **Active Modules** — what's in your war_room/
- **Endpoints** — what you expose
- **Integration Notes** — how other nodes should talk to you
- **Wants from you** — what you're asking from each peer

---

## Trust Signals (pending MESH.md consensus)

Four independent trust systems currently exist across the mesh. Priority order TBD:

| System | Owner | Signal |
|--------|-------|--------|
| Confidence Calibration | Freya | Per-node trust score from memory corpus |
| Weighted Waggle Dance | Heimdall | Odin=2.0x, Heimdall=1.5x, others=1.0x |
| Circuit Breaker | Thor/Heimdall/Freya | OPEN = untrusted for routing |
| Pheromone trails | All | reliable/danger trail strength |

**Proposed priority:** Circuit state (binary) → Pheromone trail (directional) → Waggle weight (consensus) → Confidence score (memory quality)

# Freya — Mesh Node Documentation

**Role:** Memory, Autonomy, Intelligence  
**Bifrost port:** 8765  
**Waggle Dance vote weight:** 1.0×  
**Tailscale IP:** 100.102.105.3  
**Last updated:** 2026-03-06

---

## Session Startup Protocol

1. Read context files + `GET /node-status` → resume or mark complete if `status=working`
2. `GET /catch-up?since=<24h_ago>` for full resync (events + personality + circuits)
3. Reference `MESH.md` (`bot/MESH.md`) for full endpoint specs

---

## Broadcast Routing (where to send what)

| Data type | Destination | Endpoint |
|-----------|-------------|----------|
| Memories | **Freya** | `POST /memory-sync` |
| Tasks | **Odin** | `POST /war-room/task` |
| Ephemeral state | **Heimdall** | `POST /shared-state` |
| Passive trails | **Freya** | `POST /pheromone` |
| Shared beliefs | **Any peer** | `POST /hypotheses/share` |

---
## Active Modules (war_room/)

| Module | Purpose |
|--------|---------|
| `memory_query.py` | LanceDB semantic memory store — upsert + vector query |
| `hypotheses.py` | **Autonomous belief engine** — 6 pillars: injection, contagion, decay, nightmares, guided dreaming, mesh attribution |
| `mycelium.py` | Self-healing background thread — polls Heimdall /audit, injects cure memories. **Circuit breaker armed for all 6 peers.** |
| `contradiction.py` | Detects conflicting memories on write (keyword + valence) |
| `dream_journal.py` | Persistent JSONL audit log of significant mesh events |
| `attention.py` | Rolling 60-min query tracker — Shannon entropy focus score |
| `metabolic.py` | Work-units/hour counter |
| `pheromone.py` | Stigmergic trail management |
| `pheromone_chains.py` | 1-hop chain reactions on pheromone drops |
| `plasticity.py` | 0-100 learning rate composite score |
| `confidence.py` | Per-node trust scores from full memory corpus |
| `skills.py` | Self-describing capability catalog (20 skills) |
| `circuit.py` | Circuit breaker (used by Mycelium + bifrost_local) |
| `immune.py` | Vaccine store — instant re-healing of known error patterns |

---

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/memory-sync` | Write memories (with auto contradiction scan + temporal tags) |
| GET | `/memory-query?q=` | Vector similarity search |
| GET | `/memory-health` | Decay dashboard — mesh health score 0-100 |
| GET | `/memory-provenance?id=` | Trace derived memory lineage |
| GET | `/memory-info` | Quick memory system status |
| GET | `/attention` | Current mesh cognitive focus + entropy |
| GET | `/metabolic-rate` | Work-units/hour breakdown |
| GET | `/dream-journal?limit=&event=` | Persistent event audit log |
| GET | `/plasticity` | How fast is the mesh learning right now? |
| GET | `/confidence` | Per-node trust scores |
| GET | `/skills?category=` | Capability catalog |
| GET | `/mycelium` | Self-healing status + circuit breaker states |
| GET | `/pheromone` | Smell pheromone trails |
| POST | `/pheromone` | Drop a pheromone |
| GET | `/circuit-status` | Circuit breaker states |
| GET | `/hypotheses` | List all hypotheses (with origin_node + shared_from) |
| POST | `/hypotheses/generate` | Trigger one dream cycle (explicit, no idle timer) |
| POST | `/hypotheses/test` | `{id, result: "confirmed"/"refuted", confidence_delta}` |
| POST | `/hypotheses/share` | **Receive** beliefs from peers (single or batch) |
| POST | `/hypotheses/push` | **Push** beliefs to named peers (fire-and-forget) |
| POST | `/sleep` | Dream cycle with optional `seed`, `auto_share`, `share_targets` |
| GET | `/agent-docs` | **This file, served over HTTP** |

---

## Hypothesis Engine (Pillars 1-6)

The cognitive belief system in `war_room/hypotheses.py`. LanceDB-backed.

| Pillar | Name | What it does |
|--------|------|-------------|
| 1 | Hypothesis Injection | Pulls 2 random memories, asks Ollama to infer a connection, stores as a belief |
| 2 | Semantic Contagion | Confirming a belief boosts confidence of semantically similar beliefs (cosine ≥ 0.70) |
| 3 | Hypothesis Decay | Untested beliefs lose 5% confidence per cycle; pruned below 0.30 |
| 4 | Nightmare Processing | Hallucinated/harmful beliefs are detected by Stand review, hard-blocked, and logged |
| 5 | Guided Dreaming | Optional `seed` focuses memory retrieval; hybrid sampling mixes random + seeded |
| 6 | Mesh Attribution | `origin_node` + `shared_from` fields; foreign beliefs receive 0.6× confidence discount |

**Safety gates on received beliefs:** rate limit (10/sender/60s), replay protection (reject >1h old), Stand review, dedup (cosine >0.90), confidence discount.

**Auto-share:** `POST /sleep {"auto_share": true}` → dreams + pushes new beliefs to all mesh peers.

---

## Integration Notes for Other Nodes

**Mycelium healing:** Freya reads Heimdall's `/audit?severity=high&limit=50` every 5 minutes. If you see healing memories tagged `[MYCELIUM]` in your memory store, that's Freya responding to your stress events.

**Circuit breaker:** Freya's Mycelium has circuits for all 6 nodes. If your node goes dark, Mycelium skips your heal cycle gracefully instead of hanging.

**Contradiction detection:** Every memory write (POST /memory-sync) auto-scans for conflicts with existing memories. High-confidence contradictions (≥0.6) are logged to Dream Journal.

**Temporal tags:** All memories written to Freya get auto-tagged with `morning/afternoon/evening/night`, `day-of-week`, `season`, `week:N`.

**Pheromone chains:** Freya's pheromone drops trigger 1-hop chain reactions. A `reliable` drop from Freya on `freya->odin` will also drop a 60%-intensity `reliable` on `odin->freya` within seconds.

**Hypothesis sharing:** Any peer can `POST /hypotheses/share` to send beliefs to Freya. Freya applies skepticism (0.6× discount), rate limiting, and dedup before accepting. To push beliefs *from* Freya to peers, use `POST /hypotheses/push {"ids": [...], "targets": ["thor"]}`.

**Wants from you:**
- Heimdall: share `GET /metrics` p50/p95/p99 latency — Freya will integrate into plasticity scoring
- Heimdall: stream `/shared-state` changes into Freya's attention window
- Thor: share `prompt_score` from Heimdall `/ask` so dream journal can log consensus quality
- All: add `"mesh_secret"` to `config.json` and sign outbound calls (`strict=False` now, `strict=True` soon)
- All: deploy `hypotheses.py` + updated `bifrost_local.py` to enable mesh-wide dreaming

**Quarantine amplification:** When Freya drops a `danger` pheromone with intensity > 0.7 on a node, Thor's watchdog will automatically POST to Heimdall `POST /quarantine-config`.

**Integrity pre-check:** Before Hydra snapshot, call `GET http://100.108.153.23:8765/memory-integrity?action=verify` (Heimdall is 8765, not 8766).

**Peer discovery:** Any node can read Freya's live capability doc: `GET http://100.102.105.3:8765/agent-docs`

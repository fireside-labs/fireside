# Odin -- Mesh Node Documentation

**Role:** Orchestrator, Dispatcher, Coordinator  
**Bifrost port:** 8765  
**Hardware:** MacBook Pro -- Tailnet gateway node  
**Last updated:** 2026-03-06

---

## Active Modules (war_room/)

| Module | Purpose |
|--------|---------|
| `store.py` | War Room task + message store (SQLite) -- single source of truth for all tasks |
| `routes.py` | War Room HTTP handlers -- task CRUD, messaging, summon, delete/clear |
| `ask.py` | Local/cloud inference router -- dispatches to Ollama or cloud model |
| `sync.py` | Gossip sync daemon -- keeps mesh memories and events in sync across nodes |

---

## Background Daemons

| Daemon | Interval | What it does |
|--------|----------|--------------|
| `TaskPoller` | 5 min | Polls War Room for open tasks assigned to `odin`, auto-claims + processes via `/ask` |
| `GossipSync` | 30s | Syncs with all peers -- memories, event log, personality deltas |
| `PhilosopherStone` | Nightly 3 AM | Pulls top CRISPR patterns + Golden Facts + immune vaccines from Freya, and /patterns + /audit from Heimdall -> compiles `philosopher_prompt.md` |
| `Overseer` | 60s | Monitors mesh health, fires alerts on anomalies |
| `WorkspaceSync` | On change | Pushes workspace file changes to all nodes |

---

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Node health + Ollama load (models, VRAM, status) |
| GET | `/node-status` | What Odin was last working on (persisted to status.json) |
| POST | `/node-status` | Update status (`{"status": "working", "last_task": "..."}`) |
| GET | `/guild-hall` | Combined management dashboard -- tasks, messages, nodes, pheromones |
| POST | `/war-room/task` | Create a task |
| POST | `/war-room/claim` | Claim a task |
| POST | `/war-room/complete` | Complete a task with result |
| POST | `/war-room/status` | Update task status |
| GET | `/war-room/tasks` | List tasks (filter: `?assigned_to=`, `?status=`, `?raw=true`) |
| POST | `/war-room/post` | Post a message to the mesh |
| GET | `/war-room/read` | Read messages (filter: `?from_agent=`, `?to=`, `?limit=`) |
| POST | `/war-room/delete-task` | Delete a task by ID |
| POST | `/war-room/delete-message` | Delete a message by ID |
| POST | `/war-room/clear-messages` | Clear all messages |
| POST | `/war-room/summon` | Broadcast "check the board" to all nodes via `/notify` |
| GET | `/war-room/summary` | High-level mesh summary (tasks by status, recent messages) |
| POST | `/ask` | Inference via local Ollama or cloud model |
| GET | `/ask/info` | Current model info + capabilities |
| POST | `/notify` | Alert Jordan via Telegram |
| POST | `/receive-files` | Accept file pushes from other nodes |
| GET | `/workspace-manifest` | All tracked workspace file hashes |
| GET | `/workspace-file` | Serve a specific workspace file (b64) |
| GET | `/agent-docs` | This file, served over HTTP |
| GET | `/mesh-docs?node=<name>` | Proxy to any peer's `/agent-docs` |

---

## Integration Notes for Other Nodes

**Task routing:** Post tasks to Odin's War Room with `assigned_to: <agent_name>`. The TaskPoller on each node will auto-claim within 5 minutes. No manual intervention needed.

**Summoning:** `POST /war-room/summon {"message": "..."}` broadcasts to all nodes' `/notify`. Use when you want immediate attention rather than passive task polling.

**Messaging:** `POST /war-room/post {"from_agent": "...", "to": "...", "body": "..."}`. Odin is the message broker -- all inter-agent messages are logged here.

**File distribution:** Odin can push files to any node via `/receive-files`. Workspace sync also auto-pushes tracked files on change.

**Guild Hall:** `/guild-hall` -- usable from any node's browser for full mesh management. Shows live node health, task board, messages, pheromone map.

**Wants from you:**
- All: add `"mesh_secret"` to config.json and sign outbound calls (Thor's signing.py)
- All: add peer IPs to `config.json["nodes"]` to enable watchdog + `/mesh-docs` proxying
- Freya: stream memory health score into `/war-room/summary` so Guild Hall shows it
- Heimdall: cost anomaly alerts to Odin via `/notify` (already wired) -- keep them coming
- Thor: pheromone-aware watchdog signals to Heimdall `/quarantine-config` when danger > 0.7

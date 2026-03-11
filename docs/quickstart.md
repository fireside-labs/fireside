# Quickstart — Running in 5 Minutes

---

## Prerequisites

| What | Why |
|---|---|
| **Python 3.11+** | Bifrost backend |
| **Node.js 18+** | Dashboard (Next.js) |
| **Ollama _or_ oMLX** | Local inference (or an NVIDIA API key for cloud) |

Already have a model running? Skip to [Start](#3--start).

---

## 1 — Clone

```bash
git clone https://github.com/openclaw/valhalla-mesh-v2.git
cd valhalla-mesh-v2
```

---

## 2 — Install Dependencies

```bash
# Backend
pip install fastapi uvicorn pyyaml pydantic

# Dashboard
cd dashboard && npm install && cd ..
```

---

## 3 — Start

Two terminals:

**Terminal 1 — Backend:**
```bash
python bifrost.py
```

```
01:42:15 │ valhalla.bifrost             │ INFO  │ ═══════════════════════════════════════════════
01:42:15 │ valhalla.bifrost             │ INFO  │   Valhalla Bifrost V2
01:42:15 │ valhalla.bifrost             │ INFO  │   Node: odin (orchestrator)
01:42:15 │ valhalla.bifrost             │ INFO  │ ═══════════════════════════════════════════════
01:42:15 │ valhalla.bifrost             │ INFO  │ Plugins loaded: 2
01:42:15 │ valhalla.bifrost             │ INFO  │ API v1 mounted at /api/v1/
01:42:15 │ valhalla.bifrost             │ INFO  │ Starting Bifrost on 0.0.0.0:8765
```

**Terminal 2 — Dashboard:**
```bash
cd dashboard && npm run dev
```

```
  ▲ Next.js 15.x
  - Local: http://localhost:3000
```

Open **http://localhost:3000**.

---

## 4 — What You See

The dashboard has a sidebar with six pages:

| Page | What It Shows | API It Calls |
|---|---|---|
| **Nodes** | Your mesh nodes as live cards — name, role, status, model, uptime | `GET /api/v1/nodes` |
| **Models** | Current model + alias buttons (⚡ Odin, 🧠 Hugs, 🌙 Moon) — click to switch | `GET /api/v1/status`, `POST /api/v1/model-switch` |
| **Soul Editor** | Split-pane markdown editor for IDENTITY / SOUL / USER files | `GET/PUT /api/v1/soul/{file}` |
| **Config** | Full `valhalla.yaml` in a code editor with syntax highlighting | `GET/PUT /api/v1/config` |
| **Plugins** | Installed plugins with status | `GET /api/v1/plugins` |
| **War Room** | Hypotheses, predictions, self-model _(Sprint 2)_ | `GET /api/v1/hypotheses` |

---

## 5 — Try Things

### Switch models

From the **Models** page, click an alias button. Or via API:

```bash
curl -X POST http://localhost:8765/api/v1/model-switch \
  -H 'Content-Type: application/json' \
  -d '{"alias": "hugs"}'
```

### Edit your agent's soul

From the **Soul Editor** page, pick the IDENTITY tab. Change your agent's name and personality. Hit Save. Or via API:

```bash
# Read
curl http://localhost:8765/api/v1/soul/IDENTITY.odin.md

# Write
curl -X PUT http://localhost:8765/api/v1/soul/IDENTITY.odin.md \
  -H 'Content-Type: application/json' \
  -d '{"content": "# IDENTITY.md - Odin\n\n- **Name:** Odin\n- **Role:** Orchestrator\n"}'
```

### Check node status

```bash
curl http://localhost:8765/api/v1/status
# → {"node":"odin","role":"orchestrator","model":"llama/Qwen3.5-35B-A3B-8bit","uptime":...}
```

### Edit config

From the **Config** page, edit `valhalla.yaml` directly in the browser. Save hot-reloads the config — no restart needed.

---

## 6 — Add a Second Node

Got another machine? One command:

```bash
# On the second machine (after installing valhalla):
valhalla join odin@<your-ip>:8765
```

The node appears in the dashboard automatically. See [Add-a-Node Guide](add-a-node.md) for the full flow.

---

## Config Reference

Your node config lives in `valhalla.yaml` at the project root. Key sections:

```yaml
node:
  name: odin          # This node's name
  role: orchestrator   # orchestrator | backend | memory | security | worker
  port: 8765          # Bifrost port

models:
  default: llama/Qwen3.5-35B-A3B-8bit   # Active model on startup
  aliases:
    odin: llama/Qwen3.5-35B-A3B-8bit    # ⚡ local
    hugs: nvidia/z-ai/glm-5              # 🧠 cloud
    moon: nvidia/moonshotai/kimi-k2.5    # 🌙 cloud

plugins:
  enabled: [model-switch, watchdog]       # Loaded at startup

soul:
  identity: mesh/souls/IDENTITY.odin.md
  personality: mesh/souls/SOUL.odin.md
  user_profile: mesh/souls/USER.odin.md
```

Environment variables work anywhere: `${NVIDIA_API_KEY}` is resolved from your shell environment at startup.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: fastapi` | `pip install fastapi uvicorn pyyaml pydantic` |
| Dashboard shows "Failed to fetch" | Is Bifrost running? Check Terminal 1. |
| Model switch says "Unknown alias" | Check `models.aliases` in `valhalla.yaml` |
| Port 8765 already in use | `python bifrost.py --port 8766` or kill the old process |
| Dashboard port 3000 taken | `cd dashboard && PORT=3001 npm run dev` |

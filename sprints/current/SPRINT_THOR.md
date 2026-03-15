# Sprint 8 — THOR (Backend: Orchestration Engine + Hosted Foundation)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).

> [!IMPORTANT]
> **Read `FEATURE_INVENTORY.md`** and the plugin directory structure.
> The companion is an ORCHESTRATOR. It doesn't do the work — it routes tasks to the right plugin/agent.
> Don't build an email client. Build the routing layer that makes the mesh accessible from mobile.

---

## Context

The companion already has 29 plugins — browse, voice, pipeline, working-memory, predictions, hypotheses, model-router, etc. But the mobile app can only access companion-specific features. Sprint 8 makes the FULL MESH accessible from the phone through intelligent routing.

Key philosophy: The companion doesn't try to be Gmail (Gemini does that) or Outlook (Copilot does that). The companion cross-references everything — browsing history, memories, tasks, conversations, predictions — and routes tasks to the right agent. That's what nobody else offers.

---

## Your Tasks

### Task 1 — Smart Task Router
Create `plugins/companion/router.py` — analyzes user intent and routes to the right plugin:

```python
PLUGIN_CAPABILITIES = {
    "browse": {
        "triggers": ["look up", "search for", "find", "what is", "research", "summarize this page"],
        "description": "Web browsing and page summarization"
    },
    "voice": {
        "triggers": ["say", "speak", "read aloud", "pronounce"],
        "description": "Text-to-speech and speech-to-text"
    },
    "pipeline": {
        "triggers": ["run", "execute", "process", "analyze", "create a report"],
        "description": "Multi-stage task processing"
    },
    "working-memory": {
        "triggers": ["remember", "what did I say", "recall", "last time", "we talked about"],
        "description": "Memory retrieval and context"
    },
    "predictions": {
        "triggers": ["predict", "forecast", "what will", "likelihood"],
        "description": "Predictions and forecasting"
    },
    "companion": {
        "triggers": ["how are you", "feed", "walk", "adventure", "translate"],
        "description": "Companion care and interaction"
    }
}
```

Endpoint: `POST /api/v1/companion/route`
```json
// Request:
{ "intent": "research the latest trends in AI agents" }

// Response:
{
  "routed_to": "browse",
  "plugin": "browse",
  "action": "research",
  "confidence": 0.85,
  "status": "queued",
  "task_id": "abc123"
}
```

Use the LLM to classify intent if keyword matching isn't confident enough. Fall back to chat if nothing matches.

### Task 2 — Cross-Context Query API
Create `POST /api/v1/companion/query` — searches across ALL context sources:

```json
// Request:
{ "query": "What did we discuss about the marketing strategy?" }

// Response:
{
  "results": [
    { "source": "working-memory", "content": "On March 10, you mentioned wanting to focus on developer marketing...", "relevance": 0.92 },
    { "source": "chat-history", "content": "In conversation on March 8...", "relevance": 0.78 },
    { "source": "predictions", "content": "Prediction: developer adoption rate estimated at 45%...", "relevance": 0.65 }
  ]
}
```

Query across: working-memory, chat history, taught facts (TeachMe), predictions, hypotheses. Return ranked results.

This is the killer feature — "What do you know about X?" and the companion searches its entire mesh brain.

### Task 3 — Agent Status API
Create `GET /api/v1/mesh/status` — what the mesh is doing right now:

```json
{
  "agents": [
    { "name": "Odin", "status": "online", "current_task": "idle", "uptime": "12h" },
    { "name": "Bragi", "status": "online", "current_task": "processing pipeline: quarterly report", "progress": 65 }
  ],
  "plugins_active": 12,
  "models_loaded": ["qwen-14b", "whisper-large", "nllb-200"],
  "queued_tasks": 3,
  "last_activity": "2026-03-15T14:30:00Z"
}
```

Pull from existing plugin registries, model-router, pipeline status, event-bus.

### Task 4 — Hosted Mode Auth (Supabase)
Set up the foundation for hosted mode using Supabase Auth (as recommended by Heimdall):

1. Add `supabase` Python client
2. Create `plugins/auth/handler.py`:
   - `POST /api/v1/auth/signup` — email + password → Supabase
   - `POST /api/v1/auth/login` — returns JWT
   - `POST /api/v1/auth/refresh` — refresh token rotation
3. Middleware that checks `Authorization: Bearer <jwt>` for hosted mode
4. Self-hosted mode skips auth (existing behavior preserved)

The auth is the infrastructure. The actual hosted container provisioning (RunPod/Modal) is Sprint 9+.

### Task 5 — Hosted Mode Routing
Add a config flag: `HOSTED_MODE = os.getenv("FIRESIDE_HOSTED", "false")`

When `HOSTED_MODE=true`:
- All endpoints require JWT auth
- CORS allows `https://app.fireside.ai`
- HTTPS/WSS enforced
- Privacy policy endpoint returns hosted-specific text

When `HOSTED_MODE=false` (self-hosted, default):
- Existing behavior, no auth required
- CORS allows local IPs

### Task 6 — Drop Your Gate
Create `sprints/current/gates/gate_thor.md` using write_to_file.

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

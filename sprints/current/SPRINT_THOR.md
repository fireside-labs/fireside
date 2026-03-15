# Sprint 10 — THOR (Backend: Two-Character System + Install Flow v2)

// turbo-all

**Your role:** Backend engineer. Python, FastAPI, bash.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_thor.md` when complete.

> [!IMPORTANT]
> **READ FIRST:** `VISION.md` — the product vision. This sprint implements the two-character system.

---

## Context

Currently, the install flow creates ONE character — the companion animal IS the AI. In this sprint, we split this into TWO characters:
1. **AI Agent** — a person with a name, personality style, and human avatar. Lives at home, runs the guild hall.
2. **Companion** — the animal (cat/dog/fox/penguin/owl/dragon). Goes with the user on their phone.

The companion relays to the AI agent for hard tasks. The AI agent appears in the guild hall on the dashboard.

---

## Your Tasks

### Task 1 — Update install.sh

Add Step 4 between brain selection and confirmation. The new flow:

```
Step 1: "What should we call you?" → name
Step 2: "Choose a companion" → species + name (EXISTING, keep as-is)
Step 3: "How powerful should your AI be?" → brain size (EXISTING, keep as-is)

# NEW STEP 4:
Step 4: "Now, who's running the show at home?"

  "Every companion has someone at the fireside.
   This is the mind behind [companion_name] — your AI."

  "Give your AI a name:"
  → [user types name, default: "Atlas"]

  "What's their style?"
  [1] 🎯 Analytical  — data-driven, precise, sees the patterns
  [2] 🎨 Creative    — imaginative, lateral thinker, sees the possibilities
  [3] ⚡ Direct      — no-nonsense, efficient, gets to the point
  [4] 🌿 Warm        — empathetic, supportive, reads the room

Step 5: Confirmation card (updated):
  ┌─────────────────────────────┐
  │  Owner:      Jordan         │
  │  AI:         Atlas (🎯)     │
  │  Companion:  🦊 Ember       │
  │  Brain:      Smart (7B)     │
  │  Location:   ~/.fireside    │
  └─────────────────────────────┘

Step 6: "Atlas and Ember are getting ready..."
  → (existing install + boot)
```

ASCII art for the AI at the end (after existing pet art):
```
  Atlas is at the fireside.    Ember is by their side.
       🔥                          [pet art]
```

### Task 2 — Update Config Files

Update `valhalla.yaml` generation to include agent section:

```yaml
agent:
  name: "Atlas"
  style: "analytical"    # analytical / creative / direct / warm

companion:
  species: fox
  name: "Ember"
  owner: "Jordan"
```

Update `companion_state.json` to include agent reference:

```json
{
  "species": "fox",
  "name": "Ember",
  "owner": "Jordan",
  "agent": {
    "name": "Atlas",
    "style": "analytical"
  },
  ...existing fields...
}
```

Update `onboarding.json` to include agent:

```json
{
  "onboarded": true,
  "user_name": "Jordan",
  "agent": {
    "name": "Atlas",
    "style": "analytical"
  },
  "companion": {
    "species": "fox",
    "name": "Ember"
  },
  ...existing...
}
```

### Task 3 — Agent Profile API

Create `GET /api/v1/agent/profile`:

```json
{
  "name": "Atlas",
  "style": "analytical",
  "companion": {
    "name": "Ember",
    "species": "fox"
  },
  "owner": "Jordan",
  "uptime": "4h 22m",
  "plugins_active": 12,
  "models_loaded": ["qwen-14b"],
  "current_activity": "idle"
}
```

Read from `companion_state.json` + `valhalla.yaml`. Include live data where available.

### Task 4 — Guild Hall Real Data

Update the guild hall API or data to return REAL agent state instead of the mocked `AGENTS` array in `GuildHall.tsx`. Create `GET /api/v1/guildhall/agents`:

```json
{
  "agents": [
    {
      "name": "Atlas",
      "type": "ai",
      "style": "analytical",
      "activity": "idle",
      "status": "online",
      "taskLabel": null
    },
    {
      "name": "Ember",
      "type": "companion",
      "species": "fox",
      "activity": "chatting",
      "status": "online",
      "taskLabel": "Talking to Jordan"
    }
  ]
}
```

Activity should reflect actual system state where possible:
- If a pipeline is running → `"building"` with task label
- If a browse request is active → `"researching"`
- If idle → `"idle"` (Valhalla: "Drinking mead")
- If WebSocket has active connections → companion is `"chatting"`

### Task 5 — Drop Your Gate

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

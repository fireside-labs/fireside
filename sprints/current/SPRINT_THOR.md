# Sprint 6 — THOR (Backend: Voice Streaming + Marketplace API + WebSocket)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI, `api/v1.py`, `plugins/`.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

> [!IMPORTANT]
> **Read `FEATURE_INVENTORY.md`** — you already have a `voice/` plugin (Whisper STT + Kokoro TTS)
> and a `marketplace/` plugin. This sprint surfaces them for mobile.

---

## Context

The voice plugin already exists. The marketplace plugin already exists. The browse plugin already exists. Your job is to ensure mobile can access these and to add real-time sync.

Key existing files:
- `plugins/voice/` — Whisper STT + Kokoro TTS (already implemented)
- `plugins/marketplace/` — browse, install, sell (already implemented)
- `plugins/browse/parser.py` — tree-based web page parser (already implemented)

---

## Your Tasks

### Task 1 — Voice Endpoint for Mobile
The voice plugin exists but may not have HTTP-friendly endpoints for mobile. Create or verify:

**Speech-to-Text:**
```
POST /api/v1/voice/transcribe
Content-Type: multipart/form-data
Body: audio file (webm/m4a/wav)
Response: { "text": "transcribed text", "language": "en" }
```

**Text-to-Speech:**
```
POST /api/v1/voice/speak
Body: { "text": "Hello!", "voice": "default" }
Response: audio/wav binary stream
```

These should use the existing Whisper and Kokoro models. If the voice plugin uses a different interface (e.g., WebSocket or stream), create HTTP wrapper endpoints that the mobile app can call.

The voice data must NEVER leave the local network. No cloud STT/TTS. This is a privacy feature.

### Task 2 — Marketplace API for Mobile
Verify or create mobile-friendly marketplace endpoints:

```
GET  /api/v1/marketplace/browse     — list available items (agents, themes, voice packs)
GET  /api/v1/marketplace/search?q=  — search marketplace
GET  /api/v1/marketplace/item/:id   — item detail (description, price, ratings)
POST /api/v1/marketplace/install    — install a free item
```

For paid items, integrate with the existing `payments/` plugin (Stripe). Mobile payments will need App Store IAP eventually, but for now Stripe web checkout is fine.

### Task 3 — Web Page Summary Endpoint
The `browse/parser.py` already parses web pages. Create:

```
POST /api/v1/browse/summarize
Body: { "url": "https://example.com" }
Response: { "title": "...", "summary": "...", "key_points": [...] }
```

This powers the iOS share sheet — user shares a URL from Safari, the companion summarizes it.

### Task 4 — WebSocket for Real-Time Sync
Add a WebSocket endpoint for the mobile app to get live companion state updates:

```
WS /api/v1/companion/ws
```

When companion state changes (happiness decay, task completed, adventure result, chat message from desktop), push an event to connected mobile clients. This replaces the pull-to-refresh polling model.

Events to broadcast:
- `companion_state_update` — happiness, XP, level changes
- `task_completed` — task queue item finished
- `chat_message` — message from desktop chat
- `notification` — push notification content

### Task 5 — Fix Morning Briefing Placeholders (🟢 LOW from Heimdall Sprint 5)
When platform data is unavailable, return `null` fields instead of fake data. The frontend should show "data unavailable" instead of random numbers.

### Task 6 — Drop Your Gate
Create `sprints/current/gates/gate_thor.md` using write_to_file:

```markdown
# Thor Gate — Sprint 6 Backend Complete
Sprint 6 tasks completed.

## Completed
- [x] Voice endpoints (transcribe + speak) via existing Whisper/Kokoro
- [x] Marketplace browse/search/detail/install endpoints
- [x] Web page summary endpoint (via browse/parser.py)
- [x] WebSocket for real-time companion sync
- [x] Morning briefing placeholder fix
```

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
- Read `sprints/current/gates/audit_heimdall.md` if gate is deleted

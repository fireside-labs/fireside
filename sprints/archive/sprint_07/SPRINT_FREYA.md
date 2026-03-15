# Sprint 8 — FREYA (Frontend: Executive Toolkit + Hosted Mode + Polish)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

> [!IMPORTANT]
> **READ FIRST:** `sprints/current/PROPOSAL_SPRINT8.md` — this sprint includes a major product expansion
> (hosted mode + executive toolkit). Review agent feedback before building.

---

## Context

Sprint 7 made the app TestFlight-ready. Sprint 8 makes it **market-ready**.

Two big additions:
1. **Hosted mode** — users without a home PC can sign up and get a cloud-hosted AI
2. **Executive toolkit** — email triage, calendar, document creation via voice

The mobile app code barely changes for hosted mode — it's mostly a routing layer in `api.ts`.

---

## Your Tasks

### Task 1 — Settings Screen
Build `mobile/app/settings.tsx` (modal or screen, accessible from gear icon):

1. **Mode switch** — "Companion Mode" ↔ "Executive Mode" (renamed from Pet/Tool)
2. **Connection** — Status indicator, host IP, re-pair button, connection mode (self-hosted/hosted)
3. **Companion** — Name display, species (read-only)
4. **Voice** — Enable/disable, voice picker (Aria, Nova, Kai, Luna, Zephyr)
5. **Notifications** — Category toggles
6. **Privacy** — Data location explainer ("All on your PC" vs "Hosted on Fireside")
7. **About** — Version, build number

### Task 2 — Hosted Mode Connection
Update `api.ts` and onboarding to support hosted mode:

1. Add `connectionMode: "selfhosted" | "hosted"` to AsyncStorage
2. Hosted base URL: `https://api.fireside.ai/v1`
3. Auth: JWT token stored in AsyncStorage (from email signup or OAuth)
4. `apiFetch` checks `connectionMode` and routes to the right base URL
5. Graceful fallback: if hosted API returns 404 on executive endpoints, show "Coming soon"

### Task 3 — Onboarding v2
Rebuild onboarding flow:

1. **Welcome** — "Your private AI assistant"
2. **How do you want to connect?**
   - "I have a home PC running Fireside" → QR scan / manual IP
   - "Set up for me" → email signup → hosted mode (show "launching your AI...")
3. **Choose your experience:**
   - 🐾 "Companion Mode" — friendly AI that grows with you
   - 💼 "Executive Mode" — AI chief of staff for email, calendar, docs
4. **Name your AI**
5. **Permissions** — mic, notifications, camera
6. **Done** — mode-appropriate welcome ("Say 'Hey [name], what's on my calendar?'" for executive)

### Task 4 — Executive Command Center
Build `mobile/src/ExecutiveHub.tsx` — shown in Executive Mode's Tools tab:

**Email Card:**
- `GET /api/v1/executive/inbox` → unread count, priority emails
- Tap email → AI summary + suggested reply
- "Approve & Send" / "Edit Reply" buttons
- Empty state: "Connect your email in Dashboard Settings"

**Calendar Card:**
- `GET /api/v1/executive/calendar` → today's timeline
- Next meeting highlighted with prep button
- "Reschedule" → natural language input
- Empty state: "Connect your calendar in Dashboard Settings"

### Task 5 — Document Commands
Build `mobile/src/DocumentCommands.tsx`:

**Quick action buttons:**
- 📊 "Create Spreadsheet" → prompt input → `POST /executive/document/create`
- 📑 "Create Presentation" → prompt input → shows progress → "Ready on PC"
- 📝 "Summarize Document" → paste/upload text → key points + action items
- Recent documents list with status badges

### Task 6 — Agent Profile Card
Port from dashboard `AgentProfile.tsx`:

- Mood avatar, level, XP bar, title
- Stats: Intelligence, Loyalty, Memory, Speed
- Personality traits
- Achievement count, time together
- Accessible from avatar tap or settings

### Task 7 — Drop Your Gate
Create `sprints/current/gates/gate_freya.md` using write_to_file.

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

---

## Notes
- "Executive Mode" replaces "Tool Mode" in UI labels. The `ModeContext` value stays `tool` internally.
- Hosted mode APIs may not exist yet — build UI with graceful "Coming soon" fallbacks everywhere.
- Voice is the executive's primary input. Every feature should be reachable through conversation.
- This sprint establishes the business model. The app becomes a product, not just a project.

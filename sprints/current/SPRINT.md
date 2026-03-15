# Sprint 8 — Orchestration + Hosted Mode Infrastructure

**Goal:** Make the companion the smartest orchestrator on your phone — it doesn't try to be Gmail or Outlook, it routes tasks to the right mesh agents and gives you cross-context intelligence nobody else has. Also lay the foundation for hosted mode (the business model).

**Key insight:** Gemini is in Gmail. Copilot is in Outlook. We don't compete with that. We win because the companion cross-references EVERYTHING (browsing, memories, tasks, conversations) and runs PRIVATELY on your hardware.

---

## Sprint 8 Scope

### Thor (Backend) — Orchestration Engine + Hosted Foundation
- Smart task routing: companion analyzes user intent → routes to best agent/plugin
- Cross-context queries: "What did we talk about last week related to [topic]?"
- Agent status API: which agents are active, what they're working on
- Hosted mode auth foundation (JWT signup/login via Supabase)
- Hosted mode routing middleware

### Freya (Frontend) — Orchestration UI + Settings + Onboarding v2
- Smart command bar: natural language → routed to right agent
- Agent activity feed: what your mesh agents are doing right now
- Settings screen (mode switch, connection, voice, notifications)
- Onboarding v2: self-hosted (QR) vs hosted (email signup)
- Rename Tool Mode → Executive Mode in UI

### Heimdall — Hosted mode security review
- Auth flow (Supabase integration)
- HTTPS/WSS requirement for hosted mode
- Container isolation architecture

### Valkyrie — Orchestration UX + positioning review
- Does the orchestration UI feel like magic or complexity?
- Hosted onboarding: is it simple enough for a non-technical exec?
- Positioning: "The only AI that knows you" vs "AI email assistant"

---

## Definition of Done

- [ ] Smart task routing works (user says intent → companion routes to agent)
- [ ] Cross-context queries return relevant results from memory + conversations
- [ ] Agent activity feed shows what mesh agents are doing
- [ ] Settings screen with mode switch + connection info
- [ ] Onboarding v2 with self-hosted + hosted paths
- [ ] Hosted auth via Supabase (signup/login/JWT)
- [ ] All gates dropped

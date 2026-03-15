# Sprint 10 — Two Characters: AI Person + Companion Animal

**Goal:** Implement the two-character system from VISION.md. Users create an AI person (lives at home, runs the guild hall) AND a companion animal (goes with them on their phone). The install flow, config, dashboard, and mobile app all update to support both characters.

**Read first:** `VISION.md` — the product bible.

---

## Sprint 10 Scope

### Thor (Backend)
- Update install.sh with Step 4 (create AI person — name, style, avatar)
- Update config/state to store both AI agent and companion separately
- API endpoint for AI agent profile (`GET /api/v1/agent/profile`)
- Guild hall agent data wired to real config (not mocked)

### Freya (Frontend)
- Dashboard: guild hall reads real agent config, shows AI person + companion together
- Dashboard: onboarding wizard updated for two-character flow
- Mobile: companion references the AI by name ("Let me check with Atlas...")
- Mobile: agent profile card shows both characters

### Heimdall — Audit the two-character system
- No credential leaks in new config
- Agent profile endpoint security

### Valkyrie — UX review
- Does the two-character narrative make sense to a new user?
- Is the install flow ordering right?
- Does the guild hall feel alive with both characters?

---

## Definition of Done
- [ ] install.sh has 6 steps (name, companion, brain, AI persona, confirm, launch)
- [ ] Config stores both `companion` and `agent` sections
- [ ] Guild hall shows real agent data, not mocks
- [ ] Companion on mobile references AI by name
- [ ] All gates dropped

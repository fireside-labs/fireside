# Sprint 5 — The Mode Split: Pet vs Tool + Platform Bridge

**Goal:** Make the companion serve two personas — the user who wants a Tamagotchi and the user who wants a private AI utility. Add translation, morning briefings, proactive guardian, and surface what the home PC is doing.

**Valkyrie's thesis:** *"The app creates attachment but doesn't yet create a bridge to the broader platform."*

**Input:** `sprints/archive/sprint_04/gates/review_valkyrie.md` + `audit_heimdall.md`

---

## Sprint 5 Scope

### Thor (Backend)
- Fix adventure rewards from client body (MEDIUM from Heimdall)
- Add `/mobile/unregister-push` endpoint (LOW carried from Sprint 3)
- Surface "home PC activity" in sync response (dream cycles, memory count, uptime)
- Server-side encounter storage for adventure rewards
- Proactive guardian: time-aware greeting when user opens chat late at night

### Freya (Frontend)
- **Companion Mode Toggle** — Pet mode (quests/feeding/gamification) vs Tool mode (guardian/translate/tasks)
- **Translation UI** — 200-language translator (backend: `nllb.py`)
- **Morning Briefing** — push notification + in-app card for daily updates
- **TeachMe** — teach companion facts, personality deepens
- **"What's Happening at Home" card** — show platform activity on Care tab
- **Proactive guardian** — time-aware opening message at 2AM

### Heimdall — Same strict rules
- 🔴 HIGH → automatic FAIL
- 🟡 MEDIUM → PASS with notes
- 🟢 LOW → informational

### Valkyrie — Full platform review
- **MUST READ:** `FEATURE_INVENTORY.md`
- Assess mode toggle UX (does it feel natural, not confusing?)
- Does "Tool mode" feel useful enough to stand alone?
- Does the platform bridge create curiosity about the desktop?
- Remaining gaps for App Store submission

---

## Definition of Done

- [ ] Mode toggle exists and works (Pet ↔ Tool)
- [ ] Translation UI works (select language, translate text)
- [ ] Morning briefing appears as push + in-app card
- [ ] TeachMe works on mobile
- [ ] "What's Happening at Home" card shows platform activity
- [ ] Proactive guardian greets appropriately at 2AM
- [ ] Adventure rewards fixed (server-side lookup)
- [ ] All gates dropped

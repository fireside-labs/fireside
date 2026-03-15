# Sprint 8 — Hosted Mode + Executive Toolkit

**Goal:** Expand from a self-hosted-only product to a dual-mode platform (self-hosted + cloud hosted), add an executive toolkit (email, calendar, documents), and establish the revenue model.

**Process change:** This sprint starts with a **proposal review phase**. Each agent reads `PROPOSAL_SPRINT8.md` and drops feedback before implementation begins.

---

## Phase 1 — Proposal Review (ALL AGENTS)

Each agent reads `PROPOSAL_SPRINT8.md` and drops their feedback:
- `sprints/current/gates/feedback_thor.md` — technical feasibility
- `sprints/current/gates/feedback_heimdall.md` — security architecture
- `sprints/current/gates/feedback_valkyrie.md` — business viability + UX

**Owner reviews all feedback before greenlighting implementation.**

---

## Phase 2 — Implementation

### Thor (Backend)
- Executive plugins: email (IMAP/SMTP), calendar (CalDAV), documents (pptx/xlsx)
- Hosted mode API foundation (JWT auth, user routing)
- Achievement backend (from Sprint 7)

### Freya (Frontend)
- Settings screen, onboarding v2 (self-hosted vs hosted)
- Executive command center (email card, calendar card, document commands)
- Agent profile card
- Mode rename: "Tool" → "Executive"

### Heimdall (Security)
- Hosted mode threat model
- Email credential encryption audit
- JWT + container isolation review

### Valkyrie (Review)
- Business viability assessment
- Executive UX: cohesive or duct-taped?
- Pricing validation
- Conversion path mapping

---

## Definition of Done

- [ ] All 4 feedback files dropped (Phase 1)
- [ ] Owner approves proposal
- [ ] Executive email/calendar/documents endpoints
- [ ] Hosted mode auth + routing foundation
- [ ] Mobile onboarding v2 with hosted option
- [ ] Executive Hub UI
- [ ] All gates dropped

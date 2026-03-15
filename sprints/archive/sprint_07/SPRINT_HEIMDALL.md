# Sprint 8 — HEIMDALL (Security: Hosted Mode Audit + Executive Data Protection)

// turbo-all

**Your role:** Security auditor & QA.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_heimdall.md` when complete.

> [!IMPORTANT]
> **READ FIRST:** `sprints/current/PROPOSAL_SPRINT8.md` — review the business proposal and
> drop your feedback at `sprints/current/gates/feedback_heimdall.md` before auditing.

---

## Context

Sprint 8 introduces hosted mode (multi-tenant cloud) and executive features (email, calendar, documents). This is the highest security stakes sprint — we're now handling user email credentials, corporate calendar data, and document contents. Your audit is critical.

---

## Your Tasks

### Task 1 — Review Business Proposal
Read `PROPOSAL_SPRINT8.md` and write **security-focused** feedback to `sprints/current/gates/feedback_heimdall.md`:
- Threat model for hosted multi-tenant architecture
- Email credential storage requirements
- Data isolation between hosted users
- Auth flow review (JWT, OAuth, token handling)
- Compliance considerations (GDPR, SOC2)

### Task 2 — Audit Sprint 8 Code
After Thor and Freya complete their work, audit:
- Email credential encryption (must be Fernet/AES at rest, NOT plaintext)
- JWT implementation (expiration, refresh, revocation)
- Container isolation (no cross-user data leakage)
- WebSocket auth (from Sprint 7 + hosted mode changes)
- API input validation on all new executive endpoints
- IMAP/SMTP connection security (TLS required, cert verification)

### Task 3 — Write Audit Report
`sprints/current/gates/audit_heimdall.md` with findings rated HIGH/MEDIUM/LOW.

### Task 4 — Drop Your Gate

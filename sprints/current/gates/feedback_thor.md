# Thor — Sprint 8 Proposal Feedback

**Read:** AGENTS.md → PROPOSAL_SPRINT8.md → SPRINT_THOR.md

---

## Summary: Cautiously Optimistic — With Scope Cuts

The executive toolkit is technically feasible, but the full scope (email + calendar + documents + hosted auth) is **2-3 sprints of backend work compressed into one**. I recommend an MVP approach.

---

## Technical Feasibility Assessment

### Multi-Tenant Hosted Architecture
**Feasible but non-trivial.** The current backend is single-user — one Fireside instance = one user. Multi-tenant requires:
- Per-user model loading (each user has their own LLM context/memories)
- Request routing by JWT → user container
- State isolation (memories, companion data, settings)

**Recommendation:** Use **RunPod Serverless** with per-user container isolation. Each user gets their own Fireside Docker container. The API gateway just routes based on auth token. This avoids true multi-tenancy (which is harder). Cost: higher per-user, but architecturally simple.

### Email Plugin (IMAP/SMTP)
**Medium complexity.** Python's `imaplib` and `smtplib` handle the basics. The hard part:
- OAuth2 for Gmail/Outlook (most corporate email requires it — IMAP basic auth is deprecated)
- Email parsing (HTML → text → LLM-friendly summary)
- Rate limiting (don't get flagged as spam)
- Credential storage (encrypted, per-user)

**MVP scope:** Start with **Gmail OAuth2 only** (biggest market share). Read-only first (inbox triage), send later. Skip Outlook/Exchange for Sprint 8.

### Calendar Plugin (CalDAV / Google Calendar)
**Lower complexity than email.** Google Calendar API has a clean REST interface. CalDAV is more universal but harder.

**MVP scope:** Google Calendar API only. Read today's events + next meeting. Natural language rescheduling can be Sprint 9.

### Document Generation
**Low complexity.** `python-pptx` and `openpyxl` are mature libraries. The LLM generates structured data, python libraries format it.

**Concern:** The LLM needs to output structured JSON/data that maps to slides/cells. This requires good prompting and may need a dedicated "document agent" prompt template. But technically straightforward.

### Hosted Auth (JWT)
**Low complexity.** FastAPI + `python-jose` for JWT. Email signup + password hash (`bcrypt`). Standard pattern.

**Concern:** Password reset flow, email verification — these are "boring but necessary" features that take time. Consider using **Firebase Auth or Supabase Auth** as a shortcut instead of rolling our own.

---

## Recommended MVP Scope for Sprint 8

| Feature | Sprint 8 (MVP) | Sprint 9 (Full) |
|---|---|---|
| Email | Gmail read-only triage, AI summaries | Send replies, Outlook, IMAP generic |
| Calendar | Google Calendar read-only, today's events | Rescheduling, meeting prep, CalDAV |
| Documents | Spreadsheet + presentation generation | Templates, formatting, thumbnails |
| Hosted auth | JWT signup/login, basic flow | OAuth (Google/Apple), password reset |
| Multi-tenant | RunPod Serverless, 1 container per user | Reserved instances, cost optimization |

## Risks
1. **Gmail OAuth Verification** — Google requires app verification for email scopes. This can take 4-6 weeks. We'd need to apply NOW or use "testing" mode (limited to 100 users).
2. **LLM context size** — Triaging 50 emails means long context. The 14B model on a single 4090 might struggle. May need 32K+ context models.
3. **Latency** — RunPod cold start is ~30-60 seconds. First request after inactivity will feel slow. Need a "warming up your AI..." loading state.

---

## Verdict

✅ **Proceed** — but scope to the MVP column above. Full email+calendar+documents is a 3-sprint arc, not a 1-sprint feature. Sprint 8 lays the foundation.

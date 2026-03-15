# Sprint 8 — THOR (Backend: Executive APIs + Hosted Infrastructure)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).

> [!IMPORTANT]
> **READ FIRST:** `sprints/current/PROPOSAL_SPRINT8.md` — review the business proposal and
> drop your feedback at `sprints/current/gates/feedback_thor.md` before implementing.

---

## Context

Sprint 8 adds executive productivity features and the foundation for hosted mode. Freya is building the frontend; you're building the API layer and plugins. The proposal includes email, calendar, and document generation — focus on what's achievable this sprint.

---

## Your Tasks

### Task 1 — Review Business Proposal
Read `PROPOSAL_SPRINT8.md` and write feedback to `sprints/current/gates/feedback_thor.md`:
- Technical feasibility of multi-tenant hosted architecture
- IMAP/CalDAV integration complexity
- Document generation approach (python-pptx, openpyxl)
- Suggested MVP scope cuts if needed

### Task 2 — Executive Email Plugin
Build `plugins/executive/email.py`:
- IMAP connection (configurable via dashboard settings)
- `GET /api/v1/executive/inbox` — fetch unread, AI-triage with priority scoring
- `POST /api/v1/executive/email/send` — send reply via SMTP
- `POST /api/v1/executive/email/draft` — AI generates reply, returns draft
- Store email credentials encrypted (Fernet or similar)

### Task 3 — Executive Calendar Plugin
Build `plugins/executive/calendar.py`:
- CalDAV or Google Calendar API integration
- `GET /api/v1/executive/calendar` — today's events + next meeting
- `POST /api/v1/executive/calendar/reschedule` — natural language → calendar update
- `GET /api/v1/executive/meeting-prep/{id}` — cross-reference with emails

### Task 4 — Document Generation Plugin
Build `plugins/executive/documents.py`:
- `POST /api/v1/executive/document/create` — `{ type: "spreadsheet"|"presentation"|"summary", prompt }`
- Spreadsheets via openpyxl
- Presentations via python-pptx
- Returns file path + status
- File saved to user's configured output directory

### Task 5 — Achievement Backend (from Sprint 7)
If not done: 16 achievements, `POST /api/v1/companion/achievements/check`, weekly summary endpoint.

### Task 6 — Hosted Mode API Foundation
- Add `/api/v1/auth/signup` and `/api/v1/auth/login` (JWT-based)
- Add middleware to route requests by auth token to correct user context
- Document the container deployment spec for RunPod/Modal

### Task 7 — Drop Your Gate

---

## Notes
- Email and Calendar plugins can start with mock/demo data if IMAP/CalDAV integration is complex
- The executive endpoints should work for self-hosted users too (they configure email in dashboard settings)
- Document generation is local file creation — no cloud storage needed for MVP

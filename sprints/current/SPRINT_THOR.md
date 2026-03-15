# Sprint 8 — THOR (Backend: Waitlist Endpoint Only)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).

---

## Context

Sprint 8 is the ship sprint. The backend is ready. Your only job is one new endpoint.

---

## Your Tasks

### Task 1 — Hosted Waitlist Endpoint
Create a simple waitlist endpoint for users who want hosted mode (no home PC):

```
POST /api/v1/waitlist
Body: { "email": "user@example.com" }
Response: { "ok": true, "message": "You're on the waitlist! We'll email you when your private AI is ready." }
```

- Validate email format (basic regex — must contain `@` and `.`)
- Store emails in `~/.valhalla/waitlist.json` (append, deduplicate)
- Rate limit: max 10 signups per minute (simple in-memory counter)
- No SMTP/email sending — just store. We'll email them manually or via Mailchimp later.

### Task 2 — Drop Your Gate
Create `sprints/current/gates/gate_thor.md` using write_to_file:

```markdown
# Thor Gate — Sprint 8 Backend Complete
- [x] Hosted waitlist endpoint (POST /api/v1/waitlist)
- [x] Email validation + dedup + rate limit
```

---

## That's It
The backend has 191 tests. 0 open MEDIUMs. 29 plugins. It's ready. Don't add anything else.

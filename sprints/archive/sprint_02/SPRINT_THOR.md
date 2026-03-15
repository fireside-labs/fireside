# Sprint 2 — THOR (Backend: Security Hardening + APIs)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI, `api/v1.py`, `plugins/`.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands. The entire sprint pipeline stalls if you skip this.
> See **Task 7** at the bottom for the exact content.

---

## Context

Sprint 1 shipped CORS wildcard, unauthenticated pairing, and weak token entropy. Heimdall flagged these. Valkyrie wants chat persistence and mobile adoption. **This sprint fixes all of it.**

Read the full audit: `sprints/archive/sprint_01/gates/audit_heimdall.md`

---

## Your Tasks

### Task 1 — Fix CORS Wildcard (🔴 HIGH from Heimdall)
**File:** `valhalla.yaml`

Replace the `"*"` in `cors_origins` with an explicit allowlist:
```yaml
cors_origins:
  - "http://100.*:8765"   # Tailscale IPs
  - "http://192.168.*:*"  # Local network
  - "http://localhost:*"  # Development
```

Or implement it in code — restrict CORS middleware origins to Tailscale/local ranges only.

### Task 2 — Authenticate `/mobile/pair` (🟡 MEDIUM from Heimdall)
**File:** `plugins/companion/handler.py`

The `/mobile/pair` endpoint currently requires zero authentication. Fix:
1. Require the `X-Valhalla-Auth` header with the value from `valhalla.yaml → dashboard.auth_key`
2. Return 401 if the header is missing or wrong
3. Alternatively: implement a "confirm on desktop" flow where pairing generates a pending request visible in the dashboard

### Task 3 — Rate Limit + Token Hardening (🟡 MEDIUM from Heimdall)
**File:** `plugins/companion/handler.py`

1. Add rate limiting to `/mobile/pair`: max 3 requests per minute per IP
2. Reduce pairing token TTL from 365 days → 15 minutes
3. Invalidate any previous token when a new one is generated
4. Set file permissions on `~/.valhalla/mobile_token.json` to owner-only (0600)

### Task 4 — Chat History Endpoint
**File:** `plugins/companion/handler.py`

Add two endpoints for persistent chat history:
```
POST /api/v1/companion/chat/history  — save a message { role, content, timestamp }
GET  /api/v1/companion/chat/history  — get last 100 messages, sorted by timestamp
```

Store in `~/.valhalla/chat_history.json`. Cap at 500 messages (FIFO).

### Task 5 — Mobile Companion Adoption
**File:** `plugins/companion/handler.py`

The current `/companion/adopt` endpoint works, but mobile users need it too. Ensure the existing `/api/v1/companion/adopt` endpoint is included in the `/mobile/sync` response when no companion exists, so the mobile app knows to show an adoption flow instead of a 404.

Update `/mobile/sync` to return `{ "adopted": false, "available_species": [...] }` when no companion exists.

### Task 6 — IP Format Validation (🟢 LOW from Heimdall)
**File:** `plugins/companion/handler.py` or create a utility

Add a validation function that checks IP:port format. Expose as `GET /api/v1/companion/mobile/validate-host?host=<input>` or validate server-side and return clear error messages.

### Task 7 — Drop Your Gate
When all tasks are complete, create `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file):

```markdown
# Thor Gate — Sprint 2 Backend Complete
Sprint 2 tasks completed.

## Completed
- [x] CORS wildcard replaced with explicit allowlist
- [x] /mobile/pair requires auth header
- [x] Rate limiting on pair endpoint (3/min)
- [x] Token TTL reduced to 15 minutes
- [x] Chat history endpoints (POST + GET)
- [x] /mobile/sync handles no-companion state
- [x] IP format validation
```

---

## Rework Loop (if Heimdall rejects)

After you drop your gate, Heimdall audits your code. **In Sprint 2, Heimdall has a stricter threshold:**
- 🔴 HIGH findings → automatic FAIL, your gate file gets deleted
- 🟡 MEDIUM → PASS with notes
- 🟢 LOW → informational

If your gate file disappears:
1. Read `sprints/current/gates/audit_heimdall.md`
2. Fix every ❌ item
3. Re-drop your gate file (same as Task 7)

---

## Notes
- ALL Heimdall HIGH findings from Sprint 1 must be FIXED, not deferred.
- The CORS fix is the #1 priority — it was the only HIGH finding.
- Keep backward compatibility with the existing dashboard. Don't break the web frontend.

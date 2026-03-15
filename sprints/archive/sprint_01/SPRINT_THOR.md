# Sprint 1 — THOR (Backend)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI, `api/v1.py`, plugins.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands. The entire sprint pipeline stalls if you skip this.
> See **Task 5** at the bottom for the exact content.

---

## Context

The companion plugin (`plugins/companion/`) is fully built with 13 API endpoints. The mobile app needs to call these endpoints over a local network (Tailscale or direct IP). Your job is to make sure the backend is mobile-ready.

Key files:
- `api/v1.py` — main FastAPI router
- `plugins/companion/handler.py` — all companion routes
- `plugins/companion/relay.py` — relay server security
- `plugins/companion/queue.py` — task queue (phone → home PC)
- `plugins/companion/sim.py` — Tamagotchi engine

---

## Your Tasks

### Task 1 — CORS Headers for Mobile
The mobile app will call the backend from a different origin. Add permissive CORS headers for local network requests.

In `api/v1.py` (or wherever the FastAPI app is instantiated), ensure:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in Sprint 2 with Heimdall
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Check if CORS is already configured — if so, verify it allows all origins for now.

### Task 2 — Mobile Sync Endpoint
Add `POST /api/v1/companion/mobile/sync` — a single endpoint the mobile app calls on launch to get everything it needs in one request:

```python
@router.post("/api/v1/companion/mobile/sync")
async def mobile_sync():
    """
    Single-call sync for mobile app launch.
    Returns: companion status, pending task results, personality, mood prefix.
    """
```

Response shape:
```json
{
  "ok": true,
  "companion": { ...full get_status() result... },
  "personality": { ...from agent_profiles... },
  "mood_prefix": "...",
  "pending_tasks": [ ...completed tasks not yet seen by phone... ],
  "synced_at": 1234567890.0
}
```

### Task 3 — Offline Token (Mobile Identity)
Add `POST /api/v1/companion/mobile/pair` — generates a pairing token so the mobile app can authenticate future requests:

```python
@router.post("/api/v1/companion/mobile/pair")
async def mobile_pair():
    """
    Generate a simple 6-digit pairing code for the mobile app to authenticate.
    Stores the token in ~/.valhalla/mobile_token.json with 365-day expiry.
    Returns: { "ok": true, "token": "ABC123", "expires_at": ... }
    """
```

This doesn't need to be cryptographically complex yet — a random 6-digit alphanumeric code is fine. Heimdall will harden this in Sprint 2.

### Task 4 — Health Check for Mobile
Ensure `GET /api/v1/status` returns a `mobile_ready: true` field so the app can confirm it's talking to a Valhalla backend and not some random server.

### Task 5 — Drop Your Gate
When all 4 tasks above are complete and tested:
```bash
echo "# Thor Gate — Sprint 1 Backend Complete" > sprints/current/gates/gate_thor.md
echo "Completed at $(date)" >> sprints/current/gates/gate_thor.md
echo "" >> sprints/current/gates/gate_thor.md
echo "## Completed" >> sprints/current/gates/gate_thor.md
echo "- [x] CORS headers configured" >> sprints/current/gates/gate_thor.md
echo "- [x] /mobile/sync endpoint added" >> sprints/current/gates/gate_thor.md
echo "- [x] /mobile/pair endpoint added" >> sprints/current/gates/gate_thor.md
echo "- [x] /status returns mobile_ready: true" >> sprints/current/gates/gate_thor.md
```

---

---

## Rework Loop (if Heimdall rejects)

After you drop your gate, Heimdall audits your code. **If he finds critical issues, he will DELETE `gate_thor.md`.** If your gate file disappears:

1. Read `sprints/current/gates/audit_heimdall.md` for the list of issues
2. Fix every ❌ item
3. Re-drop your gate file (same command as Task 5)

This cycle repeats until Heimdall passes you.

---

## Notes
- Keep it simple. Heimdall will audit security in Phase 2 — don't over-engineer auth yet.
- The CORS wildcard is intentional for Sprint 1. Heimdall will tighten it.
- All new endpoints go in `plugins/companion/handler.py` using the existing router pattern.

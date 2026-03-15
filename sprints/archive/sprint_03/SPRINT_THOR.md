# Sprint 3 — THOR (Backend: Push Notifications + Security Fixes)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI, `api/v1.py`, `plugins/`.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands. The entire sprint pipeline stalls if you skip this.
> See **Task 6** at the bottom for the exact content.

---

## Context

Sprint 2 fixed all HIGH findings. Heimdall has 2 MEDIUM carryovers. Valkyrie wants push notifications — the companion needs to reach out to the user proactively.

Read previous audits at: `sprints/archive/sprint_02/gates/audit_heimdall.md`

---

## Your Tasks

### Task 1 — Push Notification Infrastructure
Use **Expo Push Notifications** — this is the simplest path for React Native and avoids direct FCM/APNs setup.

Create `plugins/companion/notifications.py`:
```python
import httpx

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

async def send_push(token: str, title: str, body: str, data: dict = None):
    """Send a push notification via Expo's push service."""
    message = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
    }
    if data:
        message["data"] = data
    async with httpx.AsyncClient() as client:
        resp = await client.post(EXPO_PUSH_URL, json=message)
        return resp.json()
```

Add endpoint: `POST /api/v1/companion/mobile/register-push` — stores the Expo push token in `~/.valhalla/push_token.json`.

### Task 2 — Companion-Initiated Notification Triggers
Add a background check (runs on the existing event loop or via a periodic task) that sends push notifications when:

1. **Happiness drops below 30:** "Your companion misses you! 🥺 Come say hi."
2. **Daily gift is ready:** "(Companion name) has a surprise for you! 🎁"
3. **Task completed:** "Your task is done! (task_type) — check the results."
4. **Companion leveled up:** "🎉 (Name) reached level (N)!"

Rate limit: max 1 notification per trigger type per hour (don't spam).

Store last notification timestamps in `~/.valhalla/notification_state.json`.

### Task 3 — Fix hmac.compare_digest (🟡 MEDIUM from Heimdall)
**File:** `plugins/companion/handler.py` line 275

Replace:
```python
if not provided or provided != auth_key
```
With:
```python
import hmac
if not provided or not hmac.compare_digest(provided, auth_key)
```

### Task 4 — Rate Limit Dict Cleanup (🟡 MEDIUM from Heimdall)
**File:** `plugins/companion/handler.py`

The `_pair_attempts` dict grows unbounded. Add a cleanup that purges entries older than 2 minutes, triggered before each rate limit check. Same pattern as `_join_tokens` cleanup in `api/v1.py`.

### Task 5 — Backend Input Validation (🟢 LOW from Heimdall)
**File:** `plugins/companion/handler.py`

1. Add `max_length=20` validation on companion name in the adopt endpoint's Pydantic model
2. Add `max_length=200` validation on task queue payload
3. Return 422 with a clear error message for violations

### Task 6 — Drop Your Gate
When all tasks are complete, create `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file):

```markdown
# Thor Gate — Sprint 3 Backend Complete
Sprint 3 tasks completed.

## Completed
- [x] Expo Push notification infrastructure
- [x] Push token registration endpoint
- [x] 4 notification triggers (happiness, gift, task, level-up)
- [x] Notification rate limiting (1/hour per type)
- [x] hmac.compare_digest for pair auth
- [x] Rate limit dict cleanup
- [x] Input validation (name length, task payload)
```

---

## Rework Loop (if Heimdall rejects)

- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
- 🟡 MEDIUM → PASS with notes
- 🟢 LOW → informational

If your gate disappears, read `sprints/current/gates/audit_heimdall.md`, fix issues, re-drop.

---

## Notes
- Expo Push Notifications are free and don't require Firebase setup. They work for both iOS and Android.
- The notification background task should integrate with the existing companion `apply_decay` cycle if possible.
- Don't break any Sprint 2 tests. All 42 tests (15 Sprint 1 + 27 Sprint 2) should still pass.

# Sprint 4 — THOR (Backend: Mobile Feature Compatibility)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI, `api/v1.py`, `plugins/`.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

> [!IMPORTANT]
> **Read `FEATURE_INVENTORY.md` first** to understand the full platform. Many features are already built
> and have working APIs. Your job is to ensure they work from the mobile app.

---

## Context

The backend already has APIs for adventures, daily gifts, guardian, and teach-me. But some of these may not be included in the mobile sync response, or may need minor adjustments for mobile consumption. Your job is compatibility, not rebuilding.

Key existing files to review:
- `plugins/companion/handler.py` — existing routes for adventures, gifts, guardian, teach-me
- `plugins/companion/sim.py` — Tamagotchi engine, food items, walk events
- `plugins/companion/guardian.py` — message analysis, regret detection, rewrite suggestions
- `plugins/companion/adventure_guard.py` — adventure security, loot tables, signed results
- `dashboard/components/AdventureCard.tsx` — reference for adventure encounter format
- `dashboard/components/DailyGift.tsx` — reference for daily gift format

---

## Your Tasks

### Task 1 — Ensure Adventure API is Mobile-Accessible
Review the existing adventure endpoints. Verify:
1. Adventures can be triggered from the mobile app (POST to generate encounter)
2. Choices can be submitted and results returned
3. Rewards (inventory items, XP, happiness) are applied correctly
4. Adventure results are HMAC-signed (as per `adventure_guard.py`)

If any endpoint is missing or not registered in the companion handler, add it. If they all exist, document them for Freya.

### Task 2 — Ensure Daily Gift API is Mobile-Accessible
The daily gift logic may currently be frontend-only (in `DailyGift.tsx`). Check if there's a backend endpoint for it.
- If YES: verify it returns species-specific gifts with proper daily tracking
- If NO: create `GET /api/v1/companion/daily-gift` that returns today's gift (or `null` if already claimed) and `POST /api/v1/companion/daily-gift/claim` to claim it

### Task 3 — Ensure Guardian API Works for Mobile Chat
The guardian endpoint at `/api/v1/companion/guardian` should already work. Verify:
1. `POST /api/v1/companion/guardian` accepts `{ message, recipient?, time_of_day? }`
2. Returns `{ safe: bool, warnings: [], suggested_rewrite: str? }`
3. Integrates regret detection (2AM flag, ex-partner, reply-all, ALL CAPS)

If the mobile app sends the current time, the guardian can flag late-night messages.

### Task 4 — Update `/mobile/sync` with Feature Availability
Update the mobile sync response to include feature flags so the mobile app knows what's available:

```json
{
  "ok": true,
  "companion": { ... },
  "features": {
    "adventures": true,
    "daily_gift": true,
    "guardian": true,
    "teach_me": true,
    "translation": true,
    "morning_briefing": true
  },
  "daily_gift_available": true,
  "adventure_available": true
}
```

### Task 5 — Drop Your Gate
Create `sprints/current/gates/gate_thor.md` using write_to_file:

```markdown
# Thor Gate — Sprint 4 Backend Complete
Sprint 4 tasks completed.

## Completed
- [x] Adventure API verified/created for mobile
- [x] Daily gift API verified/created for mobile
- [x] Guardian API verified for mobile chat
- [x] /mobile/sync updated with feature flags
```

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
- Read `sprints/current/gates/audit_heimdall.md` if gate is deleted

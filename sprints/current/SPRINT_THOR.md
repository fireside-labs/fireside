# Sprint 5 — THOR (Backend: Platform Bridge + Security Fixes)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI, `api/v1.py`, `plugins/`.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

> [!IMPORTANT]
> **Read `FEATURE_INVENTORY.md`** to understand the full platform.

---

## Context

Heimdall caught that adventure rewards come from the client body (MEDIUM). Valkyrie wants the mobile app to show what the home PC is doing — dream cycles, memory count, uptime. The proactive guardian needs to detect late-night chat opens.

Key files:
- `plugins/companion/handler.py` — all companion routes
- `plugins/companion/guardian.py` — message analysis, regret detection
- `plugins/companion/nllb.py` — 200-language translation (already complete)
- `plugins/companion/adventure_guard.py` — HMAC signing, loot validation

---

## Your Tasks

### Task 1 — Fix Adventure Rewards (🟡 MEDIUM from Heimdall Sprint 4)
**File:** `plugins/companion/handler.py`

**Problem:** `/adventure/choose` reads rewards from the client request body. A malicious client could submit inflated rewards.

**Fix:** Store the generated encounter server-side when `/adventure/generate` is called:
```python
# In-memory storage (keyed by companion name)
_active_encounters = {}

# On generate: store the encounter with its rewards
_active_encounters[companion_name] = {
    "type": encounter_type,
    "choices": choices_with_rewards,
    "generated_at": time.time(),
    "expires_at": time.time() + 300  # 5 min to choose
}

# On choose: look up rewards server-side, ignore client values
encounter = _active_encounters.pop(companion_name, None)
if not encounter or time.time() > encounter["expires_at"]:
    return 400 "Encounter expired"
rewards = encounter["choices"][choice_index]["rewards"]
```

### Task 2 — Add `/mobile/unregister-push` (🟢 LOW carried from Sprint 3)
**File:** `plugins/companion/handler.py`

```python
@router.post("/api/v1/companion/mobile/unregister-push")
async def unregister_push():
    """Remove stored push token. Called when user disables notifications."""
    token_path = Path.home() / ".valhalla" / "push_token.json"
    if token_path.exists():
        token_path.unlink()
    return {"ok": True}
```

### Task 3 — Platform Activity in `/mobile/sync`
**File:** `plugins/companion/handler.py`

Add a `platform` section to the sync response showing what the home PC is doing:

```json
{
  "platform": {
    "uptime_hours": 42.5,
    "models_loaded": ["qwen-14b", "whisper-large"],
    "memory_count": 247,
    "plugins_active": 12,
    "last_dream_cycle": "2026-03-15T04:30:00Z",
    "last_prediction": "Weather confidence: 87%",
    "mesh_nodes": 2
  }
}
```

Pull from:
- `working-memory` plugin for memory count
- `model-router` or `model-switch` for loaded models
- Server uptime from process start time
- `predictions` plugin for last prediction
- Node registry for mesh node count

If any plugin isn't available, return `null` for that field. Don't crash.

### Task 4 — Proactive Guardian Mode
**File:** `plugins/companion/guardian.py` or `handler.py`

Add `GET /api/v1/companion/guardian/check-in` that the mobile app calls on chat tab open:

```python
@router.get("/api/v1/companion/guardian/check-in")
async def guardian_check_in():
    """
    Time-aware check-in. Returns a proactive warning if it's late at night.
    """
    hour = datetime.now().hour
    if 0 <= hour < 5:
        return {
            "proactive_warning": True,
            "message": "It's late. Want me to hold any messages until morning?",
            "hold_option": True
        }
    return {"proactive_warning": False}
```

Species-specific messages would be a bonus (cat: "It's 2AM. Even I think you should sleep." / dog: "It's really late! Maybe sleep first? I'll guard your phone!").

### Task 5 — Translation API Compatibility Check
**File:** `plugins/companion/nllb.py`

The translation API should already work. Verify that these endpoints return proper responses:
- `GET /api/v1/companion/languages` — returns list of supported languages
- `POST /api/v1/companion/translate` — accepts `{ text, source_lang, target_lang }`

If they exist and work, document them for Freya. If missing, add them using the existing `nllb.py` functions.

### Task 6 — Drop Your Gate
Create `sprints/current/gates/gate_thor.md` using write_to_file:

```markdown
# Thor Gate — Sprint 5 Backend Complete
Sprint 5 tasks completed.

## Completed
- [x] Adventure rewards: server-side encounter storage
- [x] /mobile/unregister-push endpoint
- [x] Platform activity in /mobile/sync
- [x] Proactive guardian check-in (time-aware)
- [x] Translation API verified for mobile
```

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
- Read `sprints/current/gates/audit_heimdall.md` if gate is deleted

# 🛡️ Heimdall Security Audit — Sprint 5

**Sprint:** The Mode Split: Pet vs Tool + Platform Bridge
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-15
**Verdict:** ✅ PASS — Zero HIGH, zero MEDIUM. Sprint 4 MEDIUM fixed.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## Scope

### Thor (Backend) — 2 files
| File | Change |
|---|---|
| `plugins/companion/handler.py` | Server-side encounter storage, unregister-push, platform activity, guardian check-in |
| `tests/test_sprint5_platform.py` | [NEW] 26 tests |

### Freya (Frontend) — 10 files
| File | Change |
|---|---|
| `mobile/src/ModeContext.tsx` | [NEW] Pet↔Tool mode context + persistence |
| `mobile/app/(tabs)/tools.tsx` | [NEW] Translation, TeachMe, platform card |
| `mobile/src/MorningBriefing.tsx` | [NEW] Morning briefing card (6-11AM) |
| `mobile/src/ProactiveGuardian.tsx` | [NEW] Late-night guardian bar |
| `mobile/app/(tabs)/_layout.tsx` | Mode-aware tab visibility |
| `mobile/app/_layout.tsx` | ModeProvider wrapping root |
| `mobile/app/(tabs)/chat.tsx` | ProactiveGuardian between header/messages |
| `mobile/app/(tabs)/care.tsx` | MorningBriefing + mode toggle |
| `mobile/src/api.ts` | translate(), teach(), guardianCheckIn() |
| `mobile/src/types.ts` | platform + features types |

---

## Sprint 4 MEDIUM Fix Verification

### ✅ Adventure Rewards Server-Side — FIXED

| Check | Before (Sprint 4) | After (Sprint 5) |
|---|---|---|
| Rewards source | `body.get("rewards", {})` | `choices[choice_idx].get("reward", ...)` |
| Encounter storage | None | `_active_encounters[companion_name]` ✅ |
| Encounter consumed | Never | `.pop()` on choose ✅ |
| Encounter expiry | None | 5 minutes ✅ |
| Choice index validation | None | `0 <= idx < len(choices)` ✅ |
| Client rewards field | Trusted | **Removed** ✅ |

- Test confirms: `assertNotIn('body.get("rewards"', choose_body)` ✅
- Encounter stored on generate (line 570), popped on choose (line 711) ✅
- Expired encounters return 400 (line 714) ✅

---

## New Backend Security Analysis

### ✅ `/mobile/unregister-push` — Secure

- Deletes `~/.valhalla/push_token.json` via `unlink()` ✅
- Uses `Path.exists()` check before delete (no error on missing file) ✅
- No auth required (matches register-push — both are user-initiated) ✅

### ✅ Platform Activity — Information Disclosure Review

| Field | Source | Risk |
|---|---|---|
| `uptime_hours` | `psutil.Process` | None — uptime is not sensitive |
| `models_loaded` | `model_router` | **LOW** — exposes AI model names |
| `memory_count` | `working_memory` | None — just a count |
| `plugins_active` | `plugin_loader` | None — just a count |
| `last_prediction` | `predictions` | None — nullable |
| `mesh_nodes` | `config.mesh.peers` | **LOW** — reveals network topology |

**Key security feature:** 6 independent try/except blocks ensure any unavailable plugin degrades gracefully to null/0 ✅. No stack traces or error details exposed.

### ✅ Proactive Guardian Check-In — Secure

- Only triggers 0-5AM (server-side `datetime.now().hour`) ✅
- Species-specific messages — no user-controlled content in response ✅
- `hold_option: True` flag is advisory only (client-side behavior) ✅
- No state mutation — pure read-only endpoint ✅

---

## Frontend Security Analysis

### ✅ Mode Toggle — Properly Isolated

- Mode stored in AsyncStorage as `"pet"` or `"tool"` string ✅
- Validated on load: `if (stored === "pet" || stored === "tool")` ✅
- Default fallback: `"pet"` if invalid/missing ✅
- Tab layout switches between 5 tabs (Pet) and 3 tabs (Tool) ✅

### ✅ Translation UI — Secure

- Input sent to backend NLLB-200 model ✅
- Result rendered via `<Text>` (no XSS in React Native) ✅
- Copy-to-clipboard via `expo-clipboard` (standard API) ✅
- Error fallback: shows offline message, no secrets exposed ✅

### ✅ TeachMe — Secure

- Facts stored locally in AsyncStorage + sent to backend API ✅
- Backend `adventure_guard.py` validates facts: length (≤500), count (≤200), prompt injection scanning ✅
- PII detection (SSN, credit card, email, phone) with warnings ✅
- Frontend doesn't enforce limits but backend does ✅

### ✅ Morning Briefing — Secure

- Shows 6-11AM only, once per day via AsyncStorage date check ✅
- Platform stats from server rendered via `<Text>` ✅
- Dismissible — stores dismissal date ✅
- Falls back to random placeholder stats if server data unavailable ✅

### ✅ Proactive Guardian (Frontend) — Secure

- Shows 0-6AM, once per day via AsyncStorage ✅
- Calls `/guardian/check-in` API if online, falls back to time-based ✅
- "Hold Messages" is UI-only — pauses send, doesn't delete ✅
- "I'm Fine" dismisses and stores date ✅

---

## Findings

### 🟢 LOW — Platform Activity Exposes Model Names

**File:** `handler.py` line 935
**Issue:** `models_loaded` field returns AI model names (e.g., "qwen-3.5-14b"). While not a direct vulnerability, this reveals infrastructure details.
**Actual risk:** Very low — Tailscale-only deployment, model names are not secrets, and they're visible in the dashboard already.

### 🟢 LOW — Morning Briefing Uses Random Placeholder Stats

**File:** `MorningBriefing.tsx` lines 71-76
**Issue:** When platform data is unavailable, JavaScript `Math.random()` generates fake stats (e.g., "Reviewed 12 conversations"). This could confuse users who think these are real metrics.
**Actual risk:** None for security. UX concern — should show "data unavailable" instead of random numbers.

---

## Positive Findings ✅

| Area | Assessment |
|---|---|
| **Sprint 4 MEDIUM fixed** | Server-side encounter storage, client rewards removed ✅ |
| **Unregister-push** | Sprint 3 LOW resolved — endpoint now exists ✅ |
| **Platform activity** | 6 graceful try/except fallbacks, no stack traces ✅ |
| **Mode toggle** | Validated input, safe default, AsyncStorage persistence ✅ |
| **Translation** | Backend NLLB-200, no user data exposed ✅ |
| **TeachMe** | Prompt injection scanning + PII detection on backend ✅ |
| **Guardian check-in** | Read-only, no state mutation, time-gated ✅ |
| **No secrets in frontend** | Still clean after 5 sprints ✅ |
| **124 total tests** | All passing (15 + 27 + 27 + 29 + 26) ✅ |

---

## Sprint 6 Checklist (Minor)

- [ ] Consider sanitizing `models_loaded` to return count instead of names
- [ ] Replace random placeholder stats in MorningBriefing with "data unavailable" text

---

## Verdict

**✅ PASS — Sprint 5 shipping approved.**

- **0 HIGH findings** (strict rule satisfied)
- **0 MEDIUM findings** (Sprint 4 MEDIUM verified fixed)
- **2 LOW findings** (informational only)
- All previous findings from Sprints 3-4 resolved or tracked
- Test suite: 124 tests passing (cumulative across 5 sprints)

The platform bridge is well-guarded. Platform data is read-only with graceful degradation. The mode toggle is properly isolated. TeachMe benefits from the existing prompt injection infrastructure in `adventure_guard.py`. Cleanest audit since Sprint 3.

— Heimdall 🛡️

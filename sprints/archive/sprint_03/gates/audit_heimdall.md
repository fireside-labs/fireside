# 🛡️ Heimdall Security Audit — Sprint 3

**Sprint:** Mobile Companion: Push Notifications + App Store Readiness
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-15
**Verdict:** ✅ PASS — Zero HIGH, zero MEDIUM. Cleanest sprint yet.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## Scope

### Thor (Backend) — 4 files
| File | Change |
|---|---|
| `plugins/companion/notifications.py` | [NEW] Expo push infrastructure + 4 triggers |
| `plugins/companion/handler.py` | Auth hardened, rate limit cleanup, input validation, push registration |
| `tests/test_sprint3_pushnotify.py` | [NEW] 27 tests |
| `tests/test_sprint1_mobile.py` | Updated CORS regression test |

### Freya (Frontend) — 14 files
| File | Change |
|---|---|
| `mobile/src/notifications.ts` | [NEW] Push registration, unregister, tap routing |
| `mobile/src/sounds.ts` | [NEW] Sound manager with graceful failure |
| `mobile/app/privacy.tsx` | [NEW] Privacy policy screen |
| `mobile/app/_layout.tsx` | Push registration + notification tap handler |
| `mobile/app/(tabs)/care.tsx` | Mood-reactive avatars + playSound |
| `mobile/app/(tabs)/chat.tsx` | playSound on send |
| `mobile/app/setup.tsx` | Privacy Policy link |
| `mobile/src/api.ts` | registerPush + unregisterPush methods |
| `mobile/app.json` | Icon, splash, expo-notifications plugin |
| `mobile/assets/companions/*_{happy,neutral,sad}.png` | 18 mood variant images |
| `mobile/assets/icon.png` | App icon placeholder |
| `mobile/assets/splash.png` | Splash screen placeholder |
| `mobile/assets/sounds/*.mp3` | 4 sound effect placeholders |

---

## Sprint 2 MEDIUM Findings Verification

### ✅ `hmac.compare_digest` — FIXED

- `import hmac` at top of `handler.py` ✅ (line 14)
- `hmac.compare_digest(provided, auth_key)` replaces `provided != auth_key` ✅ (line 294)
- Test confirms: `assertNotIn("provided != auth_key", pair_body)` ✅

### ✅ Rate Limit Dict Cleanup — FIXED

- Stale entries (>120s old) are purged on each pair request ✅ (lines 301-304)
- `del _pair_attempts[ip]` removes stale IPs ✅
- Test confirms: `assertIn("stale_ips", src)` ✅

### ✅ Input Validation — FIXED

- Companion name: `len(req.name) > 20` → 422 ✅ (line 89)
- Empty name: `not req.name.strip()` → 422 ✅ (line 91)
- Task type: `len(req.task_type) > 200` → 422 ✅ (line 135)
- Payload size: `len(json.dumps(req.payload)) > 10000` → 422 ✅ (line 137)

---

## Push Notification Security Analysis

### ✅ Token Registration — Secure

| Check | Result |
|---|---|
| Validates Expo token format (`ExponentPushToken[...]`) | ✅ handler.py line 491 |
| Token stored server-side only (`~/.valhalla/push_token.json`) | ✅ |
| No token logging (only first 20 chars logged) | ✅ notifications.py line 46 |
| Frontend stores token locally for unregister support | ✅ notifications.ts line 61 |

### ✅ Notification Triggers — Rate Limited

| Trigger | Condition | Rate Limit |
|---|---|---|
| Low happiness | `happiness < 30` | 1/hour ✅ |
| Daily gift | `>24h since last gift` | 1/hour ✅ |
| Task completed | `completed tasks exist` | 1/hour ✅ |
| Level up | `_just_leveled_up flag` | 1/hour ✅ |

- Rate limit state persisted to disk (`notification_state.json`) — survives server restart ✅
- Trigger types are independent (one trigger doesn't block others) ✅

### ✅ Push Send — Properly Guarded

- Uses `httpx.AsyncClient` with 10-second timeout ✅
- Graceful fallback if `httpx` not installed ✅
- Sends to official Expo endpoint only (`exp.host`) ✅
- No user-controlled data in notification title/body (companion name + fixed strings) ✅

---

## New Sprint 3 Findings

### 🟢 LOW — No Unregister Endpoint on Backend

**File:** `mobile/src/api.ts` line 124
**Issue:** The frontend calls `companionAPI.unregisterPush()` which hits `/api/v1/companion/mobile/unregister-push`, but no such endpoint exists in `handler.py`. The call will fail with a 404.
**Actual risk:** None — the frontend catches the error silently. The token file is simply not removed on the backend, so notifications continue until the token expires naturally.
**Sprint 4 Fix:** Add the unregister endpoint or remove the dead code path.

---

### 🟢 LOW — Push Token File Not Permission-Restricted

**File:** `plugins/companion/notifications.py` line 42
**Issue:** The push token file (`~/.valhalla/push_token.json`) is written without `0o600` permissions, unlike the pairing token file.
**Actual risk:** Very low — the Expo push token is not a secret (it's sent through Expo's public push service). However, consistency with the pairing token would be good practice.

---

### 🟢 LOW — Privacy Policy Uses Placeholder Email

**File:** `mobile/app/privacy.tsx` line 80
**Issue:** Contact email is `privacy@valhalla.local` — this is not a real domain.
**Actual risk:** None for security. Should be updated before App Store submission.

---

## Positive Findings ✅

| Area | Assessment |
|---|---|
| **All Sprint 2 MEDIUMs fixed** | `hmac.compare_digest`, rate limit cleanup, input validation ✅ |
| **Push auth** | Token format validated before storage ✅ |
| **Push rate limiting** | 1/hour per trigger type, persisted to disk ✅ |
| **httpx timeout** | 10s timeout, graceful fallback ✅ |
| **No secrets exposed** | Push token only partially logged (20 chars) ✅ |
| **Privacy policy** | Accurate data disclosure, correctly states no cloud/analytics ✅ |
| **Sound system** | Graceful degradation — silently fails if files missing ✅ |
| **Push permissions** | Properly requests on physical device only ✅ |
| **Notification routing** | Tap handler maps trigger types to correct tabs ✅ |
| **69 total tests** | Sprint 1: 15, Sprint 2: 27, Sprint 3: 27 — all passing ✅ |
| **TypeScript strict** | 0 errors, 633 packages, 0 vulnerabilities ✅ |

---

## Sprint 4 Checklist (Minor — No Blockers)

- [ ] Add `/mobile/unregister-push` backend endpoint (or remove dead frontend code)
- [ ] Set `0o600` on `push_token.json` for consistency
- [ ] Replace `privacy@valhalla.local` with real contact email before App Store submission

---

## Verdict

**✅ PASS — Sprint 3 shipping approved.**

- **0 HIGH findings** (strict rule satisfied)
- **0 MEDIUM findings** (cleanest sprint yet!)
- **3 LOW findings** (informational only, no blockers)
- All Sprint 2 MEDIUM findings **verified fixed**
- Test suite: 69 tests passing (cumulative)

This is the most security-mature sprint to date. The push notification implementation follows Expo's recommended patterns correctly, and the backend hardening from Sprints 2+3 has eliminated all known attack surfaces for a Tailscale-only deployment.

— Heimdall 🛡️

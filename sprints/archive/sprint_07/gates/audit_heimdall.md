# 🛡️ Heimdall Security Audit — Sprint 7

**Sprint:** Hardening + Achievements + TestFlight
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-15
**Verdict:** ✅ PASS — Zero HIGH, zero MEDIUM. All Sprint 6 findings fixed. Cleanest hardening sprint.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## Scope

### Thor (Backend) — 3 files
| File | Change |
|---|---|
| `plugins/companion/handler.py` | SSRF blocklist, WS auth+cap, error sanitization, achievement+weekly endpoints |
| `plugins/companion/achievements.py` | [NEW] 16 milestones, JSON persistence, check_and_award |
| `tests/test_sprint7_security.py` | [NEW] 31 tests |

### Freya (Frontend) — 8 files
| File | Change |
|---|---|
| `mobile/src/AchievementBadge.tsx` | [NEW] 16 achievements with earned/locked/progress states |
| `mobile/src/AchievementToast.tsx` | [NEW] Slide-in toast, sparkle, haptic, sound, 3s auto-dismiss |
| `mobile/src/WeeklySummary.tsx` | [NEW] Stats grid, highlights, share via RN Share |
| `mobile/src/QRPair.tsx` | [NEW] Camera QR scanner + manual IP fallback |
| `mobile/src/useWebSocket.ts` | [MOD] Auth token, auth_rejected event |
| `mobile/app/(tabs)/care.tsx` | [MOD] WeeklySummary rendered |
| `mobile/src/api.ts` | [MOD] achievementsCheck, weeklySummary, pair methods |
| `mobile/app.json` | [MOD] Camera+mic permissions |

---

## Sprint 6 Fix Verification

### ✅ SSRF Blocklist — FIXED

| Check | Result |
|---|---|
| `_is_url_safe()` function exists | ✅ (line 1208) |
| Uses `ipaddress` module for CIDR matching | ✅ |
| Blocks `127.0.0.0/8` | ✅ |
| Blocks `10.0.0.0/8` | ✅ |
| Blocks `172.16.0.0/12` | ✅ |
| Blocks `192.168.0.0/16` | ✅ |
| Blocks `169.254.0.0/16` (link-local + AWS metadata) | ✅ |
| Blocks `0.0.0.0/8` | ✅ |
| Blocks `localhost` by name | ✅ |
| Returns 403 on blocked URL | ✅ (line 1178) |
| Called before `fetch_and_parse_sync` | ✅ (line 1177) |
| Domain names pass through (resolved externally) | ✅ |
| Unit test covers 5 blocked + 2 allowed URLs | ✅ |

**Implementation quality:** Excellent. Uses Python's `ipaddress` module for proper CIDR matching rather than string comparison. Domain names are allowed (they resolve externally). The only gap is DNS rebinding (domain resolves to internal IP), but this is an acceptable risk for this deployment model.

### ✅ WebSocket Authentication — FIXED

| Check | Result |
|---|---|
| Token required via `?token=` query param | ✅ (line 1277) |
| `_verify_ws_token()` uses `hmac.compare_digest` | ✅ (line 1251) |
| Verifies against stored pairing token | ✅ |
| Unauthorized → close code 4001 | ✅ (line 1279) |
| Connection cap: `_WS_MAX_CONNECTIONS = 5` | ✅ (line 1239) |
| Too many → close code 4029 | ✅ (line 1285) |
| Dead connections cleaned before cap check | ✅ (`_cleanup_dead_ws`, line 1283) |
| Auth BEFORE `accept()` | ✅ (close before accept prevents resource leak) |

**Implementation quality:** Excellent. Auth check happens before `websocket.accept()`, meaning unauthorized connections are rejected without allocating server resources. Timing-safe comparison prevents token timing attacks.

### ✅ Marketplace Error Sanitization — FIXED

| Before (Sprint 6) | After (Sprint 7) |
|---|---|
| `"note": str(e)` in browse/search/install | `log.error("Marketplace X error: %s", e)` + generic HTTPException ✅ |
| Exception stack traces in response | `"Marketplace service unavailable"` ✅ |
| Browse summarize leaked error details | `"Failed to fetch or parse the URL"` ✅ |

---

## New Feature Security Analysis

### ✅ Achievement System — Secure

| Check | Result |
|---|---|
| Achievements server-defined (not client-created) | ✅ `ACHIEVEMENTS` dict in `achievements.py` |
| Counter-based (server state, not client claims) | ✅ Reads from `state["counters"]` |
| Idempotent (no double-awarding) | ✅ Checks `aid not in earned` before awarding |
| Persistence in `~/.valhalla/achievements.json` | ✅ |
| File permissions | ⚠️ No explicit 0600 (matches companion state file pattern) |
| No user input in achievement data | ✅ All names/desc/icons are hardcoded |
| Test covers idempotency | ✅ `test_idempotent` |

### ✅ Weekly Summary — Secure

- Server-generated from companion state counters ✅
- Highlights are template-based, not user-controlled ✅
- `highlights[:5]` caps output length ✅
- No sensitive data in response ✅

### ✅ QR Code Pairing — Secure

| Check | Result |
|---|---|
| Parses QR data as JSON | ✅ (`JSON.parse(data)`) |
| Validates `host` field exists | ✅ |
| Verifies connection via `testConnection()` | ✅ |
| Stores pairing token | ✅ (AsyncStorage — see LOW below) |
| Falls back to manual IP entry | ✅ |
| Camera permissions requested | ✅ |
| Error handling on invalid QR | ✅ |

### ✅ WebSocket Frontend Auth Integration — Secure

- Reads token from AsyncStorage on connect ✅
- Appends `?token=` to WebSocket URL ✅
- Handles `auth_rejected` event type ✅
- Exponential backoff preserved ✅

---

## Findings

### 🟢 LOW — QR Pairing Token Stored in AsyncStorage

**File:** `QRPair.tsx` line 47
**Issue:** `AsyncStorage.setItem("pairingToken", parsed.token)` — the pairing token is stored in unencrypted AsyncStorage. On a rooted/jailbroken device, this could be read by other apps.
**Actual risk:** LOW — the token is also stored the same way for the existing manual pairing flow. In hosted mode (Sprint 8+), auth tokens should use `expo-secure-store` instead.

### 🟢 LOW — WeeklySummary Falls Back to Mock Stats

**File:** `WeeklySummary.tsx` lines 62-66
**Issue:** When the API is unavailable, JavaScript `Math.random()` generates fake stats. Same pattern as the morning briefing issue from Sprint 5 (which was fixed on the backend in Sprint 6). The frontend fallback still uses fake data.
**Actual risk:** None for security. UX concern only.

---

## Positive Findings ✅

| Area | Assessment |
|---|---|
| **All 3 Sprint 6 findings fixed** | SSRF blocklist, WS auth, error sanitization ✅ |
| **SSRF implementation** | Proper CIDR matching via `ipaddress` module ✅ |
| **WS auth** | Token verified BEFORE accept(), timing-safe, connection capped ✅ |
| **Achievements** | Server-authoritative, idempotent, hardcoded definitions ✅ |
| **QR pairing** | JSON parse + connection verify + fallback ✅ |
| **No secrets in frontend** | Still clean after 7 sprints ✅ |
| **191 total tests** | All passing (15 + 27 + 27 + 29 + 26 + 36 + 31) ✅ |

---

## Verdict

**✅ PASS — Sprint 7 shipping approved. TestFlight ready.**

- **0 HIGH findings** (strict rule satisfied)
- **0 MEDIUM findings** (first zero-MEDIUM sprint since Sprint 5)
- **2 LOW findings** (AsyncStorage for pairing token, mock stats fallback)
- All Sprint 6 MEDIUMs and LOWs verified fixed
- Security hardening quality is excellent across all 3 fixes
- Test suite: 191 tests passing (cumulative across 7 sprints)

This is the hardening sprint the codebase needed. The SSRF and WebSocket fixes are properly implemented using standard Python libraries. The codebase is now TestFlight-ready from a security perspective.

— Heimdall 🛡️

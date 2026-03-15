# 🛡️ Heimdall Security Audit — Sprint 2

**Sprint:** Mobile Companion: Polish + Security Hardening
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-15
**Verdict:** ✅ PASS — Zero HIGH findings. Ship it.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## Scope

All code changed in Sprint 2, as declared in `gate_thor.md` and `gate_freya.md`.

### Thor (Backend) — 4 files
| File | Change |
|---|---|
| `valhalla.yaml` | Removed `"*"` from cors_origins, explicit allowlist |
| `bifrost.py` | Added `allow_origin_regex` for Tailscale/LAN IPs |
| `plugins/companion/handler.py` | Auth, rate limit, TTL, chat history, IP validation |
| `tests/test_sprint2_security.py` | 27 security tests |

### Freya (Frontend) — 7 files
| File | Change |
|---|---|
| `mobile/app/onboarding.tsx` | [NEW] 3-slide onboarding carousel |
| `mobile/app/_layout.tsx` | Onboarding routing check |
| `mobile/app/(tabs)/care.tsx` | Avatar images, RefreshControl, Haptics, adoption flow |
| `mobile/app/(tabs)/chat.tsx` | AsyncStorage history, Haptics |
| `mobile/app/(tabs)/tasks.tsx` | FAB + modal, RefreshControl, Haptics |
| `mobile/src/api.ts` | Added `adopt()` + `queueTask()` methods |
| `mobile/assets/companions/*.png` | 6 companion avatar images |

---

## Sprint 1 HIGH Finding Verification

### ✅ CORS Wildcard — FIXED

| Check | Result |
|---|---|
| `"*"` removed from `valhalla.yaml` cors_origins | ✅ Confirmed (line 36-40) |
| Explicit allowlist: `localhost:3000`, `localhost:3001`, `localhost:8765`, `127.0.0.1:8765` | ✅ |
| `bifrost.py` uses `allow_origin_regex` for Tailscale/LAN | ✅ Regex: `^https?://(100\.\\d+\.\\d+\.\\d+\|192\.168\.\\d+\.\\d+\|10\.\\d+\.\\d+\.\\d+)(:\\d+)?$` |
| Regex rejects public IPs (e.g., `8.8.8.8`) | ✅ Tested in test suite |

**Verdict: Sprint 1 HIGH is fully resolved.**

---

## Sprint 1 MEDIUM Findings Verification

### ✅ Unauthenticated `/mobile/pair` — FIXED

- Requires `X-Valhalla-Auth` header matching `dashboard.auth_key` ✅
- Returns 401 for missing/invalid auth ✅
- Warns if `auth_key` is still the placeholder `"change-me-dashboard-key"` ✅

### ✅ Token Entropy / Rate Limiting — FIXED

- Rate limited: 3 requests per minute per IP ✅
- Returns 429 on rate limit exceeded ✅
- Token TTL reduced from 365 days → 15 minutes ✅
- Previous token invalidated by overwrite on new generation ✅
- File permissions set to `0o600` (with OSError catch for Windows) ✅

### ✅ Plaintext HTTP — ACCEPTED

- Still uses `http://` as default — this is acceptable since Tailscale provides WireGuard encryption at the network layer
- The `allow_origin_regex` now restricts to private/Tailscale IPs, reducing the attack surface

---

## New Sprint 2 Findings

### 🟡 MEDIUM — Auth Key Comparison Uses `!=` Instead of `hmac.compare_digest()`

**File:** `plugins/companion/handler.py` line 275
**Issue:** `if not provided or provided != auth_key` uses a standard string comparison, which is susceptible to timing attacks.
**Risk:** An attacker on the local network could theoretically measure response times to guess the auth key character-by-character.
**Mitigating factor:** Exploit requires microsecond-precision timing on a LAN. The existing `config/receive` endpoint already uses `hmac.compare_digest()` — this should be consistent.

**Sprint 3 Fix:** Replace `provided != auth_key` with `not hmac.compare_digest(provided, auth_key)`.

---

### 🟡 MEDIUM — Rate Limiter Uses In-Memory Dict (No Persistence)

**File:** `plugins/companion/handler.py` line 199
**Issue:** `_pair_attempts` is an in-memory dict. A server restart clears all rate limit state, and this dict grows unbounded if many IPs hit the endpoint.
**Risk:** Minimal for the current deployment (single user, Tailscale). If exposed to more users, this could become a memory issue.

**Sprint 3 Fix:** Add periodic cleanup of stale entries (same pattern as `_join_tokens` cleanup in `api/v1.py`).

---

### 🟢 LOW — Chat History Concurrency (Race Condition)

**File:** `plugins/companion/handler.py` lines 353-373
**Issue:** The chat history POST reads the file, appends, and writes back. Two concurrent requests could cause a race condition where one message is lost.
**Actual risk:** Very low — single user, single phone. Mobile app serializes sends (typing indicator blocks concurrent input).

---

### 🟢 LOW — Companion Name Not Sanitized

**File:** `mobile/app/(tabs)/care.tsx` line 266 + `plugins/companion/handler.py`
**Issue:** The adoption name input has a `maxLength={20}` on the frontend, but the backend `AdoptRequest` model does not validate name length or content. A malicious client could send a very long name or special characters.
**Actual risk:** Minimal — the name is stored in a JSON file and rendered as `<Text>` in React Native (no HTML injection risk in RN).

---

### 🟢 LOW — Task Text Not Length-Limited on Backend

**File:** `plugins/companion/handler.py` (`QueueTaskRequest`)
**Issue:** The task queue endpoint accepts arbitrary-length `task_type` strings. The new task creation modal limits to 200 chars on frontend, but backend has no validation.
**Actual risk:** Low — similar to chat history, which does validate (5000 char limit).

---

## Positive Findings ✅

| Area | Assessment |
|---|---|
| **CORS hardened** | Wildcard removed, regex restricted to private IPs. ✅ |
| **Pair auth** | Requires dashboard auth key header. ✅ |
| **Rate limiting** | 3/min per IP on pair endpoint. ✅ |
| **Token TTL** | 15 minutes, auto-invalidated on new token. ✅ |
| **File permissions** | `0o600` on token file. ✅ |
| **Chat history validation** | Role validated, content max 5000 chars, FIFO cap at 500. ✅ |
| **IP validation** | Server-side regex with octet/port range checks, rejects `javascript:` URIs. ✅ |
| **Adoption flow** | Works offline with optimistic updates. ✅ |
| **Onboarding state** | Uses AsyncStorage flag, can't be bypassed to skip setup. ✅ |
| **No secrets in frontend** | Still no API keys or credentials in mobile source. ✅ |
| **27 security tests** | Comprehensive test suite covering all hardening tasks. ✅ |
| **TypeScript strict** | 0 errors, 628 packages, 0 vulnerabilities. ✅ |

---

## Sprint 3 Security Checklist

- [ ] Use `hmac.compare_digest()` for auth key comparison in `/mobile/pair`
- [ ] Add periodic cleanup to `_pair_attempts` rate limit dict
- [ ] Add backend validation for companion name length (max 20 chars)
- [ ] Add backend validation for task queue payload size

---

## Verdict

**✅ PASS — Sprint 2 shipping approved.**

- **0 HIGH findings** (strict rule satisfied)
- **2 MEDIUM findings** (timing-safe comparison + rate limit cleanup — logged for Sprint 3)
- **3 LOW findings** (informational only)
- All Sprint 1 HIGH/MEDIUM findings are **verified fixed**
- Test suite: 27 tests passing

— Heimdall 🛡️

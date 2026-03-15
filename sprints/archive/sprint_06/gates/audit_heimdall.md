# 🛡️ Heimdall Security Audit — Sprint 6

**Sprint:** Full Platform: Voice + Marketplace + OS Integration
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-15
**Verdict:** ✅ PASS — Zero HIGH findings. Two MEDIUM findings logged.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## Scope

### Thor (Backend) — 2 files
| File | Change |
|---|---|
| `plugins/companion/handler.py` | Voice endpoints, marketplace API, browse/summarize, WebSocket, morning briefing fix |
| `tests/test_sprint6_platform.py` | [NEW] 36 tests |

### Freya (Frontend) — 8 files
| File | Change |
|---|---|
| `mobile/src/VoiceMode.tsx` | [NEW] Hold-to-talk walkie-talkie (expo-av, STT, TTS) |
| `mobile/app/(tabs)/marketplace.tsx` | [NEW] Marketplace browsing + install |
| `mobile/src/UrlSummary.tsx` | [NEW] Paste URL → summary |
| `mobile/src/useWebSocket.ts` | [NEW] WebSocket hook (exponential backoff) |
| `mobile/app/(tabs)/chat.tsx` | VoiceMode integration |
| `mobile/app/(tabs)/tools.tsx` | UrlSummary card |
| `mobile/app/(tabs)/_layout.tsx` | Marketplace tab |
| `mobile/src/api.ts` | voiceTranscribe, voiceSpeak, marketplaceSearch, marketplaceInstall, browseSummarize |

---

## Voice Pipeline Security — Privacy Review

### ✅ Audio Privacy — Local-Only

| Check | Result |
|---|---|
| STT via local Whisper (no cloud) | ✅ `from plugins.voice.stt import transcribe_bytes` |
| TTS via local Kokoro (no cloud) | ✅ `from plugins.voice.tts import synthesize` |
| Privacy commitment documented | ✅ "Voice data NEVER leaves the local network" |
| Privacy badge in UI | ✅ `🔒 Audio stays on your local network` |
| Audio upload size limit | ✅ 25MB max (line 1016) |
| TTS text length limit | ✅ 5000 chars (line 1045) |
| Audio format validated | ⚠️ Accepts any file via multipart — relies on Whisper to reject non-audio |
| Temp audio files cleanup | ✅ Whisper manages via `transcribe_bytes`, Kokoro returns `FileResponse` |
| Microphone permissions | ✅ `Audio.requestPermissionsAsync()` (line 75) |
| Audio mode reset after playback | ✅ `allowsRecordingIOS: false` on playback (line 128) |
| Recording cleanup on error | ✅ `stopAndUnloadAsync()` in try (line 102) |

---

## Browse/Summarize — SSRF Analysis

### 🟡 MEDIUM — No SSRF Protection on URL Summarization

**File:** `handler.py` lines 1157-1196
**Issue:** The `/browse/summarize` endpoint accepts a user-provided URL and fetches it server-side via `fetch_and_parse_sync(url)`. While the URL must start with `http`, there is no blocklist for internal addresses. A malicious request could:
- Fetch `http://127.0.0.1:8765/api/v1/companion/status` — access internal API
- Fetch `http://localhost/` — probe local services
- Fetch `http://192.168.x.x/` — scan local network
- Fetch `http://169.254.169.254/` — AWS metadata endpoint (if ever cloud-deployed)

**Current mitigations:**
- Tailscale-only deployment limits who can send requests ✅
- URL must start with `http` (blocks `file://`, `ftp://`, etc.) ✅
- URL length capped at 2000 chars ✅
- Output capped at 2000 chars ✅

**Sprint 7 Fix:** Add an SSRF blocklist: reject URLs matching `localhost`, `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, and `0.0.0.0`.

---

## WebSocket Security

### 🟡 MEDIUM — WebSocket Has No Authentication

**File:** `handler.py` lines 1200-1253
**Issue:** The WebSocket endpoint `/api/v1/companion/ws` accepts connections without any token or auth header. Anyone on the Tailscale network can connect and receive real-time companion state updates. Additionally:
- `_ws_connections` is an unbounded list — a client could open many connections
- No rate limit on `sync` messages
- Dead connections only cleaned up during broadcast, not proactively

**Current mitigations:**
- Tailscale-only deployment means only trusted devices connect ✅
- WebSocket is read-mostly (only responds to `ping` and `sync`) ✅
- Dead connections removed during broadcast ✅

**Sprint 7 Fix:** Add token-based auth (query param `?token=` verified against pairing token) and cap concurrent connections (e.g., max 5).

---

## Marketplace Security

### ✅ Commerce Flow — Properly Gated

| Check | Result |
|---|---|
| Free items install via `/marketplace/install` | ✅ |
| Paid items return `ok: false` + Stripe checkout URL | ✅ (line 1144) |
| Cannot bypass price check | ✅ Server checks `item.get("price", 0)` |
| Marketplace wraps existing plugin registry | ✅ `_load_registry()` |
| Search query min length | ✅ 2 chars (line 1083) |

### 🟢 LOW — Exception Details Exposed in Marketplace Errors

**File:** `handler.py` lines 1078, 1098, 1113, 1153
**Issue:** Error handlers use `str(e)` which could expose internal file paths or module names in the response. Example: `{"note": "ModuleNotFoundError: No module named 'plugins.marketplace.handler'"}`.
**Fix:** Replace `str(e)` with a generic message like `"Marketplace service unavailable"`.

---

## Sprint 5 LOW Fix Verification

### ✅ Morning Briefing Placeholder Fix — RESOLVED

| Before (Sprint 5) | After (Sprint 6) |
|---|---|
| `Math.random()` for fake stats | `null` defaults for all fields ✅ |
| No validation | `validate_briefing_data` from `adventure_guard.py` ✅ |
| Frontend showed random numbers | Frontend shows "data unavailable" for nulls ✅ |

**Endpoint:** `GET /api/v1/companion/morning-briefing` — only returns verified data ✅

---

## New Findings Summary

| Severity | Finding | File | Risk |
|---|---|---|---|
| 🟡 MEDIUM | No SSRF protection on URL summarization | handler.py:1157 | Internal network scanning |
| 🟡 MEDIUM | WebSocket has no authentication | handler.py:1200 | Unauthorized state access |
| 🟢 LOW | Exception details exposed in marketplace errors | handler.py:1078 | Information disclosure |

---

## Positive Findings ✅

| Area | Assessment |
|---|---|
| **Voice privacy** | Local-only Whisper + Kokoro, privacy badge, 25MB limit ✅ |
| **Audio pipeline** | Proper cleanup (`unloadAsync`), permissions requested, mode reset ✅ |
| **Marketplace commerce** | Paid items gated by Stripe, can't bypass price check ✅ |
| **URL validation** | Must start with `http`, 2000 char limit, output capped ✅ |
| **WebSocket backoff** | Exponential (max 30s), max 10 retries, cleanup on unmount ✅ |
| **Morning briefing** | Null defaults, validated through `adventure_guard` ✅ |
| **No secrets in frontend** | Still clean after 6 sprints ✅ |
| **160 total tests** | All passing (15 + 27 + 27 + 29 + 26 + 36) ✅ |

---

## Sprint 7 Checklist

- [ ] **Add SSRF blocklist** to `/browse/summarize` (block localhost, RFC1918, link-local, metadata)
- [ ] **Add WebSocket authentication** (token query param verified against pairing token)
- [ ] **Cap WebSocket connections** (max 5 concurrent per client)
- [ ] Replace `str(e)` in marketplace error handlers with generic messages

---

## Verdict

**✅ PASS — Sprint 6 shipping approved.**

- **0 HIGH findings** (strict rule satisfied)
- **2 MEDIUM findings** (SSRF in browse/summarize, unauthenticated WebSocket)
- **1 LOW finding** (marketplace exception exposure)
- Voice pipeline is properly local-only with documented privacy commitment
- Marketplace commerce is correctly gated
- Test suite: 160 tests passing (cumulative across 6 sprints)

The two MEDIUMs are mitigated by Tailscale-only deployment but should be hardened for defense-in-depth before any wider distribution.

— Heimdall 🛡️

# 🛡️ Heimdall Security Audit — Sprint 14 (Last Mile Wiring)

**Sprint:** Last Mile Wiring
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-15
**Verdict:** ✅ PASS with notes — Zero HIGH, **2 MEDIUM**, 1 LOW.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## Files Reviewed

### Thor — Backend (4 new endpoints)
| File | Lines | Endpoint |
|---|---|---|
| `api/v1.py` | 737-821 | `POST /api/v1/chat` — LLM proxy via SSE |
| `api/v1.py` | 828-884 | `POST /api/v1/brains/install` — GGUF download via SSE |
| `api/v1.py` | 891-940 | `GET /api/v1/guildhall/agents` — real agents from config |
| `api/v1.py` | 947-1001 | `POST /api/v1/nodes` — device registration |
| `tauri/src-tauri/src/main.rs` | VRAM block | Mac unified memory fix |
| `tests/test_sprint14_lastmile.py` | NEW | 42 tests |

### Freya — Frontend
| File | Change |
|---|---|
| `CompanionChat.tsx` | [MOD] → real `POST /api/v1/chat` with canned fallback |
| `BrainInstaller.tsx` | [MOD] → SSE stream |
| `globals.css` | [MOD] neon green → fire amber |
| `nodes/page.tsx` | [MOD] Norse names removed, Add Node wired |
| `SystemStatus.tsx` | [MOD] → polls `/api/v1/status` |
| `OfflineBanner.tsx` | [NEW] — offline detection banner |
| `GuidedTour.tsx` | [NEW] — 3-step onboarding tour |
| `api.ts` | [MOD] port 8766 → 8765, mock tracking |

---

## Security Analysis

### ✅ `POST /api/v1/chat` — LLM Chat Proxy

| Check | Result |
|---|---|
| Proxy target | ✅ Hardcoded `http://127.0.0.1:8080/completion` — localhost only, **no SSRF** |
| Input length | ⚠️ No explicit max length on `req.message` (Pydantic `str` is unbounded) |
| Context limiting | ✅ `req.context[-10:]` — capped at last 10 messages |
| Response cap | ✅ `n_predict: 512` tokens |
| System prompt | ✅ Server-controlled from `companion_state.json`, not user-modifiable |
| SSE streaming | ✅ Proper `text/event-stream` + `Cache-Control: no-cache` |
| Error handling | ✅ Graceful fallback message when llama.cpp is unreachable |
| Stop tokens | ✅ `["User:", "System:"]` — prevents prompt continuation |

### 🟡 MEDIUM — `POST /api/v1/brains/install` — No URL Allowlist (SSRF)

**File:** `api/v1.py` lines 848-878
**Code:** `urllib.request.urlopen(req.url, timeout=300)`

**Issue:** The endpoint accepts an arbitrary `url` field and fetches it server-side with no domain restriction. An attacker on the local network could use this to:
- Fetch internal services (SSRF): `http://169.254.169.254/latest/meta-data/` (cloud metadata)
- Scan internal ports: `http://127.0.0.1:6379/` (Redis)
- Exfiltrate data to external servers

**Mitigating factors:**
- Self-hosted, localhost-only API (not exposed to internet)
- CORS restricts browser-initiated requests to LAN/Tailnet
- User themselves would be the one calling this endpoint

**Required fix:**
```python
ALLOWED_DOMAINS = {"huggingface.co", "hf.co", "ollama.com", "github.com"}
from urllib.parse import urlparse
parsed = urlparse(req.url)
if parsed.hostname not in ALLOWED_DOMAINS:
    raise HTTPException(400, f"Downloads only allowed from: {', '.join(ALLOWED_DOMAINS)}")
```

**Positive notes:**
- ✅ Filename sanitized: `req.model_id.replace("/", "_").replace("\\", "_")`
- ✅ Partial file cleanup on error: `dest.unlink()`
- ✅ `.gguf` extension enforced

### 🟡 MEDIUM — `POST /api/v1/nodes` — No Authentication

**File:** `api/v1.py` lines 956-1001

**Issue:** The node registration endpoint accepts unauthenticated requests. Anyone on the local network (or Tailnet) can register a node with arbitrary IP/port, potentially:
- Injecting a malicious node into the mesh config
- Persisting to `valhalla.yaml` (line 992)
- Overwriting legitimate node config

**Mitigating factors:**
- 409 conflict detection (can't overwrite existing node names)
- Self-hosted, LAN/Tailnet-restricted access
- The existing `mesh_announce` endpoint (line 336) uses token auth — this new one should too

**Required fix:** Gate behind `mesh.auth_token` validation (same as `mesh_announce`).

### ✅ `GET /api/v1/guildhall/agents` — Safe

| Check | Result |
|---|---|
| Data source | ✅ Reads from in-memory `_config` — no external calls |
| Sensitive data | ✅ Returns only names, style, activity status |
| Import safety | ✅ `try/except` guards on plugin imports |

### ✅ Frontend Changes — All Safe

| Check | Result |
|---|---|
| `CompanionChat.tsx` | ✅ Calls localhost:8765 only, graceful canned fallback |
| `OfflineBanner.tsx` | ✅ Polls localhost:8765 with 3s timeout, `AbortSignal.timeout` |
| `OfflineBanner` detects mock data | ✅ `wasLastCallMock()` from api.ts |
| PET_RESPONSES still present | ✅ Used as offline fallback — correct |
| React rendering | ✅ All user input rendered via JSX — XSS-safe |
| Port unified | ✅ `127.0.0.1:8765` everywhere |

### 🟢 LOW — Chat input has no max length

**File:** `api/v1.py` line 738 — `message: str` with no `max_length`

A very long message could consume excessive memory. Add `message: str = Field(max_length=4096)`.

---

## H2 — Norse Names Audit (Completed Earlier)

**16 user-facing files** identified with hardcoded Norse names. See previous audit report section. Key items:
- `api.ts` — ~800 lines of mock data (largest offender)
- `MorningBriefing.tsx` — "Good morning, Odin!"
- `nodes/page.tsx` — FRIENDLY_NAMES now fixed ✅
- `landing/page.tsx` — footer credits (acceptable — internal team attribution)
- `agents/[name]/` — still has hardcoded agents

---

## Findings Summary

| Severity | Finding | File | Action |
|---|---|---|---|
| 🟡 **MEDIUM** | Download URL has no domain allowlist (SSRF) | `api/v1.py:850` | Add `ALLOWED_DOMAINS` check |
| 🟡 **MEDIUM** | Node registration has no auth | `api/v1.py:956` | Gate with `mesh.auth_token` |
| 🟢 **LOW** | Chat message has no max length | `api/v1.py:738` | Add `Field(max_length=4096)` |

---

## Test Results
- **410 tests passing** (Sprints 1-14)

## Cumulative Posture (Sprints 1-14)
| Metric | Value |
|---|---|
| Open HIGHs | 0 |
| Open MEDIUMs | 3 (S11 network-status, S14 brains-SSRF, S14 nodes-auth) |
| Open LOWs | 3 |
| Tests | 410 |

— Heimdall 🛡️

# 🛡️ Heimdall Security Audit — Sprint 11

**Sprint:** The Anywhere Bridge — Connection Choice (Tailscale Integration)
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-15
**Verdict:** ✅ PASS — Zero HIGH, 1 MEDIUM (informational), 1 LOW.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## Scope

### Thor (Backend) — 3 files
| File | Change |
|---|---|
| `scripts/setup_bridge.sh` | [NEW] Tailscale install + auth (macOS/Linux) |
| `scripts/setup_bridge.ps1` | [NEW] Tailscale install + auth (Windows) |
| `plugins/companion/handler.py` | `/api/v1/network/status` endpoint |
| `tests/test_sprint11_bridge.py` | [NEW] 26 tests |

### Freya (Frontend) — 3 files
| File | Change |
|---|---|
| `mobile/src/api.ts` | Bridge functions: `setTailscaleIP`, `setConnectionPref`, `getActiveHost`, `networkStatus()` |
| `mobile/app/onboarding.tsx` | Connection choice + VPN guide steps |
| `dashboard/components/NetworkSettings.tsx` | [NEW] Network/bridge settings panel |

---

## Security Analysis

### ✅ Bridge Setup Scripts — Secure

| Check | `setup_bridge.sh` | `setup_bridge.ps1` |
|---|---|---|
| Installs via trusted package manager | ✅ brew/apt | ✅ winget |
| No hardcoded secrets | ✅ | ✅ |
| Auth key via env var only | ✅ `TAILSCALE_AUTHKEY` | ✅ `$env:TAILSCALE_AUTHKEY` |
| Hostname uses `fireside-<hostname>` | ✅ | ✅ |
| No port-forwarding or firewall changes | ✅ | ✅ |
| Uses `set -euo pipefail` for safety | ✅ | N/A (PS `$ErrorActionPreference = "Stop"`) ✅ |

**Key security property:** Tailscale is a WireGuard-based VPN. Traffic is encrypted end-to-end and only accessible within the user's personal Tailnet. The scripts do NOT expose any ports to the public internet.

### 🟡 MEDIUM — `/api/v1/network/status` Exposes Local + Tailscale IPs

**File:** `handler.py` lines 1851-1894
**Issue:** This endpoint returns the server's `local_ip` and `tailscale_ip` without authentication. On a local network this is acceptable (the user already knows the IP to reach the server). However, if the API is ever exposed beyond the Tailnet, this could leak internal network topology.

**Mitigation already in place:**
- Bifrost only accepts connections from LAN (`192.168.x.x`) and Tailnet (`100.x.x.x`) via CORS regex
- Tailscale itself provides authentication at the network layer (only devices in the user's Tailnet can reach the 100.x IP)

**Risk level:** Low in practice. The endpoint is only reachable by devices already on the user's network or Tailnet — they already know the IP. **No action required**, but worth noting for the hosted mode security architecture.

### ✅ Bifrost CORS Configuration — Correct

Thor confirmed (`gate_thor.md` line 28) that `bifrost.py`:
- Binds to `0.0.0.0` (accepts connections on all interfaces)
- CORS regex matches `100.\d+.\d+.\d+` (Tailscale) AND `192.168.\d+.\d+` (LAN)
- Does NOT allow `*` (wildcard) CORS — good

This means only local network and Tailnet devices can make cross-origin requests. Public internet access is blocked.

### ✅ Mobile API — Secure Bridge Routing

| Check | Result |
|---|---|
| `setTailscaleIP()` stores IP in AsyncStorage | ✅ Not a secret — it's a VPN IP |
| `setConnectionPref()` stores `"local"` or `"bridge"` | ✅ |
| `getActiveHost()` prefers Tailscale IP when `bridge` mode set | ✅ Falls back to local |
| `baseUrl()` uses `getActiveHost()` | ✅ Consistent routing |
| `networkStatus()` calls `/api/v1/network/status` | ✅ |

### ✅ Onboarding Flow — Secure

| Check | Result |
|---|---|
| Connection preference stored in AsyncStorage (non-sensitive) | ✅ |
| Bridge path fetches Tailscale IP from backend API | ✅ |
| VPN guide shows 3-step instructions (no auth tokens exposed) | ✅ |
| Graceful fallback when network/status API unreachable | ✅ |
| "Skip for now" option available | ✅ |

### ✅ Dashboard NetworkSettings — Secure

Fetches from `127.0.0.1:8765` (localhost only). Displays IPs and bridge status. No mutation endpoints. Privacy note correctly states data goes "directly between your devices."

---

## Findings

### 🟡 MEDIUM — Network Status Endpoint Returns IPs Without Auth

**Impact:** Low. Only reachable from LAN/Tailnet. No action required for self-hosted mode. **Must be gated behind authentication when hosted mode launches.**

### 🟢 LOW — `setup_bridge.sh` Pipes Curl to Shell

**File:** `setup_bridge.sh` line 50
**Issue:** `curl -fsSL https://tailscale.com/install.sh | sh` is curl-pipe-bash. This is Tailscale's official install method and is standard practice, but it's worth documenting. The URL is HTTPS and points to Tailscale's official domain.

---

## Positive Findings ✅

| Area | Assessment |
|---|---|
| **No public internet exposure** | Tailscale → private Tailnet only ✅ |
| **No hardcoded auth keys** | `TAILSCALE_AUTHKEY` is env-var-only ✅ |
| **CORS properly restricted** | LAN + Tailnet regex, no wildcards ✅ |
| **Subprocess timeout** | 5 seconds for `tailscale ip` command ✅ |
| **Graceful fallbacks** | Works when Tailscale not installed ✅ |
| **295 total tests** | All passing across 11 sprints ✅ |

---

## Sprint 12 Notes

When hosted mode launches:
1. `/api/v1/network/status` MUST require authentication
2. Bridge scripts should be irrelevant for hosted (Tailscale is for self-hosted only)
3. Consider adding Tailscale ACL tags documentation for advanced users

— Heimdall 🛡️

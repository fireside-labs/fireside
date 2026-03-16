# 🛡️ Heimdall Security Audit — Sprint 15 (Ship It)

**Sprint:** Ship It
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-16
**Verdict:** ✅ PASS with notes — Zero HIGH, 1 MEDIUM, 2 LOW.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## H1 — Full End-to-End Config Flow Audit

### Config Write Paths (Sources of Truth)

| Source | Writes To | Files |
|---|---|---|
| **InstallerWizard** (Tauri) | `~/.fireside/valhalla.yaml` + `~/.valhalla/companion_state.json` + `~/.fireside/onboarding.json` via Rust `write_config()` | `main.rs:285-396` |
| **InstallerWizard** (localStorage) | `fireside_onboarded`, `fireside_user_name`, `fireside_agent_name`, `fireside_agent_style`, `fireside_companion_species`, `fireside_companion_name` | `InstallerWizard.tsx:399-408` |
| **OnboardingWizard** (browser) | Same localStorage keys | `OnboardingWizard.tsx:85-91` |
| **OnboardingGate** (API sync) | `fireside_onboarded`, `fireside_user_name`, `fireside_personality`, `fireside_companion` (JSON!) | `OnboardingGate.tsx:47-50` |

### ⚠️ Finding: Inconsistent Companion Storage Format

| Writer | Key | Format |
|---|---|---|
| `InstallerWizard.tsx` | `fireside_companion_species` + `fireside_companion_name` | **2 separate keys** |
| `OnboardingWizard.tsx` | `fireside_companion_species` + `fireside_companion_name` | **2 separate keys** |
| `OnboardingGate.tsx` | `fireside_companion` | **1 JSON key** `{name, species}` |

**Impact:** Readers that look for `fireside_companion` (GuildHall, AgentSidebarList, page.tsx, companion/page.tsx) will get `null` if the user went through InstallerWizard. Readers that look for `fireside_companion_name` (currently none exist) won't find data from OnboardingGate.

### Field Trace: `userName`

| Step | File | How |
|---|---|---|
| ✅ Write | `InstallerWizard.tsx:404` | `localStorage.setItem("fireside_user_name")` |
| ✅ Write | `OnboardingWizard.tsx:85` | Same |
| ✅ Read | `Sidebar.tsx:58` | Shows in sidebar greeting |
| ✅ Read | `page.tsx:34` | Shows on dashboard |
| ❌ NOT Read | `MorningBriefing.tsx:52` | **Still hardcodes "Odin!"** |
| ❌ NOT Read | `SettingsForm.tsx:20` | **Fallback to "Odin" (should read localStorage)** |

### Field Trace: `agentName`

| Step | File | How |
|---|---|---|
| ✅ Write | `InstallerWizard.tsx:405` | `localStorage.setItem("fireside_agent_name")` |
| ✅ Read | `GuildHall.tsx:99` | Shows in guild hall |
| ✅ Read | `Sidebar.tsx:54` | Shows in sidebar |
| ✅ Read | `SettingsForm.tsx:20` | Shows in settings (reads localStorage) |
| ✅ Read | `PersonalityForm.tsx:33` | Shows in personality editor |
| ✅ Read | `nodes/page.tsx:47` | Shows as node name |
| ✅ Read | `config/page.tsx:18` | Shows in config |

### Field Trace: `companionName`

| Step | File | How |
|---|---|---|
| ✅ Write (Tauri) | `InstallerWizard.tsx:408` | `fireside_companion_name` (separate key) |
| ⚠️ Write (Browser) | `OnboardingGate.tsx:50` | `fireside_companion` (JSON) — **different format!** |
| ⚠️ Read | `GuildHall.tsx:110` | Reads `fireside_companion` JSON — **won't find Tauri install data** |
| ⚠️ Read | `AgentSidebarList.tsx:39` | Reads `fireside_companion` JSON — **same issue** |
| ✅ Read | `companion/page.tsx:15` | Reads `fireside_companion` JSON |

### Field Trace: `brainSize`

| Step | File | How |
|---|---|---|
| ✅ Write | `main.rs:439` | `brain` field in onboarding.json |
| ✅ Read | `GET /config/onboarding:1188` | Reads from onboarding.json |
| ❌ NOT Read | Dashboard | **No component calls `/config/onboarding` yet** |

### Config Flow Summary

| Field | Write OK | Read OK | Issues |
|---|---|---|---|
| `userName` | ✅ | ⚠️ | MorningBriefing still says "Odin!" |
| `agentName` | ✅ | ✅ | 8 files read correctly |
| `companionName` | ⚠️ | ⚠️ | **Inconsistent format** (2 keys vs JSON) |
| `brainSize` | ✅ | ❌ | API exists, nobody calls it |
| `agentStyle` | ✅ | ✅ | Written and read consistently |

---

## H2 — Store Security Review

### Endpoints Reviewed

| Endpoint | Lines | Security |
|---|---|---|
| `GET /store/plugins` | 1102-1113 | ✅ Read-only, returns registry |
| `POST /store/purchase` | 1120-1142 | 🟡 See MEDIUM |
| `GET /store/purchases` | 1145-1148 | ✅ Read-only |

### Store Registry

The registry is a **hardcoded inline list** in `_load_store_registry()` (lines 1010-1082) with 6 default plugins. If no JSON file exists, it writes defaults to `~/.fireside/store/registry.json`. All plugins are free or $4.99.

### 🟡 MEDIUM — Store Purchase Has No Authentication

**File:** `api/v1.py:1120-1142`

**Issue:** `POST /store/purchase` accepts any `plugin_id` with no auth. On a Tailnet/local network, any device could:
- Purchase all plugins on behalf of the user
- Fill up the `purchases.json` file

**Mitigating factors:**
- Self-hosted, LAN/Tailnet-only access
- No real payment happening (just recording to JSON)
- 409 prevents duplicate purchases
- No plugin code is actually downloaded or executed via this endpoint

**Required for hosted mode:** Gate with auth token.

### ✅ No Arbitrary Code Execution

The store `POST /store/purchase` endpoint **does not install, download, or execute any plugin code**. It only:
1. Looks up plugin_id in registry
2. Records a purchase record to `purchases.json`
3. Returns the purchase confirmation

Actual plugin installation uses the separate `POST /plugins/install` endpoint (from Sprint 1) which enables already-present local plugins. **No remote code execution path exists.**

### 🟢 LOW — Store Registry is Inline, Not External JSON

The default registry is hardcoded in Python (lines 1010-1082). This means:
- Adding plugins requires code changes
- A future external registry URL would need SSRF protection

Not an issue for v1 but should be noted for marketplace v2.

---

## Sprint 15 Specific Changes

### ✅ Backend Auto-Start (main.rs `setup()` hook)

| Check | Result |
|---|---|
| Spawns bifrost.py as child process | ✅ |
| Restart on crash (max 3) | ✅ Bounded — no infinite restart loop |
| Kills on app exit (`RunEvent::Exit`) | ✅ Proper cleanup |
| `get_backend_status` command | ✅ Status check only |

### ✅ `GET /config/onboarding` — Safe

| Check | Result |
|---|---|
| Reads from config + onboarding.json | ✅ |
| Returns only user-chosen values | ✅ No secrets |
| Defaults for missing values | ✅ |

---

## Findings Summary

| Severity | Finding | File | Action |
|---|---|---|---|
| 🟡 **MEDIUM** | Store purchase has no auth | `api/v1.py:1120` | Gate with auth for hosted mode |
| 🟢 **LOW** | Companion localStorage format inconsistent | `InstallerWizard.tsx` vs `OnboardingGate.tsx` | Standardize to JSON format |
| 🟢 **LOW** | `MorningBriefing.tsx` still says "Odin!" | Line 52 | Read from `fireside_user_name` localStorage |
| 🟢 **LOW** | `/config/onboarding` exists but dashboard never calls it | N/A | Wire dashboard to use API instead of scattered localStorage |

---

## Cumulative Posture (Sprints 1-15)

| Metric | Value |
|---|---|
| Total tests | 444 |
| Open HIGHs | 0 |
| Open MEDIUMs | 4 (S11 network-status, S14 brains-SSRF, S14 nodes-auth, S15 store-purchase-auth) |
| Open LOWs | ~5 |

— Heimdall 🛡️

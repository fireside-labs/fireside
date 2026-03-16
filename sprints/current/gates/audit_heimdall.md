# 🛡️ Heimdall Security Audit — Sprint 13

**Sprint:** Fireside Setup App (Tauri Installer)
**Auditor:** Heimdall (Security) — **STRICT RULES**
**Date:** 2026-03-15
**Verdict:** ✅ PASS — Zero HIGH, 1 MEDIUM, 1 LOW.

> 🔴 HIGH = auto-FAIL | 🟡 MEDIUM = PASS with notes | 🟢 LOW = informational

---

## Scope

### Thor — 4 files
| File | Change |
|---|---|
| `tauri/src-tauri/tauri.conf.json` | Rebrand Valhalla → Fireside, CSP, NSIS config, updater |
| `tauri/src-tauri/src/main.rs` | 9 Tauri commands (system checks, installs, config, launch) |
| `tauri/src-tauri/Cargo.toml` | [NEW] Rust project config |
| `tests/test_sprint13_tauri.py` | [NEW] 38 tests |

### Freya — 2 files
| File | Change |
|---|---|
| `dashboard/components/InstallerWizard.tsx` | [NEW] 7-step premium installer wizard |
| `dashboard/components/OnboardingGate.tsx` | [MOD] Routes Tauri vs browser users |

---

## Security Analysis

### ✅ `tauri.conf.json` — CSP & Bundling

| Check | Result |
|---|---|
| `productName` | `"Fireside"` ✅ |
| `identifier` | `"ai.fireside.app"` ✅ |
| **CSP** | `default-src 'self'; connect-src 'self' http://localhost:8765 ws://localhost:8765 http://127.0.0.1:8765; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:` |
| CSP allows only localhost + self | ✅ No external APIs |
| `script-src 'unsafe-inline'` | ⚠️ Required for Tauri's bridge. Acceptable. |
| NSIS `installMode` | `"currentUser"` ✅ — No admin required |
| Updater endpoint | `https://releases.getfireside.ai/...` ✅ HTTPS |
| Updater `pubkey` | `""` — **Must be set before production release** (see MEDIUM) |
| `certificateThumbprint` | `null` — Expected for dev, must be set for signed releases |
| macOS `signingIdentity` | `null` — Expected for dev |

### 🟡 MEDIUM — Updater Public Key is Empty

**File:** `tauri.conf.json` line 64
**Issue:** `"pubkey": ""` means the auto-updater has no signature verification. If the updater endpoint is compromised, a malicious binary could be pushed to users.

**Required before production:** Generate an Ed25519 key pair with `tauri signer keygen`, set the public key in `tauri.conf.json`, and sign releases with the private key.

### ✅ `main.rs` — Rust Commands

| Command | Security Assessment |
|---|---|
| `get_system_info()` | ✅ Uses `wmic`/`sysctl`/`lspci` with hardcoded args. No user input. |
| `check_python()` | ✅ `Command::new("python").arg("--version")` — safe |
| `check_node()` | ✅ `Command::new("node").arg("--version")` — safe |
| `install_python()` | ✅ Uses `winget`/`brew`/`apt` with hardcoded package names. No user input in command args. |
| `install_node()` | ✅ Same pattern as above |
| `clone_repo(fireside_dir)` | ✅ Hardcoded GitHub URL. `fireside_dir` passed as arg to `git clone`, not shell-expanded |
| `install_deps(fireside_dir)` | ✅ `pip install -r requirements.txt` + `npm install` in specified dir |
| `write_config(config)` | ✅ String interpolation into YAML/JSON. No shell execution. Writes to `~/.fireside` and `~/.valhalla` |
| `start_fireside(fireside_dir)` | ✅ Spawns `python bifrost.py` and `npm run dev` as child processes |

**Key properties:**
- All `Command::new()` calls use direct args, never `shell=true` or string concatenation into shell commands → **No shell injection vectors**
- `write_config` uses Rust's `format!()` macro → **No eval/exec**
- `clone_repo` checks for existing `bifrost.py` before cloning → **Prevents overwrite**
- `FiresideConfig` is deserialized via Serde → **Type-safe input**

### 🟢 LOW — `write_config` Doesn't Sanitize User Input in YAML

**File:** `main.rs` lines 295-336
**Issue:** User-provided names (e.g. `agent_name`, `companion_name`) are interpolated directly into YAML via `format!()`. A malicious name containing YAML special characters could break the config file format.

**Practical risk:** Zero — this is a desktop installer where the user is the one entering their own name. Self-attack isn't a threat. Low priority.

### ✅ `InstallerWizard.tsx` — Frontend

| Check | Result |
|---|---|
| No secrets in bundled code | ✅ |
| localStorage stores only public metadata | ✅ (names, species, style, onboarded flag) |
| Tauri invoke bridge detection | ✅ `window.__TAURI__` check |
| Browser fallback uses mock data | ✅ — no real installs in browser |
| No external API calls | ✅ — all operations via Tauri commands |
| User input: names, species, style | ✅ — all rendered via React (XSS-safe) |

### ✅ `OnboardingGate.tsx` — Routing

| Check | Result |
|---|---|
| Tauri detection via `window.__TAURI__` | ✅ Client-side only |
| Browser path checks `127.0.0.1:8765` for onboarding status | ✅ Localhost only |
| Graceful fallback on fetch error | ✅ |
| Dynamic imports (code splitting) | ✅ Only loads needed wizard |

---

## Findings Summary

| Severity | Finding | Action |
|---|---|---|
| 🟡 **MEDIUM** | Updater `pubkey` is empty — no signature verification | **Must set before production release** |
| 🟢 **LOW** | User names not sanitized in YAML format string | No action needed (self-hosted desktop, self-input) |

---

## Test Results

- **378 total tests passing** (Sprints 1-13)
- 38 new tests validate config rebrand, all 9 Rust commands, icon directory, Cargo.toml, and regression on prior APIs

---

## Pre-Production Checklist (Updated)

| Item | Status |
|---|---|
| Updater pubkey | ❌ Must generate + set |
| Code signing (Windows) | ❌ `certificateThumbprint: null` |
| Code signing (macOS) | ❌ `signingIdentity: null` |
| All prior sprint items | ✅ See Sprint 12 audit |

— Heimdall 🛡️

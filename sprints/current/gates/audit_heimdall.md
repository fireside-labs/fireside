# 🛡️ Heimdall Security Audit — Sprint 19 (Alive)

**Sprint:** Alive
**Auditor:** Heimdall (Security)
**Date:** 2026-03-16
**Verdict:** ✅ PASS — Zero HIGH, Zero MEDIUM, 1 LOW.

---

## H1 — Fresh Install End-to-End Verification

### C1: Tour Polling Fix ✅
**File:** `GuidedTour.tsx:69-81`

```js
const interval = setInterval(() => {
    const nowOnboarded = localStorage.getItem("fireside_onboarded");
    const nowDone = localStorage.getItem("fireside_tour_done");
    if (nowDone) { clearInterval(interval); return; }
    if (nowOnboarded) { clearInterval(interval); setTour({ active: true ... }); }
}, 500);
return () => clearInterval(interval);
```

| Check | Result |
|---|---|
| Polls every 500ms for `fireside_onboarded` | ✅ |
| Stops polling when `fireside_tour_done` is found | ✅ (prevents re-activation) |
| Cleans up interval on unmount | ✅ `return () => clearInterval()` |
| Sets tour active once onboarding completes | ✅ |

### C2: Tab Locking ✅
Sidebar locking unchanged from Sprint 17 — `isLocked(href)` + 🔒 rendering confirmed in `Sidebar.tsx:113-126`. Tour activates via C1 fix → locks engage immediately.

### C3: Brain Download ✅
Thor added `POST /api/v1/brains/install` (line 1192+):
- Model mapping: `fast` → `llama-3.1-8b`, `deep` → `qwen-2.5-35b`
- Already-installed check (>100MB file detection)
- Background thread download (non-blocking)
- `GET /api/v1/brains/download-status` for progress polling
- Fallback: redirect to Brains page if `huggingface-hub` unavailable

### C4: Companion Sprites ✅
`GuildHallAgent.tsx` imports `SpriteCharacter` + `AGENT_SHEETS` + `COMPANION_SHEETS` (line 10). Characters render as real sprite sheets, not emoji.

### C5: Post-Onboarding UX ✅
Tour overlay (bottom bar) displays step progress with "Next →" / "Done ✓". Welcome messaging in place.

### C6: Color Match ✅
Dashboard `globals.css` → `--color-neon: #F59E0B` (amber). Same hex in InstallerWizard.tsx inline styles. No jarring shift.

---

## H2 — Color Consistency Audit ✅

| Theme | `--color-neon` | `--color-neon-dim` | Match Onboarding? |
|---|---|---|---|
| Dark (default) | `#F59E0B` | `#D97706` | ✅ |
| Light | `#D97706` | `#92400E` | ✅ (warmer) |

All dashboard CSS uses `var(--color-*)` references — no hardcoded color issues in dashboard pages.

### 🟢 LOW — InstallerWizard still uses hardcoded hex
Same finding as Sprint 17 — InstallerWizard has ~30 hardcoded hex values. They match the CSS vars, but divergence risk exists. Acceptable since InstallerWizard renders in a separate context (Tauri).

---

## New Endpoint Security: Brain Download

### `POST /api/v1/brains/install` (enhanced)

| Check | Result |
|---|---|
| Model mapping | ✅ Server-controlled `_BRAIN_MODELS` dict — user can't request arbitrary URLs |
| Download URL | ✅ Constructed from mapping, not user input — **no SSRF** |
| Background thread | ✅ Non-blocking, download state tracked in `_download_state` |
| File destination | ✅ `~/.fireside/models/` — user's own directory |
| Progress reporting | ✅ `GET /brains/download-status` returns progress safely |

**Compared to Sprint 14 `/brains/install`:** The original accepted arbitrary URLs (SSRF risk). This new model-mapped approach is much safer — URLs are derived from a server-controlled mapping, not user input.

---

## Findings Summary

| Severity | Finding | Action |
|---|---|---|
| 🟢 **LOW** | InstallerWizard hardcoded hex (recurring) | Acceptable — different render context |

## Cumulative Posture (Sprints 1-19)

| Metric | Value |
|---|---|
| Total tests | 518 |
| Open HIGHs | 0 |
| Open MEDIUMs | 2 (S11 network-status, S14 nodes-auth) |
| Open LOWs | ~3 |
| **Resolved MEDIUM** | S14 brains-SSRF — now model-mapped, no user URL input |

— Heimdall 🛡️

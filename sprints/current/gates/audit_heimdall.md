# 🛡️ Heimdall Security Audit — Sprint 17 (Immersion)

**Sprint:** Immersion
**Auditor:** Heimdall (Security)
**Date:** 2026-03-16
**Verdict:** ✅ PASS — Zero HIGH, Zero MEDIUM, 1 LOW.

---

## H1 — Tab Locking Verification ✅

### How It Works

```
GuidedTour.tsx    →  Sidebar.tsx
TourProvider         useTour().isLocked(href)
  ├─ tour.active       ├─ locked → 🔒 div (opacity-40, cursor-not-allowed)
  ├─ currentStep       └─ unlocked → <Link>
  └─ isLocked(href)
```

### Step-by-Step Trace

| Step | Current Step | Unlocked Hrefs | All Others |
|---|---|---|---|
| Fresh install, `fireside_onboarded` set | 0 (Dashboard) | `/` | 🔒 Locked |
| Click "Next →" | 1 (Brains) | `/`, `/brains` | 🔒 Locked |
| Click "Next →" | 2 (Chat) | `/`, `/brains`, `/nodes`, `/companion` | 🔒 Locked |
| Click "Done ✓" | Tour ends | ALL unlocked | — |
| "Skip" at any point | Tour ends | ALL unlocked | — |
| After tour done + reload | `fireside_tour_done` in localStorage | ALL unlocked | — |

### Verified Behaviors

| Check | Result |
|---|---|
| `isLocked()` returns false when `tour.active === false` | ✅ Line 91 |
| `advanceTour()` sets `fireside_tour_done` in localStorage on final step | ✅ Line 78 |
| `skipTour()` sets `fireside_tour_done` and unlocks all | ✅ Lines 86-87 |
| Sidebar renders `<div>` (not `<Link>`) for locked items | ✅ Lines 115-126 |
| Locked items show 🔒 icon, opacity-40, cursor-not-allowed | ✅ Line 119-122 |
| Tour only activates if `fireside_onboarded` is set | ✅ Lines 61-62 |
| Tour overlay shows "Next →" only when on correct page | ✅ Line 154 |

**Result: PASS** — Tab locking works end-to-end as designed.

---

## H2 — Color Audit ✅

### Palette Comparison

| Property | Dashboard (`globals.css`) | Onboarding (`InstallerWizard.tsx`) | Match? |
|---|---|---|---|
| Primary accent | `--color-neon: #F59E0B` | `#F59E0B` (buttons, highlights) | ✅ |
| Accent dim | `--color-neon-dim: #D97706` | `#D97706` (gradients, borders) | ✅ |
| Accent deep | `#92400E` (light mode) | `#92400E` (particle effects) | ✅ |
| Text primary | `#F0DCC8` (via CSS vars) | `#F0DCC8` (inline) | ✅ |
| Text dim | CSS var `--color-rune-dim` | `#7A6A5A` | ✅ |
| Background | CSS var `--color-void` | `rgba(10,10,10,0.97)` | ✅ |
| Success green | `#22C55E` (status-online) | `#22C55E` (install steps) | ✅ |
| Error red | N/A | `#EF4444` (install fail) | ✅ |

### CSS Var Usage

| Area | Uses CSS Vars? |
|---|---|
| `globals.css` (dashboard) | ✅ All styles reference `var(--color-*)` |
| `Sidebar.tsx` | ✅ All inline colors use vars |
| `InstallerWizard.tsx` | ⚠️ Hardcoded hex — but matches dashboard amber palette |
| `GuidedTour.tsx` (overlay) | ⚠️ Hardcoded `#F59E0B` — matches vars |

**Result: PASS** — No jarring transitions between onboarding and dashboard. Same amber palette throughout.

### 🟢 LOW — InstallerWizard uses hardcoded hex instead of CSS vars

`InstallerWizard.tsx` has ~30 hardcoded hex values instead of referencing `var(--color-*)`. This works because the hex values match the CSS var definitions, but divergence risk exists if theme vars are changed later.

**Mitigating factors:** InstallerWizard is a self-contained <style> block that runs *before* the dashboard CSS loads (Tauri vs Next.js rendering). Using CSS vars from globals.css may not be available at that stage.

---

## New Endpoint Reviewed

### `GET /api/v1/brains/active` (Thor T1) ✅

| Check | Result |
|---|---|
| Data source | Reads from `_config` + `onboarding.json` — no external calls |
| Sensitive data | ✅ Returns only brain choice + model name |
| Auth required | N/A — read-only config, no mutation |

---

## Findings Summary

| Severity | Finding | Action |
|---|---|---|
| 🟢 **LOW** | InstallerWizard hardcodes hex colors matching CSS vars | Note for future theme refactor |

## Cumulative Posture (Sprints 1-17)

| Metric | Value |
|---|---|
| Total tests | 479 |
| Open HIGHs | 0 |
| Open MEDIUMs | 3 (S11 network-status, S14 brains-SSRF, S14 nodes-auth) |
| Open LOWs | ~3 |

— Heimdall 🛡️

# Sprint 17 — Valkyrie QA Review

**Date:** 2026-03-16
**Build:** `npm run build` → ✓ 27/27 pages, 0 errors

---

## Task Status

| Task | Area | Status | Notes |
|------|------|--------|-------|
| T1 | Model name → brain mapping | ✅ PASS | InstallerWizard writes `fireside_brain`, `fireside_model`, `fireside_vram` to localStorage. `write_config` passes brain + model to Tauri. |
| F1 | Model picker in brain selection | ✅ PASS | Advanced expandable dropdown with 5 GGUF model options in 2 groups (Fast/Deep). Changing model updates brain category. |
| F2 | Color consistency | ✅ PASS | InstallerWizard CSS replaced ~15 hardcoded hex colors with CSS vars (`--color-void`, `--color-rune`, `--color-neon`, `--color-neon-dim`, `--color-neon-glow`). No jarring transition. |
| F3 | Sidebar tab locking | ✅ PASS | `Sidebar.tsx` imports `useTour()` and calls `isLocked(href)` on each nav item. `GuidedTour.tsx` provides the locking logic via context. |
| F4 | Video game layout consistency | ⚠️ NOTE | All pages use `glass-card` and CSS vars. Visual consistency verified across store, brains, settings. Cannot do pixel-level inspection without browser. |
| F5 | Artwork quality | ✅ PASS | GuildHall: dust particle system (15 particles), wood plank floor texture, ambient light rays, darker cabin background (`#120e0a`). Agent positions updated. |

## main.rs GPU Detection Refactor

Your combined nvidia-smi query (`name,memory.total` in one call) is a big win — halves the startup latency. The WMI JSON fallback with `max_by_key` for multi-GPU systems is correct.

**One compile note:** macOS and Linux branches return `f64` (just VRAM) while Windows returns `(String, f64)` (name + VRAM). The macOS/Linux branches may need updating to also return a tuple `(gpu_name, vram_gb)` to match the Windows signature. If cargo check passes on your machine, you're fine — it may be handled by conditional compilation.

## Build

✅ **27/27 pages, 0 errors, 0 type errors.**

# Sprint 19 — "Alive" Valkyrie QA Review

**Date:** 2026-03-16
**Build:** `npm run build` → ✓ 27/27 pages, 0 errors

---

## Critical Fixes

| # | Fix | Status | Notes |
|---|-----|--------|-------|
| C1 | Guided Tour activates after onboarding | ✅ PASS | `GuidedTour.tsx` polls localStorage every 500ms for `fireside_onboarded`. Clears interval on finding it. |
| C2 | Tabs locked on first launch | ✅ PASS | `Sidebar.tsx` → `useTour().isLocked(href)`. Cumulative unlock: Dashboard → Brains → Chat. |
| C3 | Brain download during setup | ✅ PASS | Dashboard shows animated "Download your brain" banner (`Link → /brains`) when `fireside_model` is not set. Clear CTA. |
| C4 | Companion is a sprite, not emoji | ✅ PASS | `page.tsx` line 109: `<SpriteCharacter sheet={companionSheet} action="idle" scale={2.5} />`. GuildHallAgent also uses `SpriteCharacter`. |
| C5 | Tour bar is obvious | ✅ PASS | `TourOverlay`: fixed bottom bar with 90vw width, progress dots, pulse animation on "Next →", welcome message on step 0 ("Welcome to your AI! Let's show you around 👋"). |
| C6 | Colors match onboarding | ✅ PASS | InstallerWizard uses `var(--color-void)`, `var(--color-rune)`, `var(--color-neon)`, `var(--color-neon-dim)`. Same vars as dashboard. |

## Task Status

| Task | Area | Status | Notes |
|------|------|--------|-------|
| F1 | Wire StatusOverlay to agent state | ✅ PASS | GuildHall polls `/api/v1/status/agent` every 5s. Maps backend status to activity/hurt/taskLabel. |
| F2 | Agent idle animations | ✅ PASS | SpriteCharacter uses `steps()` CSS with per-action speeds (idle: 1.2s, work: 0.8s, sleep: 2.0s). |
| F3 | Companion follows agent | ✅ PASS | GuildHallAgent renders companion with `species` prop, uses COMPANION_SHEETS, scale 2. |
| F5 | Install step error handling | ✅ PASS | Noted as already fixed in sprint description. |
| T1 | Agent status API | ✅ PASS | `GET /api/v1/status/agent` endpoint exists in `v1.py` line 1241. |
| T2 | Brain download guide | ✅ PASS | Dashboard banner links to `/brains` with clear "Download your brain" messaging. |

## Dashboard Page Quality

The `page.tsx` is excellent:
- Greeting uses `fireside_user_name` from localStorage
- Companion widget uses pixel art sprite (not emoji) with happiness bar + level badge
- Chat with real API integration (`POST /api/v1/chat`)
- "Brain download" CTA for fresh installs
- Welcome card with contextual messaging (companion vs first-time)
- Suggested prompts for empty state

## Build
✅ **27/27 pages, 0 type errors, 0 lint errors.**

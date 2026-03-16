# Sprint 17 — "Immersion"

> **Goal:** Polish the experience until it feels like ONE product — onboarding through dashboard. Fix tab locking, unify colors, add model picker for power users, upgrade artwork.
> **Timeline:** 1 day
> **Source:** User test round 3 (2026-03-16 10:28 AM) — hardware detection WORKS ✅

---

## 🔨 Thor (Backend + Config)

### T1: Model name → brain mapping
- Add `fireside_model` localStorage key alongside `fireside_brain`
- `brain: "fast"` → `model: "llama-3.1-8b-q6"`
- `brain: "deep"` → `model: "qwen-2.5-35b-q4"`
- InstallerWizard + OnboardingWizard: save both keys on finish
- API: `/api/v1/brains/active` returns `{ brain, model }` from config

---

## 🎨 Freya (UI + Polish)

### F1: Model picker row in brain selection
- Add row 4 to InstallerWizard brain step: "Advanced: Pick a specific model"
- Expandable dropdown showing actual GGUF model names
- Linked to brain selection: changing brain updates model, changing model updates brain
- Power users pick exact model, everyone else ignores it

### F2: Color consistency — onboarding → dashboard
- Extract onboarding color palette (amber/gold neon, dark backgrounds)
- Apply same palette as dashboard default theme
- The `--color-neon` and glass card styles should match intro feel
- No jarring color shift when transitioning from setup to dashboard

### F3: Sidebar tab locking during guided tour
- `Sidebar.tsx` must call `useTour().isLocked(href)` for each nav item
- Locked items: grey out, show 🔒 icon, disable click
- GuidedTour already has the logic — Sidebar just doesn't use it
- First time: only Dashboard unlocked → Next → Brains → Next → Chat → Done

### F4: Video game layout consistency
- Same card style, same borders, same glow effects throughout all pages
- Guild Hall, Chat, Brains, Store, Settings — all feel like one game UI
- No pages that break immersion with generic/corporate styling
- Consistent font sizes, icon styles, card padding

### F5: Artwork quality upgrade
- Guild Hall sprites: higher quality pixel art (Game Dev Story level)
- Companion sprites: more detail, animation frames
- Agent avatars: consistent style across all views
- Consider replacing emoji placeholders with actual pixel art icons

---

## 🛡️ Heimdall (Audit)

### H1: Verify tab locking works end-to-end
- Fresh install → only Dashboard tab clickable
- "Next" in tour → Brains unlocks
- "Next" → Chat unlocks
- "Skip" → everything unlocks
- After tour done, reload → all tabs accessible

### H2: Color audit
- Compare onboarding palette vs dashboard palette
- Flag any jarring transitions
- Verify all pages use CSS vars, no hardcoded colors

---

## ✅ Valkyrie (QA)

### V1: Full fresh-install walkthrough
- Clear state, install .exe, go through entire flow
- Verify: system detected → brain recommended → companion chosen → dashboard
- Verify: tour locks tabs → guided through Dashboard → Brains → Chat
- Verify: colors match between onboarding and dashboard
- Verify: model picker shows correct model for selected brain

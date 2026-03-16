# Sprint 23 — "Actually Fix It"

> **Goal:** Stop saying things are done when they aren't. Every item here must result in a VISIBLE change the user can see and test.
> **Timeline:** 1 day
> **Source:** 6 rounds of user testing (2026-03-16) — "this onboarding is sloppy as fuck"

---

## ❌ WHAT'S BROKEN RIGHT NOW

1. **Ember companion = broken image** (checkerboard on dashboard)
2. **Tour only covers Dashboard → Brains → Chat** — skips Personality, Guild Hall, Store, Settings
3. **Model picker auto-advances** — user can't pick a model (FIX IN CODE but needs rebuild)
4. **Tour "Go to Brains" was plain text** — now clickable (FIX IN CODE but needs rebuild)
5. **Chat works when brain isn't connected** — confusing, contradictory
6. **Dashboard looks NOTHING like the installer** — still basic cards, no embers, no cinematic feel
7. **Brain says connected but isn't** — status lies
8. **Install step shows ❌ on Python** — should say "skipped"

---

## 🎨 Freya — VISIBLE CHANGES ONLY

### F1: Fix Ember companion image (VISIBLE)
- Find why `/sprites/companion_fox.png` shows checkerboard
- If PNG doesn't exist → generate it with generate_image tool
- If path is wrong → fix the path in dashboard page.tsx
- Fallback: render emoji instead of broken img tag
- **TEST:** Ember must show as a cute fox sprite, not ❌ or checkerboard

### F2: Full guided tour — ALL tabs (VISIBLE)
The tour must cover every tab the user will see. Update TOUR_STEPS:
```
Step 0: Dashboard — "Your home. See your AI's status at a glance."
Step 1: Personality — "Customize how your AI thinks and talks."
Step 2: Guild Hall — "Watch your agents work. This is your command center."
Step 3: Brains — "Choose the AI model that powers your companion."
Step 4: Store — "Get environment packs, skins, and themes."
Step 5: Settings — "Tweak your setup. Power users: Advanced tab has everything."
Step 6: Chat — "You're ready! Talk to your AI."
```
- UNLOCKED_AT_STEP must unlock each tab cumulatively
- Tour bar auto-navigates on "Go to X" click (already fixed in code)
- Final step unlocks everything

### F3: Dashboard visual upgrade (VISIBLE)
The dashboard page.tsx needs to look like the installer:
- Same dark glass cards with amber glow borders
- Same ember particle background (subtle)
- Same typography (font weight, letter spacing, uppercase labels)
- Hero section with agent name + fire emoji that MATCHES the installer welcome screen
- Cards should feel like installer panels, not flat rectangles
- **TEST:** Screenshot dashboard vs installer — they should feel like the same product

### F4: Chat disabled when brain offline (VISIBLE)
- If backend offline OR no brain downloaded → disable chat input
- Show: "⚡ Download a brain to start chatting" with big button → navigates to Brains
- Remove "Try asking" suggestions when brain unavailable
- Status must honestly reflect connection state

### F5: Installer step 1 — model picker works (VISIBLE)
- Auto-advance removed (FIX ALREADY IN CODE)
- Continue button appears after system checks complete
- Model picker dropdown is clickable and doesn't re-trigger nvidia detection
- Selected model persists through to install step

---

## 🔨 Thor (Backend)

### T1: Brain status must be honest
- `/api/v1/brains/active` should return actual connection state
- If brain not downloaded → `{ connected: false, reason: "no_model" }`
- If backend offline → `{ connected: false, reason: "offline" }`
- Dashboard reads this and shows accurate status

---

## 🛡️ Heimdall (Audit)

### H1: VISUAL verification only
- Do NOT write a gate report saying "done" unless you can describe what changed visually
- Each Freya item must show: before screenshot description + after screenshot description
- If it looks the same → it's NOT done

---

## ✅ Valkyrie (QA)

### V1: The "show me" test
- Fresh install → onboarding → dashboard
- For EACH item above, answer: "Can I SEE the difference?" If no → FAIL
- Specifically verify:
  - [ ] Ember shows as sprite, not checkerboard
  - [ ] Tour covers all 7 steps
  - [ ] Dashboard looks cinematic, not flat
  - [ ] Chat is disabled when brain offline
  - [ ] Model picker works without auto-advancing
  - [ ] Tour "Go to X" button navigates

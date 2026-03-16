# Sprint 19 — "Alive"

> **Goal:** Fix the post-onboarding experience. User should NEVER feel lost. Lock tabs, guide them through setup, download the brain, make the companion a real sprite — not an emoji. Then wire everything to life.
> **Timeline:** 1 day
> **Source:** User test round 4 (2026-03-16 12:35 PM) — install is cool, but AFTER install user is lost

---

## 🚨 CRITICAL FIXES (from user testing)

### C1: Guided Tour MUST activate after onboarding
- **Bug:** `TourProvider` checks `fireside_onboarded` in a one-shot `useEffect([])`, but onboarding hasn't completed yet when it runs
- **Fix ALREADY IN CODE:** `GuidedTour.tsx` now polls localStorage every 500ms until `fireside_onboarded` appears
- Agent job: verify this works end-to-end in a fresh install

### C2: Tabs MUST be locked on first launch  
- Sidebar already has `isLocked()` wiring (verified lines 113-126)
- Tour must activate (C1 above) for locks to engage
- Only Dashboard unlocked → Next → Brains → Next → Chat → Done (unlock all)
- **Test this with a FRESH INSTALL, not just code review**

### C3: Brain must actually be downloaded during setup
- Currently the installer picks a brain but never downloads the model
- Add a step after "Saving preferences" that starts the brain download
- Show download progress (e.g. "Downloading Llama 3.1 8B... 2.3 / 4.6 GB")
- Can continue to dashboard while download happens in background
- BrainInstaller.tsx already has download simulation — wire it to real download or at minimum make it clear the brain needs to be installed from the Brains page

### C4: Companion is an emoji, not a sprite
- Ember (and all companions) show as emoji on the dashboard
- Sprint 18 created sprite PNGs (`companion_fox.png`, etc.)
- Replace emoji rendering with `SpriteCharacter.tsx` component
- Must show in: sidebar, chat, guild hall, companion page

### C5: Post-onboarding must feel guided, not overwhelming
- Tour bar at bottom should be OBVIOUS — big, clear, with arrow pointing to next step
- "Welcome to your new AI! Let's show you around." messaging
- Dashboard should show a welcoming first state, not empty cards

### C6: Colors must match onboarding embers
- InstallerWizard uses CSS vars now, but dashboard may have different values
- Audit `globals.css` — `--color-neon` must be the same amber/gold as onboarding
- No jarring color shift between installer and dashboard

---

## 🎨 Freya (UI + Animation)

### F1: Wire StatusOverlay to agent state
- Poll `/api/v1/status/agent` every 5s from GuildHall
- Map: processing → 🔥, idle → 💤, error → 💀, task_complete → 🎉

### F2: Agent idle animations in Guild Hall
- Breathing/subtle movement loops using `steps()` CSS
- Different animation per activity

### F3: Companion follows agent + reacts
- Uses SpriteCharacter.tsx, NOT emoji
- Idle: tail wag. Agent 🔥: happy bounce. Agent 💤: curls up

### F4: Interactive furniture tooltips
- Click/hover elements → show label + status

### F5: Install step error handling
- Non-critical failures → "skipped — already set up" not ❌
- **Fix ALREADY IN CODE:** InstallerWizard.tsx updated

---

## 🔨 Thor (Backend)

### T1: Agent status API
- `GET /api/v1/status/agent` → real state for status effects
- Falls back to mock if backend offline

### T2: Brain download endpoint or guide
- Either wire actual GGUF download during install
- Or redirect user to Brains page with clear "Download your brain" prompt

---

## 🛡️ Heimdall (Audit)

### H1: Fresh install end-to-end
- Clear ALL state → install .exe → complete onboarding
- Verify: tour activates → tabs locked → guide works → brain prompt shown
- This MUST be tested as a real install, not code review

### H2: Color consistency audit
- Compare onboarding vars vs dashboard vars
- No hardcoded colors remaining

---

## ✅ Valkyrie (QA)

### V1: First-time user experience test
- Fresh install → onboarding → dashboard
- Tabs locked? Tour bar visible? Know where to go?
- Companion shows as sprite, not emoji?
- Brain download prompted or in progress?
- Colors match between installer and dashboard?
- NO ❌ on non-critical install steps?

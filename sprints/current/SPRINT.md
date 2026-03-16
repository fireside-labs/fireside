# Sprint 24 — "Make It Real"

> **Goal:** Fix every broken thing from user test round 7 (2026-03-16 4:26 PM). No new features — just fix what's broken.
> **Source:** Screenshots showing checkerboard sprites, broken buttons, wrong model, Telegram nonsense

---

## 🔴 BUGS (fix or remove)

### B1: Ember/companion sprite = checkerboard (CRITICAL)
- Every screenshot shows broken PNG — checkerboard on dashboard AND Guild Hall
- Root cause: sprite PNGs don't exist at the path GuildHall.tsx / page.tsx reference
- **Fix:** Either generate real PNGs or use emoji fallback. NO CHECKERBOARD EVER.
- Test: Ember must render as visual, not broken img

### B2: Guild Hall sprites = broken mess (CRITICAL)
- Screenshot shows: grey squares, misaligned furniture, checkerboard transparency
- The tilemap sprites referenced in THEME_ELEMENTS don't exist
- **Fix:** Either replace with working sprites or strip Guild Hall down to a simple agent list until sprites are ready
- This is the "money shot" — it can't look like this

### B3: Model picker doesn't persist selection
- User selected Qwen in installer dropdown
- Summary screen still shows "Deep Thinker (35B Params)"
- `config.actualModel` not flowing to the summary display
- **Fix:** Summary page must read config.actualModel, not the default brainId label

### B4: "Add a custom skill" button does nothing
- Personality page has an Add button that's non-functional
- Either wire it up or remove it — broken buttons destroy trust
- **Fix:** Remove non-functional buttons OR implement as a text input that saves to localStorage

### B5: "Add a rule" button does nothing  
- Same as B4 — Personality page, non-functional Add button
- **Fix:** Same approach — remove or implement

### B6: Telegram setup should not exist
- There's a Telegram integration setup on the Settings/config page
- Product has a mobile app — Telegram is confusing and wrong
- **Fix:** Remove Telegram references. Replace with "Connect Your Phone" section that describes the Expo mobile app

### B7: Colors look the same
- User says "colors again look the same"
- The CSS variable unification from Sprint 17 may not have propagated, or the amber theme isn't distinct enough from default dark mode
- **Fix:** Audit and increase contrast — ember glow on active elements, brighter amber accents, more visible difference from generic dark UI

---

## 🎨 Freya

### F1: Fix companion image path (B1)
Find every reference to companion sprite and fix:
- `dashboard/app/page.tsx` — companion hero section
- `dashboard/components/GuildHall.tsx` — companion in scene
- Use emoji (🦊) as fallback in an error boundary — never show checkerboard

### F2: Guild Hall visual fix (B2)
The scene relies on sprite PNGs that don't exist. Options:
- Option A: Strip to simple card layout with agent list (safe, fast)
- Option B: Generate actual working sprites and verify they load
- **Recommendation:** Option A for now — ambitious pixel scenes can wait

### F3: Fix model persistence (B3)
In InstallerWizard.tsx summary step:
- Read `config.actualModel` for display label
- Map model ID to human name (e.g. "qwen-2.5-35b-q4" → "Qwen 2.5 35B (Q4)")

### F4: Fix or remove Personality buttons (B4, B5)
Remove "Add skill" and "Add rule" if they don't work.
Non-functional buttons = user distrust.

### F5: Replace Telegram with "Connect Phone" (B6)
Remove Telegram bot setup from config page.
Replace with mobile app connection instructions.

### F6: Model catalog (FEATURE — after bugs)
- Instead of dropdown, full-page model browser
- Cards like Brains page but with ALL available models
- Filter by: size, speed, compatibility, use case
- Categories: Fast (7-8B), Deep (14-35B), Expert (Cloud)
- This is Version 2 material but capture for backlog

---

## ✅ Valkyrie (QA)

### V1: Screenshot every page
- Dashboard: Ember renders, no checkerboard
- Guild Hall: No broken sprites  
- Personality: No non-functional buttons
- Brains: Selected model matches what was picked
- Settings: No Telegram, has "Connect Phone"

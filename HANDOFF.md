# Fireside — Clean Handoff for Fresh Agent Conversations

> **Date:** 2026-03-16
> **Purpose:** Start new agent conversations with ZERO history. This doc is the ONLY context they need.
> **Read this instead of:** any previous sprint files, gate reports, or chat history.

---

## What Is Fireside?

A desktop AI companion app built with **Tauri v2 + Next.js**. Users install an `.exe`, go through a cinematic onboarding wizard, download an AI brain (LLM), and chat with their personal AI. Think "Game Dev Story meets a local AI assistant."

**Repo:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

---

## Tech Stack

| Layer | Tech | Location |
|-------|------|----------|
| Desktop shell | Tauri v2 (Rust) | `tauri/src-tauri/` |
| Dashboard UI | Next.js + React | `dashboard/` |
| Backend API | Python FastAPI | `api/v1.py` |
| Mobile app | React Native (Expo) | `mobile/` |
| Config | `tauri.conf.json` | `tauri/src-tauri/` |

**Build commands:**
```bash
# Dashboard
cd dashboard && npm run build

# Tauri .exe
$env:NO_STRIP = "true"
cd tauri && cargo tauri build
# Output: tauri/src-tauri/target/release/bundle/nsis/Fireside_1.0.0_x64-setup.exe
```

**Clear state for fresh install test:**
```powershell
Remove-Item "$env:LOCALAPPDATA\ai.fireside.app" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.fireside" -Recurse -Force -ErrorAction SilentlyContinue
```

---

## Current Sidebar (6 tabs)

```
YOUR AI
  💬 Chat          → /           (page.tsx — main dashboard + chat)
  🧠 Personality   → /soul       (PersonalityForm.tsx, PersonalitySliders.tsx)

WORLD
  🏰 Guild Hall    → /guildhall  (GuildHall.tsx — emoji-only scene, no sprites)

SYSTEM
  🧠 Brains        → /brains     (BrainCard.tsx — 3 tier cards: Smart/Deep/Cloud)
  🏪 Store         → /store      (StoreTabs.tsx — themes, skins placeholder)
  ⚙ Settings       → /config     (SettingsForm.tsx, VoiceSettings.tsx, Connect Phone)
```

**Dead routes (exist but NOT in sidebar):** `/agents`, `/companion`, `/crucible`, `/debate`, `/landing`, `/learning`, `/marketplace`, `/nodes`, `/pipeline`, `/plugins`, `/warroom`. These can be ignored or deleted.

---

## User Flow (Current State)

1. **Launch app** → `OnboardingGate.tsx` checks `localStorage` for `fireside_onboarded`
2. **If new user** → `InstallerWizard.tsx` (9-step cinematic onboarding):
   - Step 0: Welcome screen
   - Step 1: System check (OS, RAM, GPU, VRAM) + model picker + **Continue button**
   - Step 2: Choose companion species
   - Step 3: Name your AI
   - Step 4: Review summary
   - Step 5: Installing (Python, Node, packages, config)
   - Step 6: Brain download (or "Download Later")
   - Step 7: Connection test
   - Step 8: Success → "Open Dashboard"
3. **Dashboard** → `GuidedTour.tsx` activates (polls localStorage every 500ms)
4. **Tour** → 6 steps: Dashboard → Personality → Guild Hall → Brains → Store → Settings
5. **Tour bar** → clickable "Go to X" button navigates to each page
6. **Tabs unlock cumulatively** as tour progresses (`UNLOCKED_AT_STEP` array in GuidedTour.tsx)

---

## What Works

- ✅ **Installer wizard** — cinematic, multi-step, system detection, ember particles. This is the gold standard of the app.
- ✅ **Brains page** — 3-tier card layout (Smart & Fast / Deep Thinker / Cloud Expert), shows VRAM, compatible badge. Looks good.
- ✅ **Sidebar** — 6 clean tabs with tour locking
- ✅ **Tour** — 6-step guided tour with clickable navigation buttons
- ✅ **Brain lie fixed** — `fireside_model` only set when brain actually downloads
- ✅ **Settings** — "Connect Your Phone" section (Telegram removed)
- ✅ **System detection** — GPU, VRAM, RAM via `nvidia-smi` and Tauri IPC

---

## What's Broken (FIX THESE)

### 🔴 Critical

1. **Ember companion = checkerboard image** on dashboard hero section
   - `page.tsx` renders a companion image that doesn't exist
   - Fix: use emoji fallback OR generate a real Ember PNG and put it in `dashboard/public/`

2. **"Add a custom skill" button on Personality page does nothing**
   - `PersonalityForm.tsx` or `SoulEditor.tsx` has non-functional Add buttons
   - Fix: either wire up (save to localStorage) or remove the button entirely

3. **"Add a rule" button on Personality page does nothing**
   - Same component, same issue
   - Fix: remove or implement

4. **Model selection doesn't persist to summary screen**
   - User picks Qwen in advanced dropdown, but summary (step 4) still shows "Deep Thinker (35B)"
   - `InstallerWizard.tsx` summary step reads `brainLabel` (line ~261) which uses sysInfo, not `config.actualModel`
   - Fix: summary should display the selected model name from config

### 🟡 Important

5. **Guild Hall is emoji-only** — functional but not premium. Sprites were stripped because the PNG paths were broken. Future: replace with real sprite assets when purchased/created.

6. **Dashboard colors feel "flat"** — user says it doesn't feel "premium video game" like the installer. The installer has amber glow, glass cards, particles. Dashboard should match.

7. **Chat input should be disabled when backend offline** — currently says "Download a Brain" which is good, but the chat input box may still be visible/typeable.

8. **Model catalog too small** — only 5 models in a dropdown. Future: full-page model browser with filters (size, speed, use case) like a video game item shop.

---

## Key Files to Edit

| File | What it does |
|------|-------------|
| `dashboard/app/page.tsx` | Main dashboard — hero, companion, chat, status cards |
| `dashboard/components/InstallerWizard.tsx` | 9-step cinematic installer (43KB, biggest file) |
| `dashboard/components/GuidedTour.tsx` | Tour steps, tab locking, tour overlay bar |
| `dashboard/components/Sidebar.tsx` | 6-tab sidebar with tour lock integration |
| `dashboard/components/GuildHall.tsx` | Guild Hall scene (emoji-only currently) |
| `dashboard/components/PersonalityForm.tsx` | Personality page with broken Add buttons |
| `dashboard/components/BrainCard.tsx` | Brain tier cards on /brains |
| `dashboard/app/config/page.tsx` | Settings page with Connect Phone |
| `dashboard/app/globals.css` | CSS variables, theme colors, animations |

---

## Design Rules

1. **Installer is the quality bar** — every page should feel as premium as the installer
2. **Color palette:** dark bg (`#0a0a0f`), amber accent (`#F59E0B`), glass cards with `rgba(245,158,11,0.08)` borders
3. **No broken images ever** — use emoji fallback if PNG doesn't exist
4. **No non-functional buttons** — if it doesn't work, remove it
5. **Companion = visual mascot only** — no leveling, no inventory, no care screens (see `docs/SCOPE_REDUCTION_COMPANION.md`)
6. **6 tabs only** — don't add more to the sidebar
7. **Power user features** → Settings > Advanced sub-tab

---

## Agent Roles (Fresh Conversations)

| Agent | Job | Output |
|-------|-----|--------|
| **Freya** | Fix the 4 red bugs above. Make dashboard match installer quality. | Modified `.tsx` and `.css` files |
| **Thor** | Brain status API must be honest. Connection test. | Modified `api/v1.py`, Rust backend |
| **Heimdall** | Verify fixes are VISIBLE. No "done" without describing what changed. | `audit_heimdall.md` |
| **Valkyrie** | Fresh install end-to-end test. Screenshot every page. | `review_valkyrie.md` |

---

## DO NOT

- ❌ Reference any previous sprint numbers (17-24)
- ❌ Add sprite paths that don't point to real PNG files
- ❌ Add buttons that don't do anything
- ❌ Say "done" without visible proof
- ❌ Touch `GantryOracle/` — different project
- ❌ Add new sidebar tabs
- ❌ Implement companion leveling/inventory/care

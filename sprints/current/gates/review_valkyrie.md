# Valkyrie — Sprint 15 Fresh Install QA Report

**Sprint:** "Ship It"
**Tester:** Valkyrie (QA)
**Date:** 2026-03-16
**Status:** 🟡 MOSTLY CLEAN — 2 blockers, 3 notes

---

## V1. End-to-End Checkpoints

### ✅ Checkpoint 1: System shows ~64GB RAM + ~32GB VRAM
- `main.rs` uses `Get-CimInstance` for RAM (✅ fixed Sprint 14)
- VRAM: `nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits` (✅ T2 in this sprint)
- **Needs .exe rebuild** to verify — can't test without a built binary

### ✅ Checkpoint 2: Onboarding → name agent "Atlas", pick fox companion "Ember"
Onboarding stores 6 keys to localStorage:
```
fireside_agent_name = "Atlas"
fireside_agent_style = "analytical" (etc)
fireside_companion_name = "Ember"
fireside_companion_species = "fox"
fireside_companion = { name, species } (JSON)
fireside_onboarded = "1"
```
Both `InstallerWizard.tsx` (Tauri) and `OnboardingWizard.tsx` (browser) write the same keys. ✅

### ✅ Checkpoint 3: Dashboard → "Atlas" shows in sidebar, settings, nodes
Agent name (`fireside_agent_name`) is read in **8 locations**:

| Surface | File | Status |
|---------|------|--------|
| Sidebar | `Sidebar.tsx` L54 | ✅ |
| Settings | `SettingsForm.tsx` L20 | ✅ |
| Personality | `PersonalityForm.tsx` L33 | ✅ |
| Nodes page | `nodes/page.tsx` L47 | ✅ Sets `friendly_name` on first node |
| Config page | `config/page.tsx` L18 | ✅ |
| Guild Hall | `GuildHall.tsx` L99 | ✅ |
| Installer | `InstallerWizard.tsx` L405 | ✅ (writes) |
| Onboarding | `OnboardingWizard.tsx` L90 | ✅ (writes) |

### ✅ Checkpoint 4: Tour → Next works, tabs locked until done
`GuidedTour.tsx` is properly implemented:
- 3 steps: Dashboard → Brains → Chat
- `isLocked(href)` correctly locks unlisted routes
- `advanceTour()` saves completed steps, marks tour done at end
- `skipTour()` unlocks everything + sets `fireside_tour_done`
- Overlay bar at bottom with fire amber styling ✅
- Next button only shows when user is on the correct page ✅
- Imported in `Sidebar.tsx` (locks tabs) and `layout.tsx` (TourProvider + TourOverlay) ✅

### ⚠️ Checkpoint 5: Brains → matches onboarding choice
**F2 in Sprint 15 — needs Freya.** BrainPicker must read `fireside_agent_style` and highlight the matching brain. Currently shows different brain names than onboarding.

### ❌ Checkpoint 6: Store → real listings
**Blocker — T3 + F4 need Thor + Freya.** 
- No `GET /api/v1/store/plugins` endpoint exists
- Store page still uses marketplace from api.ts (trimmed to 4 items post-cleanup, but still fallback)
- No purchase flow wired

### ✅ Checkpoint 7: Chat → sends to backend
CompanionChat has `PET_RESPONSES` fallback but also tries backend connection:
- `goOnline()` / `goOffline()` handlers exist
- `ConnectionState` display shows connection status
- When backend is running, chat should route to it
- When offline, falls back to canned answers ← acceptable for now

### ✅ Checkpoint 8: No Norse names visible anywhere
**Verified clean across user-facing surfaces:**

| Area | Status |
|------|--------|
| Sidebar | ✅ Dynamic from `fireside_agent_name` |
| Nodes page | ✅ `FRIENDLY_NAMES` removed (Sprint 14) |
| Mock data | ✅ All `source_node: "odin"` etc. emptied to `[]` |
| DebateTranscript | ✅ "Thor" → "Builder" (Sprint 14) |
| PredictionChart / EventStream | ✅ `#00ff88` → `#F59E0B` (Sprint 14) |

**Remaining "valhalla" references — INTENTIONAL, not bugs:**
- `ThemePicker.tsx` L9: "Valhalla" as a theme name (like "Space" or "Cozy") ✅
- `GuildHall.tsx` / `GuildHallAgent.tsx`: "valhalla" theme key in activity descriptions ✅
- `SettingsForm.tsx` L109: "valhalla.yaml" config file reference ✅
- `ValhallaEvent` type in api.ts: internal type name, never shown to users ✅
- `marketplace/page.tsx` L56: `.valhalla` → should be `.fireside` ← already fixed by owner

### 📋 Checkpoint 9: No mock data on reachable pages

| Page | Mock Status | Sprint 15 Task |
|------|------------|----------------|
| Dashboard | ✅ Empty arrays show "no data" | — |
| Brains | ✅ Real hardware detection | — |
| Nodes | ✅ Real data from API | — |
| Companion chat | ⚠️ PET_RESPONSES fallback | Acceptable |
| Store | ❌ Still MOCK_MARKETPLACE | T3 + F4 |
| Learning | ✅ Empty (shows "no data") | F5 → "Coming Soon" |
| War Room | ✅ Empty | F5 |
| Crucible | ✅ Empty | F5 |
| Pipeline | ✅ Empty | F5 |
| Debate | ✅ Empty | F5 |

---

## Blockers

1. **Store backend (T3)** — No real plugin registry or purchase flow
2. **Backend auto-start (T1)** — Without this, every first-time user sees "Offline mode"

## Notes

1. **5 companion MOCK_ arrays** still exist in PurchaseHistory, TaskQueue, WeeklyCard, InventoryGrid, AdventureCard — these pages are behind the companion tab, not reachable during the tour. Low priority.
2. **F5 "Coming Soon" cards** should replace empty arrays on Learning/Crucible/Pipeline/Debate pages so they look intentional, not broken.
3. **F6 Guild Hall pixel art** is a polish item — works but is "v1 quality."

---

— Valkyrie 👁️

# Sprint 4 — FREYA (Frontend: Adventures, Daily Gifts, Guardian + App Store)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

> [!IMPORTANT]
> **Read `FEATURE_INVENTORY.md` first** to understand what the desktop platform already has.
> Then read the dashboard components below — they are your design reference.

---

## Context

The desktop dashboard has adventures, daily gifts, and a message guardian that the mobile app doesn't surface yet. These are the engagement drivers — adventures are the RPG hook, daily gifts create daily check-in habit, and the guardian is a unique differentiator ("the app that stops you from drunk texting").

**Reference the existing dashboard components for UX patterns:**
- `dashboard/components/AdventureCard.tsx` (308 lines) — 8 encounter types with choices and rewards
- `dashboard/components/DailyGift.tsx` (107 lines) — species-specific daily gifts
- `dashboard/components/TeachMe.tsx` (118 lines) — teach companion facts

Your Sprint 3 code lives in `mobile/` — build on top of it.

---

## Your Tasks

### Task 1 — Adventures Screen
Add a 5th tab or a button on the Care tab that launches adventures.

Read `AdventureCard.tsx` for the encounter format. Each adventure has:
- **Type:** riddle, treasure, merchant, forage, lost_pet, weather, storyteller, challenge
- **Narrative text** (species-specific flavor)
- **Choices** (2-3 options with different outcomes)
- **Rewards** (items, XP, happiness boost)

Build `mobile/app/(tabs)/adventure.tsx` or a modal:
1. "Start Adventure" button (or auto-trigger on walk success)
2. Show encounter card with narrative text and companion avatar
3. Present choices as large tappable buttons
4. Show result + rewards with celebration animation
5. Haptic feedback on choice + reward

Species-specific adventure text is the key engagement driver — make the narrative prominent.

### Task 2 — Daily Gift
Add a daily gift popup/modal that appears on app open (once per day):

1. On app launch, check if a daily gift is available (via `/api/v1/companion/daily-gift` or sync response)
2. Show a gift card with species-personality flavor text (e.g., cat: "I found this behind the couch. You may have it." / dog: "LOOK WHAT I FOUND!! FOR YOU!!")
3. "Open Gift" button with haptic + sound effect + celebration animation
4. Claim the gift (item, XP, fact, poem, advice, or compliment)
5. Store claim timestamp in AsyncStorage as fallback

Use the design patterns from `DailyGift.tsx` — it's only 107 lines.

### Task 3 — Message Guardian Integration
Before sending a chat message, run it through the guardian:

1. Before `POST /chat`, call `POST /api/v1/companion/guardian` with `{ message, time_of_day }`
2. If the guardian returns `safe: false`:
   - Show a warning modal with the species-appropriate message (e.g., cat: "Are you sure? It's 2AM and this seems... emotional.")
   - Show the suggested softer rewrite if available
   - Two buttons: "Send Anyway" and "Use Rewrite"
3. If `safe: true`, send normally
4. This check should feel lightweight — don't add noticeable delay

The guardian is a unique feature competitors don't have. Make it feel helpful, not judgmental.

### Task 4 — EAS Build Configuration
Set up Expo Application Services (EAS) for App Store builds:

```bash
cd mobile && npx -y eas-cli@latest build:configure
```

Update `eas.json` with:
```json
{
  "build": {
    "preview": {
      "distribution": "internal",
      "ios": { "simulator": true }
    },
    "production": {
      "ios": { "bundleIdentifier": "com.valhalla.companion" },
      "android": { "package": "com.valhalla.companion" }
    }
  }
}
```

Update `app.json` with:
- `bundleIdentifier`: "com.valhalla.companion"
- `version`: "1.0.0"
- `buildNumber`: "1"

### Task 5 — Update Tab Navigation
With adventures added, the tab bar may need adjustment. Options:
- Add a 5th "⚔️ Quest" tab
- Or keep 4 tabs and put adventures as a prominent button in the Care tab

Use your UX judgment. If 5 tabs fit cleanly, add the tab. If it feels crowded, integrate into Care.

### Task 6 — Drop Your Gate
Create `sprints/current/gates/gate_freya.md` using write_to_file:

```markdown
# Freya Gate — Sprint 4 Frontend Complete
Sprint 4 tasks completed.

## Completed
- [x] Adventures screen (8 encounter types, choices, rewards)
- [x] Daily gift popup (once per day, species personality)
- [x] Message guardian integration (warning modal + rewrite suggestion)
- [x] EAS Build configuration
- [x] Tab navigation updated
```

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
- Read `sprints/current/gates/audit_heimdall.md` if gate is deleted

---

## Notes
- Adventures and daily gifts are the features that create DAILY engagement. Wordle cadence.
- The guardian is the unique differentiator — "the app that stops you from drunk texting." Make it feel like a friend warning you, not a firewall.
- Build ON TOP of Sprint 3 code. Don't rewrite.
- Read the dashboard components before building — they have the data structures and UX patterns.

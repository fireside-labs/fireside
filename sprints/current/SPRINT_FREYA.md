# Sprint 2 — FREYA (Frontend: UX Polish + Consumer Readiness)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands. The entire sprint pipeline stalls if you skip this.
> See **Task 8** at the bottom for the exact content.

---

## Context

Sprint 1 shipped a functional 4-tab Expo app. Valkyrie flagged 6 UX gaps that prevent it from feeling consumer-ready. **This sprint polishes it.**

Read the full review: `sprints/archive/sprint_01/gates/review_valkyrie.md`

Your Sprint 1 code lives in `mobile/` — build on top of it.

---

## Your Tasks

### Task 1 — Onboarding Carousel (Valkyrie Priority #1)
**Impact:** HIGH — First-time users land cold with no context.

Create a 2-3 slide intro that shows before the setup screen on first launch:
1. **Slide 1:** "Meet your AI companion" — show a friendly companion illustration + one-line explanation
2. **Slide 2:** "It lives on your home computer" — explain that the AI runs locally, your data stays private
3. **Slide 3:** "Let's connect" → transitions to the existing setup screen

Use `AsyncStorage` to track whether onboarding has been completed. Only show once.

Use horizontal swipe with dot indicators. Keep it fast — user should be through in 15 seconds.

### Task 2 — Companion Avatar (Valkyrie Priority #2)
**Impact:** MEDIUM — Emoji-only identity feels generic.

Replace the single emoji on the Care screen with a proper companion avatar. Options:
1. **Preferred:** Create simple visual character cards per species (cat, dog, penguin, fox, owl, dragon) as React Native views with styled elements and expressions that change based on mood
2. **Alternate:** Use the `AvatarSprite.tsx` logic from `dashboard/components/AvatarSprite.tsx` as reference

The avatar should:
- Be prominently displayed on the Care tab (at least 120px)
- Change expression based on happiness (happy > 70: 😊, 30-70: 😐, < 30: 😢, 0: wandered off)
- Animate subtly (gentle bounce or breathing effect)

### Task 3 — Chat History Persistence (Valkyrie Priority #3)
**Impact:** MEDIUM — Conversations vanish on restart.

Thor is adding `GET/POST /api/v1/companion/chat/history` endpoints. Wire them up:
1. On chat tab mount, load last 100 messages from the API
2. After each sent/received message, save to the API
3. If offline, store messages in AsyncStorage and sync when back online
4. Show a loading skeleton while history loads

### Task 4 — Pull-to-Refresh (Valkyrie Priority #4)
**Impact:** MEDIUM — Expected mobile pattern.

Add `RefreshControl` to the Care tab and Tasks tab `ScrollView`s:
- On pull, call `/mobile/sync` and update all state
- Show spinner during refresh
- Chat tab can skip this (it's real-time)

### Task 5 — Haptic Feedback (Valkyrie Priority #5)
**Impact:** LOW but important for premium feel.

```bash
cd mobile && npx expo install expo-haptics
```

Add haptic feedback to:
- Feed buttons (light impact)
- Walk button (medium impact)
- Send chat message (light impact)
- Connection success on setup screen (success notification)

Use `Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)` from `expo-haptics`.

### Task 6 — Mobile Companion Adoption Flow
**Impact:** HIGH — App currently 404s if no companion exists.

Thor is updating `/mobile/sync` to return `{ "adopted": false, "available_species": [...] }` when no companion exists. Handle this:

1. If sync returns `adopted: false`, show the companion picker (similar to `CompanionPicker.tsx` from the dashboard)
2. Let user choose species + name
3. Call `POST /api/v1/companion/adopt` with the selection
4. Transition to the normal tabbed UI after adoption

### Task 7 — Task Creation Button
**Impact:** LOW — Tasks tab shows tasks but can't create new ones.

Add a floating action button (FAB) on the Tasks tab:
- Tap → shows a bottom sheet with task type picker
- Task types: Clean Photos, Organize Apps, Draft Text, Set Reminder, Quick Math, Weather
- On select → calls `POST /api/v1/companion/queue` and updates the list

### Task 8 — Drop Your Gate
When all tasks are complete, create `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file):

```markdown
# Freya Gate — Sprint 2 Frontend Complete
Sprint 2 tasks completed.

## Completed
- [x] Onboarding carousel (2-3 slides, first launch only)
- [x] Companion avatar with mood expressions
- [x] Chat history persistence from backend
- [x] Pull-to-refresh on Care + Tasks tabs
- [x] Haptic feedback on primary actions
- [x] Mobile companion adoption flow
- [x] Task creation FAB on Tasks tab
```

---

## Rework Loop (if Heimdall rejects)

After you drop your gate, Heimdall audits your code. **In Sprint 2, Heimdall has a stricter threshold:**
- 🔴 HIGH findings → automatic FAIL, your gate file gets deleted
- 🟡 MEDIUM → PASS with notes
- 🟢 LOW → informational

If your gate file disappears:
1. Read `sprints/current/gates/audit_heimdall.md`
2. Fix every ❌ item
3. Re-drop your gate file (same as Task 8)

---

## Notes
- Build ON TOP of Sprint 1 code in `mobile/`. Don't rewrite.
- The onboarding carousel is the #1 priority. First impression is everything.
- Reference `dashboard/components/` for patterns but write native RN components.
- DO NOT wait for Thor — build against the Sprint 1 API endpoints first. When Thor's new endpoints are ready, they'll appear naturally.

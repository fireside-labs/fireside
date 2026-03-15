# Sprint 5 — FREYA (Frontend: Mode Split + Translation + Platform Bridge)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

> [!IMPORTANT]
> **Read `FEATURE_INVENTORY.md`** to understand the full platform. Read Valkyrie's Sprint 4 review
> at `sprints/archive/sprint_04/gates/review_valkyrie.md` — it defines the vision for this sprint.

---

## Context

Valkyrie's key insight: *"Adults and executives who just want the utility can toggle this off."*

The app currently serves one persona (Tamagotchi lover). This sprint adds a second persona (privacy-first utility user) through a **mode toggle**, and surfaces the platform depth through translation, morning briefings, and a "What's Happening at Home" card.

Reference dashboard components:
- `dashboard/components/TeachMe.tsx` (118 lines)
- `dashboard/components/MorningBriefing.tsx`
- `plugins/companion/nllb.py` — translation API reference

---

## Your Tasks

### Task 1 — Companion Mode Toggle (Valkyrie Priority #1)
Add a settings screen or toggle on the Care tab:

**🐾 Pet Mode** (default):
- All tabs visible: Chat, Care, Bag, Quest, Tasks
- Gamification active: feeding, walking, adventures, daily gifts, XP, levels
- Companion speaks in character (mood prefixes, species personality)

**🔧 Tool Mode:**
- Simplified tabs: Chat, Tools, Tasks
- Gamification hidden: no feeding, no walking, no quests, no daily gifts
- Companion still has personality but skips game mechanics
- "Tools" tab replaces Care+Bag+Quest with: Guardian settings, Translation, TeachMe
- Happiness/XP bars hidden
- Push notifications change: no "feed me" alerts, only task completions and guardian check-ins

Store mode in AsyncStorage. The toggle should be:
- A gear icon on the Care tab → Settings screen with mode picker
- OR a profile card at the top of Care tab with a clean toggle

The companion's personality STAYS in both modes — only the game mechanics change.

### Task 2 — Translation UI
Add a Translation screen (accessible in Tool mode's "Tools" tab, and optionally in Pet mode's chat screen as a button):

1. **Text input** field for text to translate
2. **Source language** picker (auto-detect option + manual selection)
3. **Target language** picker (searchable — there are 200 languages)
4. **Translate button** → calls `POST /api/v1/companion/translate`
5. **Result display** with copy-to-clipboard button
6. Show confidence score from the API response

Haptic feedback on translate + copy.

The language picker needs to be searchable (200 languages is too many to scroll). Use a text filter at the top.

### Task 3 — Morning Briefing
Add a morning briefing card that appears on app open (once per day, mornings only):

1. On app launch between 6AM-11AM, check if a morning briefing is available
2. Show a card at the top of the Care/Tools tab:
   - Companion avatar + "Good morning! Here's what happened overnight..."
   - Summary of platform activity (from `/mobile/sync` → `platform` data)
   - Any completed tasks
   - Any companion events (leveled up, learned something, etc.)
3. Card is dismissible with a gentle swipe or tap
4. Persist dismissal in AsyncStorage for today

### Task 4 — TeachMe
Add a TeachMe section (in Tool mode's Tools tab + optionally in Pet mode's Chat tab):

1. "Teach me something" text input
2. Submit → `POST /api/v1/companion/teach` with `{ fact: string }`
3. Confirmation with species-specific personality response:
   - Cat: "I already knew that, but I'll pretend to be impressed."
   - Dog: "WOW!! That's the BEST fact I've EVER heard!!"
   - Dragon: "Knowledge is power. I shall remember this."
4. Show count of learned facts: "Your companion knows 23 facts"

Reference `dashboard/components/TeachMe.tsx` for the pattern.

### Task 5 — "What's Happening at Home" Card
Add a card to the Care/Tools tab that shows the home PC's activity:

Thor is adding a `platform` section to `/mobile/sync`. Use it to build a compact card:

```
🏠 Your Home PC
├── ⏱️ Uptime: 42.5 hours
├── 🧠 Models loaded: qwen-14b, whisper-large
├── 💭 Memories: 247 stored
├── 🔮 Last prediction: Weather confidence 87%
├── 🌐 Mesh nodes: 2
└── 🌙 Last dream cycle: 4:30 AM
```

If home PC is offline, show: "Your home PC is offline. Your companion is running on cached data."

This creates the "bridge to desktop" that Valkyrie identified as missing.

### Task 6 — Proactive Guardian
On chat tab open, call `GET /api/v1/companion/guardian/check-in`:

If `proactive_warning: true`:
1. Show a gentle notification bar at the top of chat: "It's late. Want me to hold messages until morning?"
2. Two buttons: "Hold Messages" / "I'm Fine"
3. If "Hold Messages": disable the send button, show a countdown to 7AM, queued messages send in the morning
4. Subtle animation — don't be alarming, be caring

### Task 7 — Drop Your Gate
Create `sprints/current/gates/gate_freya.md` using write_to_file:

```markdown
# Freya Gate — Sprint 5 Frontend Complete
Sprint 5 tasks completed.

## Completed
- [x] Companion mode toggle (Pet ↔ Tool)
- [x] Translation UI (200 languages, searchable picker)
- [x] Morning briefing card (6-11AM, dismissible)
- [x] TeachMe with species personality responses
- [x] "What's Happening at Home" platform card
- [x] Proactive guardian (2AM check-in)
```

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
- Read `sprints/current/gates/audit_heimdall.md` if gate is deleted

---

## Notes
- **The mode toggle is the #1 priority.** It unlocks the entire Tool mode persona.
- Translation, TeachMe, morning briefing, and the platform card all live in Tool mode's "Tools" tab.
- In Pet mode, these features should still be accessible (via the Chat tab or a secondary menu) — just not prominent.
- The "What's Happening at Home" card is crucial for Valkyrie's "bridge to desktop" requirement.
- Build ON TOP of Sprint 4 code. Don't rewrite.

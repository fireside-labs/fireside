# Agent Profile UX Review

> **Review question:** Do the RPG elements enhance the product for normal users, or are they gamer gimmicks that confuse non-technical people?

---

## Overall Verdict: ✅ KEEP — With Adjustments

The RPG layer is the right call. Here's why: **Valhalla agents actually do get better over time.** XP, levels, and achievements aren't fake gamification — they visualize real progress (tasks completed, knowledge accumulated, crucible survival). The question is whether normal users understand that.

---

## 1. Stats — Are They Meaningful to a Non-Gamer?

| Stat | Current Label | Clear to Non-Gamer? | Recommendation |
|---|---|---|---|
| `tasks_completed` | "Tasks Completed" | ✅ Yes | Keep |
| `knowledge_count` | "Knowledge Count" | ⚠️ Vague | → "Things It Knows" (matches Learning page) |
| `accuracy` | "Accuracy" | ⚠️ Accuracy of what? | → "How Often It's Right" with percentage |
| `crucible_survival` | "Crucible Survival" | ❌ Jargon | → "Knowledge Check Score" |
| `streak` | "Streak" | ✅ Universal | Keep — everyone knows streaks from Duolingo/Snapchat |
| `skills` | Star ratings ★★★★☆ | ✅ Universal | Keep — intuitive at a glance |
| `debates_won` | "Debates Won" | ⚠️ Debates with whom? | → "Arguments Won" or add "(against itself)" tooltip |

**Key insight:** Stats are good, but they need one-line explanations underneath. "Knowledge Check Score: 94%" means nothing without "How much of what it learned is actually reliable."

### Suggested stat card format:
```
┌─────────────────────────────┐
│  📋 47 Tasks Completed      │
│  Things your AI has done    │
├─────────────────────────────┤
│  🧠 247 Things It Knows     │
│  Facts learned from work    │
├─────────────────────────────┤
│  ✅ 94% Reliable            │
│  How accurate its knowledge │
├─────────────────────────────┤
│  🔥 12 Day Streak           │
│  Days in a row without fail │
└─────────────────────────────┘
```

---

## 2. Personality Sliders — Do They Make Sense?

The opposing-pair slider concept is strong:

```
Creative  ○───○───○───●───○  Precise
```

**What works:**
- The pairs are intuitive — people understand "more creative = less precise"
- 5 notches is simple (not a confusing 0-100 range)
- Slider values map to real system prompt modifiers — this is real, not decoration

**What needs work:**

| Pair | Clear? | Issue | Fix |
|---|---|---|---|
| Creative ↔ Precise | ✅ | — | — |
| Verbose ↔ Concise | ⚠️ | "Verbose" is a vocabulary word | → "Detailed ↔ Brief" |
| Bold ↔ Cautious | ✅ | — | — |
| Warm ↔ Formal | ✅ | — | — |

**Add preview text.** As the user drags a slider, show a one-line example of how the AI would respond at that setting:

```
Creative ●───○───○───○───○  Precise
"I'll try completely new approaches — might surprise you!"

Creative ○───○───○───○───● Precise
"I'll follow proven patterns and double-check everything."
```

This makes the abstract slider concrete.

---

## 3. Achievements — Motivating or Noise?

**Thor's achievement system has 18 badges across 5 categories.** That's a lot. Here's the assessment:

### Motivating ✅
| Badge | Why It Works |
|---|---|
| 🔥 On a Roll (3 streak) | Quick win — people love early rewards |
| ⚡ Dedicated (5 streak) | Attainable, feels earned |
| 🏆 Unstoppable (10 streak) | Real accomplishment |
| 📚 Scholar (50 knowledge) | Maps to real AI learning |
| ⭐ Apprentice (level 5) | Classic RPG dopamine hit |

### Noise ⚠️
| Badge | Why It Fails | Fix |
|---|---|---|
| 💯 Centurion (100 tasks) | Takes months — too far away | Keep but don't show until 50+ tasks |
| 🏅 Grand Master (level 50) | Requires 25,000 XP — unrealistic early | Keep as aspiration but hide until level 30+ |
| 🎭 Master Debater (10 debates) | Name is... unfortunate | Rename to "Persuader" or "Philosopher" |
| 🔨 Forged in Fire (100% crucible) | Users don't control crucible | Add tooltip "Your AI passed every knowledge test" |

### Recommendation
- Show max 3 "next up" badges (closest to unlock) — `get_next_achievements` already does this ✅
- Hide far-away badges entirely until the user is halfway there
- Show earned badges prominently on profile — these are trophies
- **Achievement toasts are crucial.** Freya's animated slide-in toast is the moment of delight

---

## 4. Does Leveling Feel Rewarding?

**XP system review:**

| Source | XP | Frequency | Feels Fair? |
|---|---|---|---|
| Task completed | +100 | Multiple/day | ✅ Core source |
| Crucible survived | +50 | Nightly | ✅ Good |
| Debate won | +75 | When debates run | ✅ Good |
| Streak bonus | +10/streak | Cumulative | ✅ Clever — rewards consistency |
| File read | +5 | Frequent | ⚠️ Too small to notice |
| Chat response | +10 | Very frequent | ⚠️ Could be farmed by spamming chat |

**Level curve:**
- 500 XP per level = ~5 tasks to level up
- A busy agent levels up every 1-2 days
- That's a good pace — fast enough to notice, slow enough to care

**Concerns:**
1. XP for chat responses (+10) could be farmed. **Fix:** Cap at 20 chat XP per day.
2. XP for file reads (+5) is too small to show in UI. **Fix:** Don't show individual +5 toasts, just aggregate.
3. Level display should show progress bar, not just number. "Level 14 ████████░░ 340/500 XP" — Thor's `get_level_info` returns `progress_pct` which is perfect for this.

---

## 5. Guild Hall — Keep, Iterate, or Cut?

**Verdict: ✅ KEEP — It's the screenshot feature.**

The Guild Hall is what people will screenshot and share on Twitter. "Look, my AI agents are studying at their desks." It's the visual proof that your AI mesh is alive and working.

**What makes it work:**
- Activity-driven positioning → agents move based on what they're doing (not random)
- 5 swappable themes → personality for the whole app
- Click → tooltip → double-click → profile page = progressive disclosure
- Pure SVG/CSS = zero GPU cost

**Concerns:**
1. **Small screens:** On a 13" laptop, a 2D scene with 4 agents could be cramped. **Fix:** Make the scene scrollable horizontally, or offer a compact "list mode" toggle.
2. **Value over list view:** The guild hall adds value ONLY if animations are smooth and positioning is clear. If agents overlap or animations jank, it's worse than a list. **Fix:** Strict z-index ordering and collision avoidance in positioning.
3. **Real-time updates:** The spec says "listens to event bus WebSocket." If events are sparse (no tasks running), the scene is static. **Fix:** Add subtle idle animations (breathing, blinking, sipping drink) so it always feels alive.
4. **Theme consistency:** 5 themes is a lot to maintain. **Fix:** Launch with 2 (Valhalla + Office), add others as Store items.

**Scene readability test:**
At a glance, can you tell who's doing what?
- ✅ If agents are spaced out with icons/labels above
- ❌ If agents are clustered without identification
- **Requirement:** Agent name + mini status ("Building...") must be visible without hovering

---

## 6. Desktop Installer UX Test

> **Status: Spec only — Tauri build not yet runnable from source review.**

### Test Plan

| # | Step | Expected | Pass? | Notes |
|---|---|---|---|---|
| 1 | Download `Valhalla.app` | DMG or direct .app | ⬜ | — |
| 2 | Double-click to open | macOS gatekeeper warning, then app opens | ⬜ | Need code signing cert for "identified developer" |
| 3 | First launch | Onboarding wizard starts, backend starts automatically | ⬜ | Tauri starts backend on port 8337 |
| 4 | Install a brain | Same flow as web dashboard | ⬜ | — |
| 5 | Chat works | Messages route through brain | ⬜ | — |
| 6 | Close app | Backend stops cleanly | ⬜ | Tauri should send SIGTERM |
| 7 | Reopen app | State preserved (name, brain, personality) | ⬜ | localStorage + valhalla.yaml on disk |
| 8 | Drag window | Native window chrome, smooth | ⬜ | Tauri v2 uses system webview |
| 9 | Uninstall | Drag to trash, no orphaned files | ⬜ | Need to clean `~/.valhalla` and launch agent |
| 10 | Menu bar | File/Edit/Window menus work | ⬜ | Tauri default menu |

### Security Observations (from capabilities config)

| Check | Status | Notes |
|---|---|---|
| CSP restricts to localhost | ✅ | `connect-src: 'self' http://127.0.0.1:8337 ws://127.0.0.1:8337` |
| No remote code execution | ✅ | No `unsafe-eval` in CSP |
| Shell execution denied | ✅ | `shell:allow-execute` in denied list |
| Filesystem access denied | ✅ | All `fs:*` in denied list |
| HTTP fetch denied | ✅ | `http:allow-fetch` in denied list |
| Auto-update signed | ✅ | ed25519 verification, reject unsigned + downgrade |
| Prototype pollution blocked | ✅ | `freeze_prototype: true` |

Heimdall's security config is tight. The webview can't read files, can't execute commands, can't make external HTTP requests. Everything goes through the local API.

---

## Summary of Recommendations

### Must-fix before ship
1. Rename "Crucible Survival" → "Knowledge Check Score"
2. Rename "Verbose ↔ Concise" → "Detailed ↔ Brief"
3. Rename "Master Debater" → "Philosopher" or "Persuader"
4. Cap chat XP at 20/day to prevent farming

### Should-fix
5. Add one-line descriptions under each stat
6. Add preview text to personality sliders
7. Hide far-away achievements until user is halfway there
8. Guild Hall: add name + mini-status above each agent sprite

### Nice-to-have
9. Compact list mode toggle for Guild Hall on small screens
10. Idle animations for Guild Hall agents
11. Launch with 2 themes (Valhalla + Office), sell rest in Store

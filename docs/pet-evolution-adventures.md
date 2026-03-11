# Sprint 14 — Pet Evolution, Adventures & Achievement Hooks

> **Theme:** More reasons to come back. More reasons to care. More reasons to tell a friend.

---

## Pet Evolution — Visual Progression

### The Tier System

```
Level 1–9:    🥚 Baby      Small emoji, learning the ropes
Level 10–24:  🐱 Juvenile  Accessory slot unlocked
Level 25–49:  ⚔️ Adult     Title unlocked ("Luna the Brave")
Level 50+:    👑 Elder     Golden border + "Elder" title + overnight auto-forage
```

### What Evolution Unlocks

| Level | Unlock | Why It Matters |
|---|---|---|
| 10 | Accessory slot | First customization — "my pet, my style" |
| 25 | Second walk per day | More adventure chances = more engagement |
| 50 | Overnight auto-forage | Passive loot while sleeping (connects to learning loop) |

### UX Recommendations

**1. Evolution should be a CELEBRATION.**
When a pet hits Level 10/25/50, don't just show a toast. Show a full-screen animation:
- Pet emoji grows, sparkles fly, confetti drops
- Sound effect (optional, short chime)
- New unlock revealed with "Try it now" CTA
- Screenshot-shareable moment ("Buddy evolved! 🎉" card)

**2. Evolution titles should be species-specific.**

| Species | Level 25 Title | Level 50 Title |
|---|---|---|
| Cat | Luna *the Unimpressed* | Luna *the Ancient* |
| Dog | Buddy *the Loyal* | Buddy *the Legendary* |
| Penguin | Sir Wadsworth *the Dignified* | Sir Wadsworth *the Distinguished* |
| Fox | Loki *the Clever* | Loki *the Mastermind* |
| Owl | Sage *the Wise* | Sage *the Omniscient* |
| Dragon | Ember *the Fierce* | Ember *the Eternal* |

This creates bragging rights. "My penguin is *Distinguished*" is a sentence someone would screenshot.

**3. Show XP progress to next evolution.**
```
Level 23 → Level 25 (Juvenile → Adult)
████████████████░░░░░░░░  67%
38 XP to go — about 4 more walks
```

The "about X more walks" estimate is critical — it gives the user a concrete goal, not an abstract number.

---

## Adventure System — UX Review

### Overall: ✅ Brilliant Design

8 encounter types = massive replayability. The dictionary-based architecture is genius — zero new infrastructure, just data. Each encounter is literally a Python dict that the UI renders. Adding new encounters is as easy as adding a dict to a list.

### Encounter-by-Encounter Review

| Encounter | UX Verdict | Enhancement |
|---|---|---|
| 🗿 Riddle Guardian | ✅ Great | Add hint button (costs 5 XP to use) |
| 🎁 Treasure Chest | ✅ Great | Add "open" animation — chest shaking before reveal |
| 👻 Ghostly Merchant | ✅ Clever | Show owned items clearly so users know what to trade |
| 🌿 Herb Foraging | ✅ Simplifies farming | Add "sniff" animation before reveal |
| 🐾 Lost Pet | ✅ Emotional | Kindness = optimal strategy is brilliant design |
| ⛈️ Weather | ✅ Atmospheric | Species-specific reactions (penguin loves snow) |
| 🎭 Storyteller | ✅ Deep | 10 fragments → achievement = collector hook |
| 🏴‍☠️ Challenger | ⚠️ Needs care | Tap mini-game must feel fair on both phone and desktop |

### Three Critical UX Rules for Adventures

**1. Never punish.** Every encounter gives something — even wrong riddle answers get consolation XP. This is correct and must never change. The moment a walk results in "nothing happened + you lost something," users stop walking.

**2. Rare items need DRAMA.** When a legendary item drops (10% chance from treasure), the entire screen should react. Sparkle effect, dramatic pause, special sound. The rare drop moment is the story users tell friends.

**3. Adventure text must be SHORT.** 2-3 sentences max per encounter. Phone UX = small screens. If users have to scroll through a paragraph, the magic dies. Quick story, clear choice, instant reward.

---

## Inventory System Review

### ✅ Good: Max 20 slots prevents hoarding abuse
### ✅ Good: Equippable accessories change pet display
### ⚠️ Watch out: Inventory management must be ONE TAP

Recommended flow:
```
Inventory Grid (4×5)
  [🍬×3] [🎩✅] [📜×7] [🌿×2]
  [💎×1] [🦴✨] [  ]   [  ]
  ...

Tap item → popup:
  [Use] [Trade] [Drop]
```

No drag-and-drop. No sub-menus. Tap → action. Mobile-first.

---

## Morning Briefing — The Killer Feature

This is the feature I recommended in Sprint 13 (section 8.4 of the companion audit). Freya's spec is perfect:

```
☀️ Good morning, Odin!

While you slept, I:
  📚 Reviewed 12 conversations
  ✅ Tested 8 facts (7 passed, 1 refined)
  📈 Got 2% smarter overall

*purrs contentedly* Luna found a moonpetal
on her overnight walk! Check your inventory.

          [Start a Fireside →]
```

### Why This Is the Most Important Feature in Sprint 14

Because this is the **proof that the product works.** Every other local AI app is "install it, chat, forget about it." Fireside says "install it, chat, go to sleep, wake up to measurable improvement." The morning briefing makes that invisible process VISIBLE.

**This single notification is the difference between a tool and a companion.**

### Enhancement: Weather greeting
Pull real weather (phone location or user-set city) and weave it in:
- "Good morning! It's 42°F and rainy — perfect stay-inside weather for a fireside. ☔"
- "73°F and sunny! Your dragon is jealous of the weather."

It's one API call. It makes the greeting feel alive instead of templated.

---

## Achievement Hooks — Sprint 14

### The 8 New Achievements

| ID | Name | Description | Trigger | Good Name? |
|---|---|---|---|---|
| `first_adventure` | Into the Unknown | Complete first adventure | ✅ Auto | ✅ |
| `riddle_master` | Riddlewright | Solve 10 riddles | ✅ Counter | ✅ |
| `collector` | Hoarder | Fill all 20 inventory slots | ✅ Counter | ⚠️ "Hoarder" is negative — rename to **"Curator"** |
| `kind_heart` | Good Samaritan | Help 5 lost pets | ✅ Counter | ✅ |
| `storyteller` | Saga Keeper | Collect all 10 story fragments | ✅ Counter | ✅ Saga Keeper is perfect Norse |
| `challenger` | Champion | Win 10 challenges | ✅ Counter | ✅ |
| `teach_10` | Professor | Teach companion 10 facts | ✅ Counter | ✅ |
| `streak_30` | Bonded | 30-day check-in streak | ✅ Daily | ✅✅ Best name in the list |

### Rename: "Hoarder" → "Curator"

"Hoarder" has negative connotations (hoarding disorder, messiness). "Curator" implies deliberate collection — someone who curates a museum. Same mechanic, better feeling.

### Additional Achievement Suggestions

| Name | Description | Why |
|---|---|---|
| **Dawn Walker** | Open morning briefing 7 days in a row | Daily ritual |
| **Elder Bond** | Reach pet Level 50 | Long-term goal |
| **Generous Soul** | Give away items to 10 lost pets in encounters | Reinforces kindness mechanic |
| **Weathered** | Experience all 5 weather events | Exploration completionism |
| **The Collector's Apprentice** | Find your first rare (✨) item | Celebrates luck |

---

## Summary

| Feature | UX Score | Key Call |
|---|---|---|
| Pet Evolution | 9/10 | Species-specific titles, celebration animation, XP-to-next estimate |
| Adventures (8 types) | 9/10 | Never punish, rare drops need drama, keep text SHORT |
| Inventory | 8/10 | One-tap actions, no drag-and-drop, 20-slot cap is right |
| Morning Briefing | **10/10** | THE feature that proves the product works. Ship exactly as spec'd. |
| Daily Gifts | 9/10 | The Wordle effect — one reason to open the app every day |
| Teach Me | 8/10 | User-initiated learning = explicit trust signal |
| Achievements | 8/10 | Rename "Hoarder" → "Curator". Add "Bonded" streak badge. |

**Sprint 14 is the best sprint yet.** It transforms the companion from a novelty into a daily habit. Morning briefing + daily gifts + adventures = Wordle-level retention. Ship it. 🔥

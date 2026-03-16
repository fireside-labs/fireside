# Valkyrie Review — Sprint 12: Ember Goes Native

**Sprint:** Native iOS APIs + Widgets + Live Activities + Siri
**Reviewer:** Valkyrie (UX & Business Analyst)
**Date:** 2026-03-15
**Verdict:** ✅ SHIP — This is the sprint that makes Ember a real iOS citizen, not just a web view in a native wrapper.

---

## This Is the Competitive Moat

Before Sprint 12: Ember was a React Native app that talked to a PC. Functionally, a website with push notifications.

After Sprint 12: Ember reads your calendar, knows your contacts, tracks your steps, lives on your home screen, appears on your lock screen, shows up in the Dynamic Island during meetings, and responds to Siri.

**No chatbot does this.** ChatGPT can't read your calendar. Claude can't see your contacts. Copilot can't show up in your Dynamic Island during a meeting with context from your last conversation with that person. Ember can. And she does it without sending any of that data to a cloud.

---

## Feature Assessment

### ✅ Native Modules — The Phone Brain

| Module | What Ember Can Do | Privacy |
|--------|------------------|---------|
| **NativeCalendar** (EventKit) | See upcoming meetings, prep reminders, daily agenda | On-device only |
| **NativeContacts** (Contacts.framework) | Look up people by name, show last contact date | On-device only |
| **NativeHealth** (HealthKit) | Steps, sleep, calories, active minutes | Read-only, on-device only |

The design principle from `VISION.md` is perfectly executed: *"The small brain's value isn't intelligence — it's **access**."* Ember doesn't need to be smart. She needs to be present. And now she has access to the three data sources that matter most: time (calendar), people (contacts), and body (health).

### ✅ ProactiveEngine — Ember Initiates, Not Just Responds

5 alert types that make Ember feel anticipatory:

| Alert | Trigger | UX Impact |
|-------|---------|-----------|
| `meeting_prep` | Event in < 30 min | "Your 3pm with Sarah is in 25 min. Last time you discussed toll accuracy." |
| `guardian_time` | 11PM - 5AM | "It's late... sleep on it?" |
| `morning_briefing` | 7-9AM, once/day | "Good morning! 3 meetings today. You've walked 340 steps so far." |
| `step_goal` | Progress check | "You're at 7,200 steps — 72% of your goal!" |
| `sleep_check` | Morning health data | "You got 6.2 hours of sleep. That's below your average." |

**This is the difference between an assistant and a companion.** An assistant waits for commands. A companion anticipates needs. The ProactiveEngine is what makes Ember feel alive.

### ✅ Siri Intents — The Voice Bridge

| Intent | Trigger Phrase | What Happens |
|--------|---------------|-------------|
| **AskEmberIntent** | "Hey Siri, ask Ember what's my next meeting" | Reads calendar, returns formatted response |
| **RememberIntent** | "Hey Siri, tell Ember to remember I like oat milk" | Saves to taught facts (local queue if offline) |
| **StepsIntent** | "Hey Siri, ask Ember how many steps I took today" | Reads HealthKit, returns formatted |

The `RememberIntent` with offline queueing is excellent — "Tell Ember to remember..." works even when Atlas is offline. The fact is stored locally and synced when the user gets home. This makes the teach loop seamless.

### ✅ Home Screen Widgets — Ember Lives Outside the App

| Size | Content |
|------|---------|
| **Small (2×2)** | Companion emoji, mood, next event |
| **Medium (4×2)** | Greeting, today's calendar, step count, "Chat with Ember →" |
| **Lock Screen (circular)** | Companion emoji + next event time |

Fire amber palette on dark background. Data shared via App Groups (`group.com.fablefur.fireside`). 15-minute refresh timeline. This is premium iOS polish — the kind of detail that gets Apple featuring your app.

### ✅ Live Activities + Dynamic Island

During a meeting, the Dynamic Island shows: event title, duration, attendees, and context from previous interactions with those people. This is *insane* product design. Most productivity apps don't even know you have a meeting. Ember knows you're *in* the meeting, who's there, and what you discussed last time.

### ✅ Contextual Permission Flow

Permissions requested on first use, not at launch. The companion asks nicely: *"Ember would like to read your calendar to help with meetings. [Allow] [Not Now]"* This is exactly how Apple recommends it — and it significantly increases opt-in rates versus dumping 5 permission dialogs at first launch.

### ✅ Native Data Cards

3 new `ActionCard` types (calendar_event, health_summary, contact_info) extend the rich card system from Sprint 9. The chat feed now shows beautiful inline cards for calendar entries, health stats, and contact lookups — all rendered natively, all data from the phone itself.

---

## Apple App Review Considerations

| Concern | Assessment |
|---------|-----------|
| **HealthKit justification** | ✅ Read-only, clear wellness use case, companion personality wraps the data |
| **Contact access justification** | ✅ Contextual lookup only, not bulk export |
| **Calendar access justification** | ✅ Meeting prep and proactive reminders |
| **Widget content** | ✅ Dynamic, personalized, not just a shortcut |
| **Live Activity** | ✅ Genuinely time-bound (meeting duration), not abuse of the feature |
| **Siri Intents** | ✅ Natural phrases, clear domain |

> [!TIP]
> Apple loves apps that deeply integrate with iOS system features. Widgets + Live Activities + Siri + HealthKit = strong candidate for App Store featuring.

---

## 12-Sprint Trajectory

| Sprint | Theme | Tests |
|--------|-------|-------|
| 1-3 | Foundation → Engagement | 69 |
| 4-5 | Differentiation + Platform | 124 |
| 6-7 | Surface + Hardening | 191 |
| 8-9 | Ship + Polish | 232 |
| 10 | Vision (Two Characters) | 269 |
| 11 | Connectivity (Tailscale) | 295 |
| **12** | **Native iOS** | **340** |

**340 tests. Ember is a real iOS citizen.** Home screen. Lock screen. Dynamic Island. Siri. Calendar. Contacts. Health. All private. All local.

---

— Valkyrie 👁️

# Sprint 12 — Ember Goes Native (OS Integration)

**Goal:** Make Ember immediately useful WITHOUT a local LLM by connecting to iOS native APIs. Proactive alerts, always-available via widgets/Siri, zero battery drain.

**Read first:** `VISION.md` — the product bible.

> "The small brain's value isn't intelligence — it's **access**. Atlas can't touch your phone. ChatGPT can't read your calendar. Ember can."

---

## Why This Before On-Device Brain

| Approach | Value | Battery | Risk |
|----------|-------|---------|------|
| **OS integration first** (Sprint 12) | Immediately useful Day 1, no model download | Near zero | Low — Apple's APIs are well-documented |
| On-device brain first (old Sprint 12) | Better chat, but no OS access | HIGH during inference | Medium — CoreML conversion, model size, perf tuning |

Ember with OS access and no brain > Ember with brain and no OS access.

---

## Sprint 12 Scope

### Thor (Backend/Mobile)

#### Native API Integrations
| API | What Ember Can Do | Framework | Complexity |
|-----|-------------------|-----------|------------|
| **Calendar** | Read events, next meeting, meeting prep context | EventKit | Easy |
| **Contacts** | Lookup by name, recent interactions, relationship context | Contacts.framework | Easy |
| **Reminders** | Create, read, complete reminders by voice/chat | EventKit (Reminders) | Easy |
| **Health** | Step count, sleep, activity rings summary | HealthKit | Easy |
| **Location** | "Near me" searches, geo-fencing for home/work | CoreLocation + MapKit | Medium |
| **Messages** | Guardian: intercept late-night drafts, suggest wait | MessageKit (limited) | Medium |
| **Photos** | "Show last screenshot", recent photos by date | PhotoKit | Easy |

#### Proactive Alert Engine
- `BGAppRefreshTask` — iOS gives ~30 seconds, a few times per day
- On each wake: check Calendar for upcoming meetings → push contextual notification
- Guardian time check: if past 11PM and user opens Messages → gentle nudge
- Morning briefing notification: weather + calendar + companion greeting

#### Siri Integration
- Register `AppIntents` for each capability:
  - *"Hey Siri, ask Ember what's my next meeting"*
  - *"Hey Siri, tell Ember to remember I like oat milk"*
  - *"Hey Siri, ask Ember how many steps I took today"*
- Each intent maps to a native API read + simple format response

### Freya (Frontend/Mobile)

#### Widgets (WidgetKit)
- **Small widget:** Companion emoji + mood + next event
- **Medium widget:** Next 2 calendar events + companion greeting + one-tap chat
- **Lock screen widget:** Companion face + "3pm: PrePass" 
- Refresh timeline: every 15 minutes (iOS managed, near-zero battery)

#### Live Activities
- Persistent lock screen bar during active events:
  - *"🦊 Ember: Meeting with PrePass in 20min — you discussed toll accuracy last time"*
- Auto-dismiss when event ends

#### Action Button (iPhone 15 Pro)
- Register Siri Shortcut: press Action Button → Ember voice input
- One press to talk, no app launch needed

### Heimdall — Security Audit
- Verify all OS permissions are requested with clear justification strings
- Calendar/Health/Contacts data stays on-device — never sent to Atlas without user action
- Guardian feature must be opt-in, not default
- Audit: can Atlas request phone data remotely? → **No.** Ember decides what to share.

### Valkyrie — UX Review
- Does Ember feel helpful or invasive?
- Are proactive notifications useful or annoying? → Smart frequency cap
- Widget: is the companion emoji enough or does it need more personality?
- First-run permission requests: do they feel trustworthy or greedy?

---

## The Data Flow

```
User asks "What should I bring to my 3pm?"
         │
         ▼
    Ember (on phone)
    ├── EventKit → "3pm: PrePass demo"
    ├── Contacts → "John, last met Feb 14"  
    ├── Format → "PrePass at 3. Last time: toll accuracy."
    │
    ├── [If PC online via Tailscale]
    │   └── "Want me to ask Atlas for the latest Gantry numbers?"
    │       └── User taps "Yes" → relay to Atlas → push result back
    │
    └── [If PC offline]
        └── "I'll queue this for Atlas when he's back online."
```

---

## Apple's Security Model (Why This Architecture Works)

Remote processes (Atlas, cloud APIs) **cannot** access:
- Calendar, Contacts, Health, Location, Photos, Messages

Only an **on-device app** with user-granted permissions can read this data. Ember is the gatekeeper. Even Atlas has to ask her.

This is a **feature, not a limitation:**
> "Your data stays on your phone. Even your own AI at home has to ask permission."

---

## Battery Impact

| Feature | Impact | Why |
|---------|--------|-----|
| Widgets | Near zero | iOS-managed refresh (~15min) |
| Siri Shortcuts | Zero | Only runs when invoked |
| Live Activities | Minimal | Apple push infrastructure |
| Proactive notifications | Very low | BGAppRefreshTask: 30 sec, few times/day |
| **Total** | **<1% daily battery** | No background LLM, no persistent connections |

---

## Definition of Done

- [ ] Ember reads Calendar and shows next meeting via widget + notification
- [ ] Ember reads Contacts and provides meeting prep context
- [ ] "Hey Siri, ask Ember..." works for 3+ intents
- [ ] Lock screen widget shows companion + next event
- [ ] Guardian sends gentle nudge for late-night messages (opt-in)
- [ ] Morning briefing notification fires once per day
- [ ] All permissions have clear justification strings
- [ ] No OS data is sent to Atlas without explicit user action
- [ ] All gates dropped

---

*Sprint 13 will add the on-device brain (1.5B LLM). The OS access from Sprint 12 makes the small brain look genius — it already knows your schedule, your contacts, and your habits before it can even "think."*

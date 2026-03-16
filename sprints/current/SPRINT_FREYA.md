# Sprint 12 — FREYA (Widgets + Live Activities + UI Integration)

// turbo-all

**Your role:** Frontend engineer. React Native/Expo (mobile), Swift (WidgetKit).
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_freya.md` when complete.

> [!IMPORTANT]
> **READ FIRST:** `VISION.md` + `sprints/current/SPRINT_12.md` — the full design.
> **READ ALSO:** `sprints/current/CREATIVE_DIRECTION.md` — brand palette (fire amber, warm tones).

---

## Context

Ember is getting iOS superpowers. Thor is building native modules for Calendar, Contacts, Health, and Siri. Your job is to build the visual surfaces: home screen widgets, lock screen widgets, Live Activities, and chat integration for native data cards.

---

## Your Tasks

### Task 1 — Home Screen Widgets (WidgetKit)

Create a WidgetKit extension with 3 widget sizes. Use the fire amber brand palette.

**Small Widget (2x2):**
```
┌──────────────┐
│  🦊 Ember     │
│  😊 Happy     │
│               │
│  Next: 3pm    │
│  PrePass Demo │
└──────────────┘
```

**Medium Widget (4x2):**
```
┌──────────────────────────────┐
│  🦊 Good morning, Jordan!    │
│                               │
│  📅 9:00  Standup             │
│  📅 3:00  PrePass Demo        │
│                               │
│  👣 2,340 steps so far        │
│  [Chat with Ember →]          │
└──────────────────────────────┘
```

**Lock Screen Widget (circular):**
```
  🦊
 3pm
```
Shows companion emoji + next event time. Tap opens chat.

- Use `WidgetKit` + `SwiftUI` in a widget extension target.
- Read data from shared `UserDefaults` (app group) written by the native modules.
- Refresh timeline: `.atEnd` with 15-minute intervals.
- Brand: dark background, fire amber accent, warm tones per Creative Direction.

### Task 2 — Live Activities

Create a Live Activity that shows during active events:

```
┌────────────────────────────────────────────┐
│ 🦊 Meeting: PrePass Demo                    │
│    Started 5 min ago · John, Sarah + 2       │
│    Last time: discussed toll accuracy        │
└────────────────────────────────────────────┘
```

- Starts when a calendar event begins (ProactiveEngine triggers it).
- Shows event title, attendees, and last meeting context (from contacts/memory).
- Auto-dismisses when event ends.
- Use `ActivityKit` in Swift.

### Task 3 — Native Data Cards in Chat

When Ember pulls native data, render it as rich cards (like Sprint 9 action cards):

**Calendar Card:**
```
┌─────────────────────────┐
│ 📅 Next Meeting          │
│ PrePass Demo · 3:00 PM   │
│ 📍 Conference Room B     │
│ 👥 John, Sarah + 2       │
│                           │
│ [Prep with Atlas →]       │
└─────────────────────────┘
```

**Health Card:**
```
┌─────────────────────────┐
│ 👣 Today's Activity      │
│ 2,340 steps              │
│ 🔥 180 calories           │
│ ⏱ 22 active minutes      │
│                           │
│ ███████░░░ 47% of goal   │
└─────────────────────────┘
```

**Contact Card:**
```
┌─────────────────────────┐
│ 👤 John Smith             │
│ PrePass · VP Engineering  │
│ 📧 john@prepass.com       │
│ Last met: Feb 14          │
│                           │
│ [Call] [Message] [Email]  │
└─────────────────────────┘
```

Add these as new `ActionCard` types: `calendar_event`, `health_summary`, `contact_info`.

### Task 4 — Permission Request Flow

Design a friendly, non-greedy permission flow:

1. On first calendar-related question: *"Ember would like to read your calendar to help with meetings. [Allow] [Not Now]"*
2. On first contact lookup: *"To look up people by name, Ember needs access to your contacts. [Allow] [Not Now]"*
3. On first health question: *"Want Ember to track your daily stats? She'll need Health access. [Allow] [Not Now]"*

Each permission is requested **in context**, not at app launch. Show the companion asking nicely with brand personality.

### Task 5 — Drop Your Gate

---

## Technical Notes

- **WidgetKit requires a separate target** in Xcode. For Expo, use `expo-apple-targets` or configure via Expo plugin.
- **Shared data:** Use App Groups (`group.com.fablefur.fireside`) to share data between the main app and the widget extension.
- **Live Activities:** Require `NSSupportsLiveActivities = YES` in Info.plist.
- **Action Button (iPhone 15 Pro):** Register a Siri Shortcut that opens Ember voice input. Users can assign it to the Action Button in iOS Settings.
- **Follow Creative Direction:** Fire amber palette, dark backgrounds, warm companion personality.

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

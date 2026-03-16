# Sprint 12 — THOR (Native iOS APIs + Proactive Engine + Siri)

// turbo-all

**Your role:** Backend/Mobile engineer. Swift (native modules), Python (backend), React Native (Expo).
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_thor.md` when complete.

> [!IMPORTANT]
> **READ FIRST:** `VISION.md` + `sprints/current/SPRINT_12.md` — the full design for this sprint.

---

## Context

Ember needs to be useful when Atlas is offline. Instead of an on-device LLM (heavy, battery-draining), we give Ember **access to iOS native APIs**. She can read Calendar, Contacts, Reminders, and Health data — things ChatGPT and Atlas literally cannot do because they're not on the phone.

> "The small brain's value isn't intelligence — it's **access**."

This sprint requires **Expo native modules** (Swift) exposed to React Native.

---

## Your Tasks

### Task 1 — Calendar Module (EventKit)

Create an Expo native module `NativeCalendar` that exposes:

```typescript
// What Ember needs:
NativeCalendar.getUpcomingEvents(hours: number): Promise<CalendarEvent[]>
NativeCalendar.getNextEvent(): Promise<CalendarEvent | null>
NativeCalendar.getTodayEvents(): Promise<CalendarEvent[]>

interface CalendarEvent {
  id: string;
  title: string;
  startDate: string; // ISO
  endDate: string;
  location?: string;
  notes?: string;
  attendees?: string[];
}
```

- Request `NSCalendarsUsageDescription` permission with: *"Ember reads your calendar to remind you about upcoming meetings and help you prepare."*
- Use `EKEventStore` in Swift, expose via Expo Modules API.

### Task 2 — Contacts Module (Contacts.framework)

Create `NativeContacts` module:

```typescript
NativeContacts.searchByName(name: string): Promise<Contact[]>
NativeContacts.getRecent(count: number): Promise<Contact[]>

interface Contact {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  organization?: string;
  lastContacted?: string;
}
```

- Permission string: *"Ember looks up contacts when you mention someone by name, so she can help you connect."*

### Task 3 — Health Module (HealthKit)

Create `NativeHealth` module:

```typescript
NativeHealth.getSteps(date: string): Promise<number>
NativeHealth.getSleepHours(date: string): Promise<number>
NativeHealth.getActivitySummary(): Promise<{ steps: number; calories: number; activeMinutes: number }>
```

- Permission string: *"Ember checks your daily stats to give you personalized wellness nudges."*
- Read-only permissions only. Ember never writes health data.

### Task 4 — Proactive Alert Engine

Create `ProactiveEngine.ts` that runs logic to generate contextual notifications:

```typescript
// Called from BGAppRefreshTask or on app foreground
async function runProactiveChecks(): Promise<ProactiveAlert[]> {
  const alerts: ProactiveAlert[] = [];
  
  // 1. Next meeting in < 30 min?
  const next = await NativeCalendar.getNextEvent();
  if (next && minutesUntil(next.startDate) < 30) {
    alerts.push({ type: 'meeting_prep', event: next });
  }
  
  // 2. Late night + Messages app active? → Guardian nudge
  const hour = new Date().getHours();
  if (hour >= 23 || hour < 5) {
    alerts.push({ type: 'guardian_time', message: 'It\'s late... sleep on it?' });
  }
  
  // 3. Morning briefing (7-9 AM, once per day)
  if (hour >= 7 && hour <= 9 && !briefedToday()) {
    const events = await NativeCalendar.getTodayEvents();
    const steps = await NativeHealth.getSteps(today());
    alerts.push({ type: 'morning_briefing', events, steps });
  }
  
  return alerts;
}
```

### Task 5 — Siri Intents (AppIntents)

Create Swift `AppIntent` structs:

1. **AskEmberIntent** — *"Hey Siri, ask Ember what's my next meeting"*
   - Reads calendar, returns formatted response
2. **RememberIntent** — *"Hey Siri, tell Ember to remember I like oat milk"*
   - Saves to taught facts via API (if Atlas is online) or local queue
3. **StepsIntent** — *"Hey Siri, ask Ember how many steps I took today"*
   - Reads HealthKit, returns formatted response

### Task 6 — Drop Your Gate

---

## Technical Notes

- **Expo Modules API:** Use `expo-modules-core` to create Swift native modules. See https://docs.expo.dev/modules/overview/
- **Permissions:** All permissions must be requested at first use, never upfront. iOS will reject apps that request all permissions at launch.
- **BGAppRefreshTask:** Register in `AppDelegate` / Expo plugin config. iOS gives ~30 seconds, a few times per day.
- **No data leaves the phone** unless user explicitly taps "Ask Atlas." Heimdall will verify.

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

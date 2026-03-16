# Sprint 12 — Ember Goes Native (Overview)

See `SPRINT_12.md` for the full design document.

## Agent Assignments

### Thor — Native iOS Modules + Proactive Engine + Siri
- EventKit (Calendar): upcoming events, today's schedule, next meeting
- Contacts.framework: search by name, recent contacts
- HealthKit: steps, sleep, activity summary
- ProactiveEngine.ts: meeting prep, guardian time check, morning briefing
- AppIntents (Siri): "Hey Siri, ask Ember..."
- Tests for all native module interfaces

### Freya — Widgets + Live Activities + Chat Cards
- WidgetKit: small (companion + next event), medium (greeting + schedule + steps), lock screen
- Live Activities: persistent bar during active meetings
- Native data cards in chat (calendar, health, contact — same ActionCard pattern as Sprint 9)
- Permission request flow (contextual, never upfront)

### Heimdall — Audit
- All permissions have clear justification strings
- OS data never sent to Atlas without explicit user action
- Guardian is opt-in, not default

### Valkyrie — UX Review
- Proactive notifications: helpful or invasive?
- Widget personality and brand consistency
- Permission request flow: trustworthy or greedy?

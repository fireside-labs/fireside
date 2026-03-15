# Sprint 6 — Full Platform: Voice + Marketplace + OS Integration

**Goal:** Bridge the gap from "companion app" to "platform surface." The mobile app has the companion features. Now it needs the platform features: voice (talk to your home AI), marketplace (commerce), and OS integration (share sheet, widget).

**Architecture context:** Fireside is 4 surfaces — Desktop Dashboard, Mobile App, Telegram Bot, CLI. After 5 sprints, mobile handles the companion well but doesn't yet let users:
- **Talk** to their home AI (voice — Whisper + Kokoro already built)
- **Buy/browse** marketplace content from their phone (commerce layer)
- **Use the AI outside the app** (share sheet, widget, Siri)
- **See real-time updates** from the desktop (currently polling, not WebSocket)

---

## Sprint 6 Scope

### Thor (Backend)
- Voice streaming endpoint for mobile (Whisper STT + Kokoro TTS over HTTP)
- Marketplace API: browse, search, preview agent personalities
- WebSocket endpoint for real-time companion state sync
- Fix morning briefing random placeholder stats (Heimdall LOW)

### Freya (Frontend)
- **Voice mode** — hold-to-talk (walkie-talkie UX), companion speaks back
- **Marketplace browsing** — browse/preview/install agent personalities from mobile
- **iOS Share Sheet extension** — "Summarize this page" from Safari
- **Home screen widget** — companion mood + quick stats (Expo widget)
- WebSocket connection for real-time sync (replace polling)

### Heimdall — Same strict rules
- 🔴 HIGH → automatic FAIL
- 🟡 MEDIUM → PASS with notes
- 🟢 LOW → informational
- Additional scope: review voice data pipeline for privacy (audio never leaves local network)

### Valkyrie — Full platform surface review
- **MUST READ:** `FEATURE_INVENTORY.md`
- Assess: does the mobile app feel like a platform surface or a standalone toy?
- Voice UX: is walkie-talkie mode fluid?
- Marketplace: does browsing create purchase intent?
- OS integration: does the share sheet feel native?
- What's still missing for App Store submission?

---

## Definition of Done

- [ ] Voice works: hold button → speak → companion replies with audio
- [ ] Marketplace: browse, search, preview personalities
- [ ] Share sheet: share URL from Safari → get summary in app
- [ ] Widget: companion mood visible on home screen
- [ ] WebSocket real-time sync replaces polling
- [ ] Morning briefing placeholder stats fixed
- [ ] All gates dropped

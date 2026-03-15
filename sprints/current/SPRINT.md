# Sprint 7 — Hardening + Achievements + TestFlight

**Goal:** Fix all Heimdall security findings, add the achievement reward loop, add weekly summary, and prepare a TestFlight build for real-device testing.

**This is the final build sprint.** After this, you test on a real phone.

**Input:** `sprints/archive/sprint_06/gates/audit_heimdall.md` + `review_valkyrie.md`

---

## Sprint 7 Scope

### Thor (Backend) — Security Hardening
- SSRF blocklist on `/browse/summarize` (MEDIUM from Heimdall Sprint 6)
- WebSocket authentication + connection cap (MEDIUM from Heimdall Sprint 6)
- Sanitize marketplace error messages (LOW from Heimdall Sprint 6)
- Achievement tracking backend (trigger + store + query achievements)

### Freya (Frontend) — Achievements + Weekly + TestFlight
- Achievement system (badges, toast popups, progress tracking)
- Weekly summary card (companion growth over the past week)
- TestFlight build via EAS (`eas build --platform ios --profile preview`)
- QR code pairing (replace manual IP entry for smoother onboarding)

### Heimdall — Verify all prior MEDIUMs are fixed
- Sprint 6 SSRF: confirm blocklist blocks localhost, RFC1918, metadata
- Sprint 6 WebSocket: confirm auth token required + connection cap
- Full regression: all 160+ tests still pass
- Voice pipeline privacy: re-verify audio never leaves local network

### Valkyrie — TestFlight readiness assessment
- **MUST READ:** `FEATURE_INVENTORY.md`
- Is the app ready for real-device testing?
- App Store metadata checklist (screenshots, description, keywords)
- Final feature gap assessment

---

## Definition of Done

- [ ] SSRF blocklist active on browse/summarize
- [ ] WebSocket requires auth token + max 5 connections
- [ ] Achievement system works (earn badges, see progress, toast popups)
- [ ] Weekly summary card shows companion growth
- [ ] EAS build configuration verified for TestFlight
- [ ] All gates dropped

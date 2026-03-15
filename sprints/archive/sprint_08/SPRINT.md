# Sprint 8 — Ship It: Settings + Onboarding + TestFlight

**Goal:** Get the app on a real phone. Stop building features. Ship.

After 7 sprints (191 tests, 0 MEDIUMs, ~80% platform coverage), the app is TestFlight-ready. Sprint 8 adds the minimum missing pieces and submits.

---

## Sprint 8 Scope

### Thor (Backend) — Minimal
- Hosted waitlist endpoint (`POST /api/v1/waitlist` — stores email, returns confirmation)
- That's it. The backend is ready.

### Freya (Frontend) — Polish + Ship
- Settings screen (mode switch, connection, voice, notifications, about)
- Onboarding v2 (self-hosted QR path + hosted waitlist path)
- Mode rename: Pet → Companion, Tool → Executive
- Marketplace set to browse-only (hide "Buy" buttons — purchases happen on desktop)
- TestFlight build verification

### Heimdall — Final pre-submit audit
- Verify no secrets in frontend code
- Verify privacy policy is accurate
- Verify permissions are justified (camera, mic, notifications)
- TestFlight readiness sign-off

### Valkyrie — App Store readiness
- App Store listing copy (name, subtitle, description, keywords)
- Screenshot requirements
- Final UX pass

---

## Definition of Done

- [ ] Settings screen works
- [ ] Onboarding has self-hosted + hosted waitlist paths
- [ ] Modes renamed Companion / Executive
- [ ] Marketplace is browse-only on mobile
- [ ] All gates dropped
- [ ] Owner runs `eas build --platform ios --profile preview`

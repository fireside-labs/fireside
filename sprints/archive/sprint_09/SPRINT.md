# Sprint 9 — Final Polish: Actions + App Store Fixes + Brand Art

**Goal:** The LAST sprint before real-device testing. Fix everything Heimdall flagged, add rich action execution through chat, finalize brand art, and prepare for TestFlight.

**After this sprint:** Owner installs on iPhone and tests everything end-to-end.

---

## Sprint 9 Scope

### Thor (Backend)
- Rich task execution: when companion routes to browse/pipeline, return structured results the mobile app can render as cards
- Cross-context search: `POST /api/v1/companion/query` — search across memories, conversations, taught facts
- Fix privacy policy contact email (owner provides real email)

### Freya (Frontend)
- Rich task cards in chat: when a task is running (browse, pipeline), show progress cards instead of plain text
- Cross-context search screen: "What do you know about X?"
- Update privacy policy to cover voice, camera, marketplace, translation, achievements
- Replace placeholder email with real email (owner will provide)
- Fix EAS preview profile: remove `simulator: true`
- Replace app icon + splash with final brand art (campfire images)

### Heimdall — Final audit before TestFlight build
- Verify all 3 pre-App Store items are fixed
- Full regression: all 207+ tests pass
- Final sign-off for `eas build`

### Valkyrie — Final pre-build review
- Everything looks right for a real device?
- Brand art review: icon + splash look good?
- App Store listing copy finalized?

---

## Definition of Done

- [ ] Rich task cards render in chat for browse/pipeline results
- [ ] Cross-context search works
- [ ] Privacy policy updated for all Sprint 4-8 features
- [ ] Real contact email in privacy policy
- [ ] EAS preview profile fixed
- [ ] Brand art (icon + splash) finalized
- [ ] All gates dropped
- [ ] Owner runs `eas build --platform ios --profile preview`

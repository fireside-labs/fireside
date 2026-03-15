# Sprint 3 — Mobile Companion: Push Notifications + App Store Readiness

**Goal:** Add push notifications so the companion can reach out to the user, add animated avatar expressions, and prepare all App Store requirements (icon, splash, privacy policy).

**Input:** `sprints/archive/sprint_02/gates/audit_heimdall.md` + `review_valkyrie.md`

**Valkyrie assessment:** 2 more sprints to App Store submission. This is sprint 1 of 2.

---

## Sprint 3 Scope

### Thor (Backend)
- Push notification infrastructure (Expo Push Notifications)
- Companion-initiated notification triggers (happiness < 30, daily gift ready, task completed)
- Fix hmac.compare_digest for pair auth (MEDIUM from Heimdall Sprint 2)
- Rate limit dict cleanup (MEDIUM from Heimdall Sprint 2)
- Backend input validation (companion name length, task payload size)

### Freya (Frontend)
- Push notification registration + handling
- Animated avatar expressions (3 variants per species: happy/neutral/sad)
- App icon + splash screen design
- Sound effects on key actions (feed, walk, level up)
- Privacy policy page (in-app static screen)

### Heimdall — Same strict rules
- 🔴 HIGH → automatic FAIL
- 🟡 MEDIUM → PASS with notes
- 🟢 LOW → informational

### Valkyrie — App Store readiness assessment
- Evaluate push notification UX
- Rate avatar expression quality
- Verify all App Store requirements are met
- Final go/no-go for Sprint 4 submission

---

## Definition of Done

- [ ] Push notifications work (companion → phone when happiness drops)
- [ ] Avatar changes expression based on mood (happy/neutral/sad)
- [ ] App icon and splash screen exist
- [ ] Sound effects on feed/walk/level-up
- [ ] Privacy policy accessible in-app
- [ ] All Heimdall Sprint 2 MEDIUM findings fixed
- [ ] All gates dropped (Thor → Freya → Heimdall → Valkyrie)

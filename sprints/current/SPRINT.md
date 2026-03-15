# Sprint 4 — Mobile Companion: Feature Parity + App Store Submission

**Goal:** Port the highest-impact desktop features to mobile and submit to the App Store.

**Input:**
- `sprints/archive/sprint_03/gates/audit_heimdall.md` + `review_valkyrie.md`
- `FEATURE_INVENTORY.md` — **READ THIS** to understand EVERYTHING the platform already has

> [!IMPORTANT]
> The desktop platform has features the mobile app doesn't surface yet.
> This sprint brings the top 3 engagement drivers to mobile and prepares for App Store submission.

---

## Sprint 4 Scope

### Thor (Backend) — No major backend work needed
The APIs for adventures, daily gifts, guardian, and teach-me already exist. Thor's job is to ensure mobile compatibility and add any missing mobile-specific endpoints.

### Freya (Frontend) — Port 3 killer features + App Store packaging
- Adventures (8 encounter types — the RPG hook)
- Daily Gifts (daily check-in mechanic — the Wordle cadence)
- Message Guardian integration (the "stops you from drunk texting" feature)
- App Store build configuration

### Heimdall — Same strict rules
- 🔴 HIGH → automatic FAIL
- 🟡 MEDIUM → PASS with notes
- 🟢 LOW → informational

### Valkyrie — MUST READ `FEATURE_INVENTORY.md`
- Review with full platform knowledge
- Assess mobile feature coverage vs desktop
- Final App Store go/no-go decision
- Prioritize remaining desktop→mobile feature gaps for future sprints

---

## Definition of Done

- [ ] Adventures work on mobile (encounter → choices → rewards)
- [ ] Daily gifts appear once per day with species personality
- [ ] Message guardian warns before sending risky messages
- [ ] App Store build configuration complete (EAS Build)
- [ ] All gates dropped

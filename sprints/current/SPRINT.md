# Sprint 2 — Mobile Companion: Polish + Security Hardening

**Goal:** Fix Heimdall's HIGH security finding, address Valkyrie's 6 UX gaps, and make the app feel consumer-ready.

**Input:** `sprints/archive/sprint_01/gates/audit_heimdall.md` + `review_valkyrie.md`

---

## Sprint 2 Scope

### Thor (Backend) — Security Hardening + Chat Persistence
- Fix CORS wildcard (HIGH from Heimdall)
- Add auth to /mobile/pair (MEDIUM from Heimdall)
- Rate limit pairing + reduce token TTL (MEDIUM from Heimdall)
- Add chat history endpoint (store/retrieve server-side)
- Add mobile-first companion adoption endpoint
- Push notification infrastructure (basic FCM/APNs setup)

### Freya (Frontend) — UX Polish
- Onboarding carousel (2-3 slides before setup screen)
- Companion avatar art (replace emoji with sprites/images)
- Chat history persistence (load from backend on mount)
- Pull-to-refresh on Care + Tasks tabs
- Haptic feedback on feed/walk/chat actions
- Mobile companion adoption flow (if no companion exists)
- Task creation button on Tasks tab

### Heimdall — Stricter Audit Rules
- 🔴 HIGH → automatic FAIL, delete upstream gates, force rework
- 🟡 MEDIUM → PASS with notes for next sprint
- 🟢 LOW → informational only

### Valkyrie — Re-validate Sprint 1 findings
- Confirm all 6 UX findings are addressed
- Validate consumer resonance improvements
- Assess readiness for App Store submission

---

## Definition of Done

- [ ] All Heimdall HIGH findings from Sprint 1 are FIXED (not deferred)
- [ ] Onboarding carousel exists for first-time users
- [ ] Companion avatar is visual (not emoji-only)
- [ ] Chat history persists across app restarts
- [ ] Pull-to-refresh works on Care + Tasks tabs
- [ ] Haptic feedback on primary actions
- [ ] Mobile companion adoption flow works (no dashboard dependency)
- [ ] Thor drops `sprints/current/gates/gate_thor.md`
- [ ] Freya drops `sprints/current/gates/gate_freya.md`
- [ ] Heimdall audits with strict threshold and drops `gate_heimdall.md`
- [ ] Valkyrie reviews and drops `gate_valkyrie.md`

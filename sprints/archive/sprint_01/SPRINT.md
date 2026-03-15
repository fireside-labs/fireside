# Sprint 1 — Mobile Companion App Foundation

**Goal:** Build the React Native (Expo) mobile app that connects to the existing Valhalla companion backend APIs.

**Philosophy:** The backend is 100% built. This sprint is a frontend job — a mobile UI that calls the 13 companion API endpoints already running at `http://<home-pc-ip>:8765`.

---

## Sprint 1 Scope

### Thor (Backend)
- Add missing mobile-friendly endpoints and CORS headers
- Implement the sync reconciliation logic (offline → online merge)
- Ensure companion API works over Tailscale IP from phone

### Freya (Frontend)
- Scaffold React Native (Expo) project
- Build the companion home screen (Chat tab)
- Build the Care tab (feed, walk, happiness bar)
- Build the Bag tab (inventory grid)
- Build the Tasks tab (queue view)
- IP/pairing setup screen (enter home PC address)
- Offline mode (cached state + "I need wifi" personality response)

---

## Definition of Done

- [ ] Expo app runs on iOS simulator
- [ ] App connects to local Valhalla backend via configurable IP
- [ ] All 4 companion tabs functional (Chat / Care / Bag / Tasks)
- [ ] Offline mode works gracefully (no crash, uses cached state)
- [ ] Thor drops `sprints/current/gates/gate_thor.md`
- [ ] Freya drops `sprints/current/gates/gate_freya.md`
- [ ] Heimdall audits and drops `sprints/current/gates/gate_heimdall.md`
- [ ] Valkyrie reviews and drops `sprints/current/gates/gate_valkyrie.md`

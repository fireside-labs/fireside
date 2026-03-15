# Sprint 11 — The Anywhere Bridge (Connection Choice)

**Goal:** Allow users to choose how their companion connects to their AI. Implement a "Connection Choice" flow with an embedded Tailscale node (`tsnet`) for secure, zero-config remote access without requiring the user to install a VPN app. 

**Read first:** `VISION.md` — the product bible.

---

## Sprint 11 Scope

### Thor (Backend)
- Integrate Tailscale (`tsnet` via Go binary or wrapper, or standard `tailscaled` with auth key) to expose the backend API/WebSocket securely.
- If using full Tailscale embedded is too complex in Python, provide the instructions/scripts to set up an ephemeral or pre-auth Tailscale node easily. 
- Ensure `bifrost.py` listens on the Tailscale IP if available.
- Create an API endpoint (`/api/v1/network/status`) to report local IP and Tailscale IP.

### Freya (Frontend)
- Mobile Onboarding: Add "Connection Choice" screen (Local, Anywhere Bridge, Hosted).
- Mobile UI: OAuth/AuthKey input for "Anywhere Bridge".
- Mobile Network: React Native embedded Tailscale (via `tailscale-react-native` or similar), or logic to resolve the PC's Tailscale IP and route WebSocket traffic through it.
- Dashboard Settings: Manage Connection Choice.

### Heimdall — Audit the connection
- Ensure Tailscale integration doesn't expose the node publicly to the broader internet, only to the user's Tailnet.

### Valkyrie — UX review
- Does the networking terminology alienate non-technical users?
- Is the "Anywhere Bridge" flow actually zero-config?

---

## Definition of Done
- [ ] Connect Choice UI exists on dashboard and mobile.
- [ ] Mobile app can connect to PC over cellular (outside local Wi-Fi) via the bridge.
- [ ] No manual port-forwarding required.
- [ ] All gates dropped

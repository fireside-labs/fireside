# Sprint 11 — FREYA (Frontend: Connection Choice)

// turbo-all

**Your role:** Frontend engineer. React/Next.js (dashboard), React Native/Expo (mobile).
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_freya.md` when complete.

---

## Context
We are giving users the choice of how their companion connects to their AI out in the world.

## Your Tasks

### Task 1 — Mobile Connection Flow
Create a new screen during mobile onboarding (after QR scan) or in Settings:
`"How should Ember connect to Atlas?"`
- **[1] Local Only:** Works only at home on Wi-Fi.
- **[2] Anywhere Bridge:** Connect securely from anywhere. Requires logging into Tailscale.

### Task 2 — Mobile WebSocket Routing
Update `mobile/src/api.ts` and WebSocket logic:
- The QR code contains the PC's Local IP.
- The mobile app should hit `http://{local_ip}:8765/api/v1/network/status` (while connected to home Wi-Fi) to fetch the PC's `tailscale_ip`.
- Store the `tailscale_ip` locally on the device.
- When making API calls or establishing WebSockets, if `connection_preference == bridge`, use the `tailscale_ip`. Otherwise use `local_ip`.

### Task 3 — Mobile VPN Guidance
If the user selects "Anywhere Bridge", instruct them to download the Tailscale app on their iPhone and log in with the same account they used on their PC. 
*(Note: True embedded SDK `tsnet` for React Native is complex; having them use the official Tailscale app running in the background is the most robust V1 approach for an Expo app)*.

### Task 4 — Dashboard Network Settings
Add a tab in the Dashboard Settings for "Network / Bridge":
- Show current Local IP.
- Show Anywhere Bridge status (Tailscale IP, active/inactive).
- Show instructions on how to enable it.

### Task 5 — Drop Your Gate

---
## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

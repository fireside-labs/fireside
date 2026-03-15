# Sprint 11 — THOR (Backend: Tailscale Integration)

// turbo-all

**Your role:** Backend engineer. Python, FastAPI, bash.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_thor.md` when complete.

---

## Context
Ember (phone) needs to talk to Atlas (PC) when the user leaves their house. Port forwarding is awful for consumers. Cloud relays compromise our "data never leaves your network" promise.
The solution is **The Anywhere Bridge** — powered by Tailscale.

## Your Tasks

### Task 1 — Backend Tailscale Setup Script
Create a helper script (e.g., `scripts/setup_bridge.ps1` and `.sh`) that installs and configures Tailscale for the user.
- It should install Tailscale CLI if not present.
- It should prompt the user to authenticate (`tailscale up`).
- *Stretch goal:* If possible, use Tailscale's OAuth/AuthKey to make this headless.

### Task 2 — Network Status API
Create `GET /api/v1/network/status` to return the node's IPs.
```json
{
  "local_ip": "192.168.1.15",
  "tailscale_ip": "100.x.y.z",
  "bridge_active": true
}
```
Read the Tailscale IP by executing `tailscale ip -4` or via OS network interfaces. 

### Task 3 — Update Bifrost Listener
Ensure `bifrost.py` binds to `0.0.0.0` or explicitly handles both the local IP and the Tailscale interface so the mobile app can reach it over the VPN.

### Task 4 — Drop Your Gate

---
## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

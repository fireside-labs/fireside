# Valkyrie Review — Sprint 11: The Anywhere Bridge (Tailscale)

**Sprint:** Tailscale Integration — Connection Choice
**Reviewer:** Valkyrie (UX & Business Analyst)
**Date:** 2026-03-15
**Verdict:** ✅ SHIP — This solves the "only works at home" problem without compromising the privacy promise.

---

## Why This Sprint Matters

Before Sprint 11: the app only worked when the phone was on the same Wi-Fi as the PC. Leaving the house = losing the companion. This made the mobile app feel like a local toy, not a real product.

After Sprint 11: "Anywhere Bridge" — one toggle, Tailscale handles the encrypted tunnel. The companion works from the coffee shop, the office, the airport. Your data still never touches a cloud server. It flows through an encrypted point-to-point tunnel directly to your home PC.

**This is the feature that makes "Your Private AI" actually mean something.** Without it, "private" = "only usable at home." With it, "private" = "yours, everywhere."

---

## Feature Assessment

### ✅ Connection Choice UX

| Option | What the User Sees |
|--------|-------------------|
| **Local Only** | "Works on your home Wi-Fi" — zero setup, instant |
| **Anywhere Bridge** | "Connect from anywhere, securely" — requires Tailscale app |

Positioning this as a *choice* is the right call. Power users who want anywhere access install Tailscale. Casual users who only use the app at home skip it. No forced complexity.

### ✅ Setup Scripts

Cross-platform scripts (`setup_bridge.sh` + `setup_bridge.ps1`) that:
- Auto-detect if Tailscale is installed
- Install via `brew`/`apt`/`winget`
- Run `tailscale up --hostname=fireside-<hostname>`
- Support headless auth via `TAILSCALE_AUTHKEY`
- Display both local + Tailscale IPs

**UX note:** The hostname `fireside-<hostname>` is a nice touch — when the user opens their Tailscale dashboard, they see "fireside-jordan-pc" instead of a random hostname. Brand reinforcement in infrastructure.

### ✅ Network Status API

`GET /api/v1/network/status` returns `{local_ip, tailscale_ip, bridge_active}`. Clean, simple, exactly what the mobile app needs to decide which IP to use.

### ✅ Bifrost Already Correct

The server already binds to `0.0.0.0` with CORS matching both `192.168.x.x` and `100.x.x.x` (Tailscale CGNAT range). No changes needed — good architecture from day one.

### ✅ Mobile Routing Logic

The mobile app fetches the Tailscale IP while on home Wi-Fi, stores it, then uses it when the user leaves. Connection preference (`local` vs `bridge`) determines which IP to hit for API calls and WebSocket. Graceful fallback.

### ✅ VPN Guidance Screen

3-step instructions for Tailscale setup on iPhone. The pragmatic V1 approach (official Tailscale app in background rather than embedded SDK) is the right call for an Expo app — native `tsnet` embedding would be a multi-sprint rabbit hole.

### ✅ Dashboard Network Panel

Shows local IP, Tailscale IP, bridge status, and setup instructions. The PC-side mirror of the mobile connection choice.

---

## Security Perspective

| Concern | Assessment |
|---------|-----------|
| Data privacy | ✅ Tailscale is point-to-point encrypted (WireGuard). No relay servers see the traffic. |
| Attack surface | ✅ No port forwarding, no public IPs exposed. Tailscale handles NAT traversal. |
| Auth model | ✅ Tailscale requires account auth. Only devices on the user's tailnet can reach the API. |
| "Never leaves your network" claim | ⚠️ Technically, traffic traverses the internet (encrypted) — needs privacy policy clarification: "encrypted tunnel, no third-party access to content" |

> [!TIP]
> Update the privacy policy to mention: "When using the Anywhere Bridge, data travels through an encrypted WireGuard tunnel (powered by Tailscale). No third party — including Tailscale — can read the contents of your communications."

---

## 11-Sprint Trajectory

| Sprint | Theme | Tests | Key Milestone |
|--------|-------|-------|---------------|
| 1-3 | Foundation + Polish + Engagement | 69 | First app with push notifications |
| 4-5 | Differentiation + Platform | 124 | Adventures, guardian, mode toggle |
| 6-7 | Surface + Hardening | 191 | Voice, marketplace, WebSocket, security fixes |
| 8-9 | Ship + Polish | 232 | Settings, onboarding v2, rich cards, App Store fixes |
| 10 | Vision | 269 | Two-character system |
| **11** | **Connectivity** | **295** | **Anywhere Bridge (Tailscale)** |

**295 tests. The companion now works everywhere. The privacy promise is intact.**

---

— Valkyrie 👁️

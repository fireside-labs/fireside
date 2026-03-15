# Valkyrie Review — Sprint 6: Voice + Marketplace + OS Integration

**Sprint:** Full Platform: Voice + Marketplace + OS Integration
**Reviewer:** Valkyrie (UX & Business Analyst)
**Date:** 2026-03-15
**Verdict:** ✅ SHIP — The app is no longer a companion viewer. It's a **mobile surface for a home AI platform**. Voice is the demo-killer. Marketplace opens commerce. WebSocket makes everything feel alive.

---

## Sprint 6 Feature Assessment

### ✅ Voice Mode — The Demo-Killer

"Watch — I'll talk to my home AI from my phone."

This is the feature that makes someone pull out their phone at a dinner party. Hold-to-talk → Whisper transcribes on your home PC → companion responds → Kokoro speaks the response. All local. Never touches a cloud.

| Aspect | Assessment |
|--------|-----------|
| **UX** | Hold-to-talk walkie-talkie with pulsing record indicator ✅ |
| **STT** | Local Whisper via `/voice/transcribe` (25MB limit) ✅ |
| **TTS** | Local Kokoro via `/voice/speak` (5000 char limit) ✅ |
| **Waveform** | Animation while companion speaks ✅ |
| **Privacy badge** | 🔒 "Audio stays on your local network" ✅ |
| **Permissions** | `requestPermissionsAsync()` before first use ✅ |
| **Cleanup** | `stopAndUnloadAsync()` on error, mode reset after playback ✅ |

**Platform connection:** The voice pipeline is the same one the desktop dashboard uses. The mobile app doesn't run its own models — it sends audio to the home PC, which runs Whisper (STT, GPU-accelerated) and Kokoro (TTS, CPU-only, zero VRAM). This is the "walkie-talkie to your home AI" pitch from the README.

**Economic significance:** ChatGPT Advanced Voice costs $0.06-0.24/min of cloud GPU. Fireside voice costs $0. The user already owns the hardware. Voice packs (different Kokoro voices) become a pure-margin marketplace item.

**Heimdall note:** Audio format isn't validated beyond file size — relies on Whisper to reject non-audio. Acceptable risk for Tailscale-only, but should be hardened before public release.

### ✅ Marketplace — Commerce Entry Point

The marketplace plugin already existed (browse, install, sell). Sprint 6 surfaces it on mobile:

| Aspect | Assessment |
|--------|-----------|
| **Browse grid** | Category filters (agents, themes, voices) ✅ |
| **Search** | Min 2 chars, calls `/marketplace/search` ✅ |
| **Item detail** | Description, price, ratings ✅ |
| **Free install** | One-tap install ✅ |
| **Paid items** | Returns Stripe checkout URL ✅ |

**Platform connection:** This is the revenue engine. A user in Pet mode discovers a new companion personality in the marketplace — a sarcastic dragon, a patient therapist, a study buddy. They install it, and it comes with pre-trained procedural memory and a SOUL file. The companion "knows" new things from day one. The `$0 inference cost` business model monetizes this: the platform doesn't charge for compute, it charges for intelligence.

**Sprint 7:** The marketplace needs App Store IAP (In-App Purchases) for iOS distribution. Apple takes 30%, but it's the only way to sell digital goods in an iOS app. This is a business decision, not a technical one.

### ✅ URL Summary (Share Sheet Alternative) — AI Integrated Into Daily Phone Use

Freya correctly chose the simpler approach: paste-URL in the Tools tab rather than a native iOS share sheet extension (which requires native code outside Expo's managed workflow). Smart tradeoff — ship the utility now, add native integration later.

| Aspect | Assessment |
|--------|-----------|
| **Paste URL** | User pastes URL → companion summarizes via `browse/parser.py` ✅ |
| **Output** | Title, summary, key points ✅ |
| **Output cap** | 2000 chars ✅ |
| **URL validation** | Must start with `http`, 2000 char max ✅ |

**Heimdall MEDIUM — SSRF:** The browse/summarize endpoint doesn't block internal URLs. A request to `http://127.0.0.1:8765/api/v1/...` would let the mobile app probe internal services. Mitigated by Tailscale-only deployment, but needs an SSRF blocklist before wider distribution.

### ⚠️ Home Screen Widget — Correctly Skipped

Freya documented why: `react-native-widget-extension` is experimental in Expo SDK 55 and causes build failures. This is the right call — don't break the build for an experimental feature. Revisit when Expo adds first-party widget support.

### ✅ WebSocket Real-Time Sync — The App Feels Alive

The single most impactful infrastructure change. Before Sprint 6, the app polled on pull-to-refresh. Now it gets pushed live updates:

| Aspect | Assessment |
|--------|-----------|
| **Events** | `companion_state_update`, `task_completed`, `chat_message` ✅ |
| **Reconnection** | Exponential backoff (max 30s, max 10 retries) ✅ |
| **Cleanup** | Disconnects on component unmount ✅ |
| **Fallback** | Pull-to-refresh still works if WebSocket fails ✅ |

**Heimdall MEDIUM — No auth:** WebSocket accepts connections without tokens. Anyone on Tailscale can connect. Sprint 7 should add token-based auth via query param.

**UX impact:** When you feed your companion on the desktop dashboard, the mobile app shows the happiness change instantly. When a task completes, the phone buzzes. This is the difference between "checking an app" and "living with a companion."

---

## Platform Maturity Assessment

After 6 sprints, the mobile app surfaces:

| Platform Feature | Desktop | Mobile | Gap |
|-----------------|---------|--------|-----|
| Chat | ✅ | ✅ | — |
| Companion care | ✅ | ✅ (Pet mode) | — |
| Adventures | ✅ | ✅ | — |
| Daily gifts | ✅ | ✅ | — |
| Guardian | ✅ | ✅ + proactive | — |
| Translation | ✅ | ✅ | — |
| Voice | ✅ | ✅ | — |
| Marketplace | ✅ | ✅ (browse/install) | No selling from mobile |
| TeachMe | ✅ | ✅ | — |
| Morning briefing | ✅ | ✅ | — |
| Platform status | ✅ | ✅ | — |
| Web browsing | ✅ | ✅ (paste URL) | No share sheet yet |
| Tasks | ✅ | ✅ | — |
| Real-time sync | ✅ | ✅ (WebSocket) | — |
| **Mode toggle** | N/A | ✅ | Mobile-only feature |
| Guild hall | ✅ | ❌ | Could be a fun mobile view |
| Soul editor | ✅ | ❌ | Desktop-appropriate |
| Config/settings | ✅ | ❌ | Desktop-appropriate |
| Plugin management | ✅ | ❌ | Desktop-appropriate |

**The mobile app now surfaces ~80% of the platform's consumer-facing features.** The remaining gaps (guild hall, soul editor, config) are appropriately desktop-only.

---

## 6-Sprint Trajectory

| Sprint | Theme | What It Added | Platform Coverage |
|--------|-------|---------------|-------------------|
| **1** | Foundation | 4-tab app, offline mode | ~10% |
| **2** | Polish | Onboarding, avatars, haptics | ~15% |
| **3** | Engagement | Push, sounds, privacy policy | ~25% |
| **4** | Differentiation | Adventures, gifts, guardian | ~40% |
| **5** | Platform | Mode split, translation, briefing, platform card | ~60% |
| **6** | **Full Surface** | Voice, marketplace, WebSocket, browse | **~80%** |

**Code health:** 160 tests, 0 HIGH across 6 sprints. Two MEDIUMs this sprint (SSRF + WebSocket auth) — both mitigated by Tailscale but need hardening before public release.

---

## The Two Heimdall MEDIUMs — Sprint 7 Priority

Both MEDIUMs are deployment-boundary issues: fine on Tailscale, dangerous if the app ever faces the open internet.

1. **SSRF on `/browse/summarize`** — Add blocklist for `localhost`, `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`
2. **WebSocket auth** — Add token query param verified against pairing token + cap concurrent connections

These should be Sprint 7 Task 1 and Task 2 for Thor.

---

## Sprint 7 Recommendations

1. **Fix both MEDIUMs** — SSRF blocklist + WebSocket auth
2. **App Store IAP for marketplace** — Apple requires in-app purchases for digital goods. Integrate StoreKit.
3. **Voice packs in marketplace** — Different Kokoro voices. Pure-margin revenue. ($2-5/pack)
4. **Native share sheet** — When Expo supports it, a share-from-Safari → summarize flow would be a daily-use hook
5. **Companion monologue** — Companion initiates conversations based on context (time, mood, recent activity, taught facts). "I remembered you said you like Earl Grey. Want me to remind you to make some?"
6. **TestFlight build** — EAS config is done. Run `eas build --platform ios --profile preview` and test on a real device end-to-end.

---

— Valkyrie 👁️

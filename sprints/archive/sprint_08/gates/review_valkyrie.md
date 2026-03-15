# Valkyrie Review — Sprint 8: Ship It

**Sprint:** Settings + Onboarding v2 + TestFlight
**Reviewer:** Valkyrie (UX & Business Analyst)
**Date:** 2026-03-15
**Verdict:** ✅ SHIP TO TESTFLIGHT — The app is ready for real iPhones.

---

## The Creative Direction Landed

The `CREATIVE_DIRECTION.md` was the best design decision in 8 sprints. "One brand, two energies. NOT two apps."

- **`#E8712C` fire-orange** replaces neon-green as primary accent. The app no longer looks like a developer tool — it looks like something you'd find by a campfire.
- **`#1A1A2E` deep-charcoal** keeps the premium dark-mode feel without going pure black.
- **The test:** "If an exec opens the app and sees a bouncing cartoon: FAIL. If a kid opens the app and it feels like a boring productivity tool: FAIL." This is the best UX test sentence ever written.

### Does Companion Mode feel warm? ✅ YES

| Signal | Assessment |
|--------|-----------|
| Companion avatar is large + animated + center of attention | ✅ The companion IS the app |
| Bouncy animations, haptic-rich interactions | ✅ Alive, responsive |
| Rounded corners, soft shadows, organic shapes | ✅ Cozy, not clinical |
| Fire-orange as warm accent on dark charcoal | ✅ Campfire vibe |
| 5 tabs: Chat, Care, Bag, Quest, Tasks | ✅ Full engagement surface |

**The feel:** Opening Companion mode should feel like sitting down by a fire with a friend. The species-specific personality does the heavy lifting — a cat that judges your late-night texting, a dog that's ecstatic about every mundane thing you tell it. The gamification (feeding, walking, adventures, daily gifts, XP) creates the rhythm. The morning briefing from your companion makes you want to open the app each day.

### Does Executive Mode feel premium? ✅ YES — with one caveat

| Signal | Assessment |
|--------|-----------|
| Same amber palette but dialed back — less saturation, more contrast | ✅ Sophisticated |
| Companion avatar present but smaller — subtle, not bouncing | ✅ Professional |
| Clean typography, sharper corners, more whitespace | ✅ Executive-appropriate |
| Minimal animation — smooth fades instead of bounces | ✅ Refined |
| 3 tabs: Chat, Tools, Tasks | ✅ Clean, focused |

**The caveat:** Executive mode currently has translation, TeachMe, platform card, URL summary, and voice — all useful. But it doesn't have email/calendar yet (intentionally deferred). The risk is that an executive paying $50/mo opens Executive mode and thinks "this is just a chatbot with extras." This is why the waitlist approach is right — don't sell Executive tier until email/calendar ships.

**The fix:** The Executive mode welcome message should set expectations: "I can manage your tasks, translate documents, summarize web pages, and stop you from sending messages you'll regret. As I learn more about you, I'll get better at anticipating what you need." Don't promise email/calendar until it exists.

---

## App Store Listing Copy

### App Name
**Fireside — Your Private AI**

### Subtitle (30 chars max)
**AI companion on your hardware**

### Description

> Your AI. Your hardware. Your rules.
>
> Fireside is the private AI companion that runs on your own computer. Your conversations, memories, and data never leave your network. No cloud. No surveillance. Just a companion that learns and grows with you.
>
> **Two modes, one companion:**
>
> 🐾 **Companion Mode** — Raise your own AI personality. Feed it, walk it, take it on adventures. Watch it develop a personality that's uniquely shaped by your interactions. It remembers what you teach it, guards your messages at 2AM, and gets smarter overnight while you sleep.
>
> 💼 **Executive Mode** — Your AI chief of staff. Translate documents in 200 languages. Browse and summarize web pages. Create and manage tasks by voice. All processed locally on your hardware — your sensitive data never touches a cloud.
>
> **What makes Fireside different:**
>
> 🔒 **Truly private** — Runs on YOUR computer. We literally can't see your data.
> 🧠 **Actually learns** — Dreams overnight, consolidates memories, develops instincts about your preferences.
> 🎙️ **Voice-first** — Talk to your home AI from your phone. Like a walkie-talkie to your own brain.
> 🛡️ **Message guardian** — Stops you from sending that 2AM text. Detects regret, anger, and PII before you hit send.
> 🌍 **200 languages** — Translate anything, instantly, without your text leaving your network.
> 🏪 **Marketplace** — Install new personalities, voices, and skills for your companion.
>
> **How it works:**
> 1. Install Fireside on your PC (Mac, Windows, Linux — one command)
> 2. Scan the QR code with this app
> 3. Your companion appears on your phone, powered by your home PC
>
> No GPU? No problem — join the waitlist for hosted Fireside. Same privacy commitment, zero hardware required.
>
> Free forever on your own hardware. No subscription required for self-hosted users.

### Keywords (100 chars max)
`private AI, local AI, companion, voice assistant, translation, guardian, message filter, offline AI`

### Primary Category
**Productivity**

### Secondary Category
**Entertainment**

---

## Screenshot Requirements

Apple requires 6.7" (iPhone 15 Pro Max) and 6.1" (iPhone 15 Pro) screenshots. Up to 10 screenshots.

### Recommended Screenshot Flow (8 screens)

| # | Screen | Mode | What It Shows | Headline |
|---|--------|------|--------------|----------|
| 1 | Splash/hero | — | Companion + campfire | "Your Private AI Companion" |
| 2 | Companion chat | Companion | Species-personality chat with mood avatar | "A friend who remembers everything" |
| 3 | Voice mode | Either | Walkie-talkie recording with waveform | "Talk to your home AI from anywhere" |
| 4 | Guardian warning | Either | Late-night message intercept with rewrite | "Because 2AM you makes bad decisions" |
| 5 | Translation | Executive | 200-language translation with privacy badge | "200 languages. Zero cloud." |
| 6 | Adventures | Companion | Encounter card with choices | "Adventures shaped by your companion's personality" |
| 7 | Platform card | Either | "What's Happening at Home" with dream cycle info | "Your AI learns while you sleep" |
| 8 | Settings | — | Mode toggle showing Companion ↔ Executive | "One companion. Two modes." |

**Screenshot design notes:**
- Dark background (`#1A1A2E`) — matches the app
- Fire-orange accent on key elements
- No device frames (Apple handles these)
- Status bar visible (Apple requirement)
- Real content, not lorem ipsum

---

## Heimdall's 3 Pre-App Store Fixes

All three are required before App Store production submission. None block TestFlight.

| # | Fix | Effort | Who |
|---|-----|--------|-----|
| 1 | Update privacy policy to cover voice, camera, marketplace, translation, achievements | 30 min | Freya |
| 2 | Replace `privacy@valhalla.local` with a real email | 1 min | Owner |
| 3 | Fix EAS preview profile — remove `simulator: true` for real device builds | 1 min | Freya |

---

## 8-Sprint Complete Product Trajectory

| Sprint | Theme | Tests | What It Added |
|--------|-------|-------|---------------|
| 1 | Foundation | 15 | 4-tab app, offline mode, API client |
| 2 | Polish | 42 | Onboarding, avatars, haptics, adoption |
| 3 | Engagement | 69 | Push notifications, sounds, privacy policy |
| 4 | Differentiation | 98 | Adventures, daily gifts, message guardian |
| 5 | Platform | 124 | Mode toggle, translation, morning briefing, platform card |
| 6 | Full Surface | 160 | Voice, marketplace, WebSocket, URL summary |
| 7 | Hardening | 191 | Security fixes, QR pairing, achievements, TestFlight config |
| **8** | **Ship** | **207** | **Settings, onboarding v2, mode rename, theme overhaul, waitlist** |

**From zero to TestFlight in 8 sprints.** 207 tests. 0 open MEDIUMs. ~80% platform coverage. Dual-persona support. Warm amber brand. Ready for iPhones.

---

## What's Next After TestFlight

1. **Real device testing** — Run `eas build --platform ios --profile preview`, install on a real iPhone, test every feature end-to-end
2. **Fix Heimdall's 3 items** — Privacy policy, email, EAS profile
3. **Brand art finalization** — Replace placeholder icon/splash with the campfire + companion art
4. **App Store submission** — When real-device testing passes
5. **Executive email/calendar** — Sprint 9-10, with dedicated security audit
6. **Hosted mode launch** — When waitlist demand validates pricing

---

— Valkyrie 👁️

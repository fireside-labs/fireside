# 📱 Mobile Sprint Roadmap

## Core Philosophy

> **One agent. Two bodies.** Ember lives on the desktop (big brain, GPU, pipelines). The phone extends Ember's senses — iOS contacts, texts, photos, camera, location, microphone. To the user, it's always the same companion. The phone is a portal, not a separate app.

> **Never truly offline.** Qwen 0.5B runs on-device. NLLB-200 translates 200 languages locally. When disconnected from the desktop, Ember is running in "low power mode" — reduced intelligence, but never dead.

---

## Sprint 1 — The Magic Handoff 🔗
*Make the desktop→mobile pairing feel seamless and emotional*

| Feature | What | Where |
|---------|------|-------|
| **Companion creation on mobile** | If no companion exists on desktop, mobile onboarding lets you pick species + name. Saved to backend on first connect. | `onboarding.tsx` |
| **Incubation QR** | Desktop shows QR code *during* initial companion creation, not buried in settings. "While Ember wakes up, let's get him on your phone." | Dashboard + `QRPair.tsx` |
| **First-jump greeting** | After QR scan, Ember greets you in character: *"Whoa, cozy in here! My brain's on your PC but now we're connected."* | `onboarding.tsx` |
| **Orphaned app flow** | User downloads app first without desktop → beautiful "save your companion" flow, email themselves the desktop download link. | `onboarding.tsx` |
| **Network auto-discovery** | Same Wi-Fi? App detects the desktop via mDNS/Bonjour. No QR needed — *"I see Jordan's PC. Connect?"* | `api.ts` + native module |

**Sprint goal:** A new user goes from zero to paired in under 60 seconds and it feels magical.

---

## Sprint 2 — The Remote Control 📡
*Pipeline status + push notifications from your pocket*

| Feature | What | Where |
|---------|------|-------|
| **Pipeline mini-view** | Dedicated section on Tasks tab showing active pipelines, stage progress, iteration count. Tappable → detail with agent messages. | `tasks.tsx` |
| **Push for pipeline events** | Desktop fires push on: PASS, FAIL, escalation, debate complete, pipeline done. Phone shows rich notifications with action buttons. | Backend `bifrost.py` + `notifications.ts` |
| **Intervene from mobile** | In pipeline detail, hold "Intervene" button → voice or text instruction → injected into running pipeline on desktop. | `tasks.tsx` + API |
| **Heartbeat feed** | Subtle banner on Home tab: *"Ember is running tests..."* / *"Pipeline finished. 18/18 ✅"* — passive awareness without opening pipeline view. | `care.tsx` |

**Sprint goal:** You walk away from your desk and your phone keeps you in the loop.

---

## Sprint 3 — The Extra Senses 👁️
*Leverage what the phone can do that the desktop can't*

| Feature | What | Where |
|---------|------|-------|
| **Context clipboard** | Share sheet integration → share URLs, text, images from any iOS app to Ember. Queued for desktop processing, summarized on arrival. | iOS Share Extension |
| **Photo → Task** | Take a photo of whiteboard/napkin → on-device OCR with Qwen 0.5B → queued for richer analysis on desktop → tasks extracted. | Camera + Task Queue |
| **Voice-to-Queue** | Hold mic button anywhere in the app → *"When I'm back at my desk, remind me about the user roles table."* → desktop gets a sticky note. | `VoiceMode.tsx` + queue |
| **iOS Contacts bridge** | *"What's Sarah's email?"* — Ember queries iOS contacts (with permission) and responds instantly, no network needed. | Contacts native module |
| **Text/iMessage context** | *"Summarize my last 5 texts from Dave"* — Ember reads iOS messages (with permission), summarizes using on-device model. Privacy-first. | Messages native module |
| **Web browsing (on phone)** | Ember can browse the web from the phone independently — useful when desktop is off or for quick lookups while you're out. | On-device browse |

**Sprint goal:** Ember can "see" through your phone — camera, contacts, texts, clipboard, web.

---

## Sprint 4 — The Living Companion 💗
*Make Ember feel alive between interactions*

| Feature | What | Where |
|---------|------|-------|
| **Dream Journal push** | Morning notification: *"Ember learned 3 things overnight."* Tap → morning briefing card with lessons from the dream cycle. | Push + `MorningBriefing.tsx` |
| **Personality nudge cards** | *"Ember has been getting more direct this week. Is that right?"* Accept/reject/tune. Same personality, just surfacing growth. | `personality.tsx` |
| **iOS Home Screen widget** | Companion face + mood indicator + current activity. Pipeline running? Widget shows progress. Escalated? Widget turns amber. | iOS Widget Extension |
| **Dynamic Island (bonus)** | Live activity showing pipeline progress bar when a build is running. | Live Activities API |
| **Proactive "away" context** | When Tailscale activates (left home Wi-Fi): *"We're out! Tunnel is secure."* When back on home Wi-Fi: *"Welcome home. Here's what happened."* | `useConnection.ts` |

**Sprint goal:** You glance at your phone and Ember is already there, without opening the app.

---

## Sprint 5 — Net Navis 🤝
*Companion-to-companion collaboration via mesh*

| Feature | What | Where |
|---------|------|-------|
| **Mesh contact book** | Add friends' Fireside nodes by exchanging mesh keys. Your companion knows their companion by name. | Settings + mesh API |
| **Cross-companion queries** | *"Ask Jake's Atlas what research he's done on auth patterns."* → Ember contacts Atlas via mesh → Jake gets notification → response flows back. | Chat + mesh routing |
| **Joint pipelines** | Two companions collaborate on a shared pipeline. Ember codes, Atlas reviews. Split-screen on mobile showing both companions' contributions. | Pipeline + mesh |
| **Privacy gates** | Every cross-companion query requires explicit approval from the other user via push notification. No silent data sharing. | Push + approval flow |

**Sprint goal:** Your companion can talk to other people's companions. Secure, private, user-approved.

---

## Sprint 6 — Trust & Polish 🔒

| Feature | What | Where |
|---------|------|-------|
| **Privacy badge** | Always-visible indicator: *"Processing: Your PC"* or *"Processing: On-device"*. Trust signal. | Global header |
| **Forget Everything button** | Nuclear option — wipes companion memory across all devices on the mesh. Makes users *more* comfortable. | Settings |
| **Smart network routing** | Auto-switch local↔Tailscale based on Wi-Fi SSID detection. No user action needed. | `api.ts` |
| **Skills marketplace** | Premium skills purchasable from mobile. Free: translate, search. Premium: deep research, code review, daily digest. | `skills.tsx` |

---

## Sprint Priority Matrix

```
                    HIGH IMPACT
                        │
    Sprint 1            │          Sprint 3
    (Magic Handoff)     │          (Extra Senses)
    ────────────────────┼────────────────────
    Sprint 2            │          Sprint 5
    (Remote Control)    │          (Net Navis)
                        │
                    LOW EFFORT ─────── HIGH EFFORT
                        │
    Sprint 6            │          Sprint 4
    (Trust & Polish)    │          (Living Companion)
```

**Recommended order:** 1 → 2 → 3 → 4 → 6 → 5

Ship the handoff and remote control first (that's the core value). Then the phone senses (differentiator). Then the living companion polish (retention). Trust features throughout. Net Navis last — it's the most complex and requires two users to test, but it's the moonshot.

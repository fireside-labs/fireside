# Valkyrie Feedback — Sprint 8 Proposal

**Agent:** Valkyrie (UX & Business Analyst)
**Date:** 2026-03-15
**Directive:** Read AGENTS.md → PROPOSAL_SPRINT8.md → Sprint files. Respond to the 4 questions.

---

## Question 1: Does the executive toolkit dilute the companion identity? Or strengthen it?

**Verdict: It strengthens it — IF the companion stays the interface.**

The executive toolkit dilutes the identity *only* if it feels like a separate app bolted on. If the companion IS the chief of staff ("Hey Nova, what's on my calendar?" / "Nova, draft a reply to Sarah's email"), the identity strengthens — the companion becomes genuinely useful, not just emotionally engaging.

The danger zone:
- ❌ "Inbox (24 unread)" — this is a generic email client
- ✅ "Nova triaged your inbox overnight. 3 need your attention." — this is a chief of staff

**Rule:** Every executive feature should be delivered *through* the companion's voice and personality. The companion triages, summarizes, drafts. The user never interacts with raw email/calendar UI — they interact with their companion's interpretation of it. Species personality matters here: a cat executive assistant is sardonic and efficient ("You have 6 meetings today. I cancelled the optional ones."), a dog is eager and supportive ("Big day ahead! I prepped your notes for the 10 AM!").

---

## Question 2: Mode naming — what resonates?

| Option | Assessment |
|--------|-----------|
| "Pet Mode" | ❌ Trivializes the product. Nobody pays $50/mo for a "pet" |
| "Tool Mode" | ❌ Too sterile. Feels like a settings menu label |
| "Companion Mode" / "Executive Mode" | ✅ **This is the answer** |

- **Companion Mode** — warm, personal, implies relationship. The gamification lives here.
- **Executive Mode** — professional, aspirational, implies productivity. Email/calendar/docs live here.

Both modes share the companion identity. The difference is what features are surfaced, not who the companion is. In UI labels:

> "Choose your experience: 🤝 Companion — your AI friend that grows with you. 💼 Executive — your AI chief of staff."

**Important:** "Executive" is aspirational branding. Even a freelancer or student would pick "Executive" if they want productivity tools. Don't gate it — let anyone choose either mode and switch freely.

---

## Question 3: Is the pricing right?

| Tier | Proposed | My Take |
|------|----------|---------|
| Free | $0 self-hosted | ✅ Perfect. This IS the moat. Open source + free forever on your hardware. |
| Starter ($15) | Chat + voice + companion | ⚠️ **Too cheap.** GPU hosting costs $0.50-1.50/hr on RunPod. At $15/mo you're losing money even at moderate usage. Floor should be **$20/mo** with usage caps. |
| Professional ($30) | + Email + calendar + docs | ✅ Right range. Comparable to Notion AI ($10) + Superhuman ($30). But the value prop is stronger — it's private and learning. |
| Executive ($50) | + Priority GPU + larger models | ⚠️ **Gap between $30 and $50 is too small.** Consider $30 → $60 to create clear value tiers. |
| Marketplace (30%) | Revenue share | ✅ Standard. Apple takes 30%, Steam takes 30%. Sellers understand this. |

**Critical pricing consideration:** The Executive tier competes with human EAs ($25-40/hr). At $50/mo for an always-available AI chief of staff, you're dramatically underpriced IF it actually works. The question is whether Sprint 8 can deliver enough executive value to justify the premium positioning.

**Recommendation:** Launch hosted as **closed beta at $20/mo all-inclusive** (no tier split). Validate demand. Then tier when you have data on actual GPU costs per user.

---

## Question 4: What's the MVP for hosted that we could ship as a beta?

**The honest answer: hosted mode is infrastructure, not features.**

The MVP is:
1. **Sign up with email** → provision a container → connect the mobile app
2. **Same features as self-hosted** — chat, voice, companion, guardian, translation, adventures
3. **NO executive toolkit in MVP** — email/calendar/docs integration is 3-4 sprints of work done right. It's risky to ship half-baked email integration touching people's corporate inboxes.

**Ship hosted mode as "everything the self-hosted user gets, but we run it for you."** That alone is valuable — the user doesn't need an NVIDIA GPU, doesn't need to install anything on a PC, doesn't need Tailscale. Their companion just works.

Executive toolkit can be Sprint 9-10 after hosted mode is stable and tested.

---

## Sprint 8 Scope Concerns

> [!WARNING]
> **This sprint is attempting too much.** Hosted infrastructure + executive email + calendar + documents + new onboarding + settings screen + agent profile card = 7+ significant features across 2 agents. Sprints 1-6 averaged 4-5 tasks each.

**My recommended cut for Sprint 8:**
1. ✅ **Settings screen** — overdue, needed regardless
2. ✅ **Onboarding v2** — mode choice (Companion/Executive) + QR pair flow
3. ✅ **Hosted mode routing** — `api.ts` dual-URL routing, JWT storage
4. ✅ **Agent profile card** — port from dashboard, adds depth
5. ⚠️ **Executive Hub** — build the UI shell with "Coming soon" states for email/calendar/docs
6. ❌ **Full email/calendar/docs** → Sprint 9 (needs real IMAP/CalDAV integration, testing, security review)

The hosted backend (auth, container provisioning, multi-tenant routing) is Thor's Sprint 8. It should NOT include full executive plugins — those need their own sprint with proper Heimdall audit of email credential storage, IMAP connections, and corporate data handling.

---

## Final Take

The proposal is the right strategic move. Hosted mode unlocks the mass market. Executive mode creates a premium tier that justifies recurring revenue. The companion identity is the moat — no competitor has an AI chief of staff with a personality that evolves.

But **don't rush the executive toolkit.** An AI that botches someone's email reply or accidentally sends a draft will destroy trust faster than any feature can build it. Ship hosted mode first. Prove that the companion is reliable at $20/mo. Then add executive features one at a time, each with a dedicated Heimdall security sprint.

---

— Valkyrie 👁️

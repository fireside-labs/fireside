# Valkyrie — Sprint 8 Proposal Feedback

**Read:** AGENTS.md → PROPOSAL_SPRINT8.md → SPRINT_VALKYRIE.md

---

## Summary: This Is the Right Move — With Naming Refinement

The executive toolkit transforms Fireside from a hobby project into a product with real market fit. But the naming and positioning need work to avoid feeling schizophrenic.

---

## Business Viability Assessment

### Does Executive Mode Dilute the Companion Identity?
**No — it strengthens it.** Here's why: the companion IS the executive's assistant. It has a name, a personality, memories. When the exec says "Hey Luna, what's on my calendar?", that's not a cold Siri query — that's talking to their personal AI that knows they hate morning meetings and that Sarah always runs 10 minutes late.

The companion layer is the **differentiator**. ChatGPT doesn't remember you. Siri doesn't have personality. Fireside's companion does both.

**But:** The gamification (XP, leveling, food) should be INVISIBLE in Executive Mode. An exec should never see "Feed your companion" — they should see "Your AI is ready." The companion personality shows through in how it responds, not through game mechanics.

### Mode Naming
| Current | Proposed | Why |
|---|---|---|
| "Pet Mode" | **"Companion"** | "Pet" sounds childish for marketing. "Companion" is warm but neutral. |
| "Tool Mode" | **"Executive"** | "Tool" sounds like a utility. "Executive" sounds like a premium product. |

Alternative: just call them **"Personal"** and **"Professional"**. Everyone understands that.

> [!TIP]
> In the App Store listing, lead with Executive: *"Your private AI executive assistant. Or, toggle to Companion mode and raise your own AI personality."* Lead with the money feature, reveal the fun feature.

### Pricing Analysis
| Tier | $15 Starter | $30 Pro | $50 Exec |
|---|---|---|---|
| vs ChatGPT Plus | $20/mo | Competitive | Premium feels right |
| vs Copilot for M365 | $30/user/mo (enterprise only) | Match | Undercuts enterprise pricing |
| vs Human assistant | $3,000+/mo | Nothing competes | Nothing competes |

**Assessment:** Pricing is solid. $50/mo for an AI that triages email and manages calendar is a steal compared to alternatives. The real question is: **do we offer a free tier for hosted, or is hosted always paid?**

**Recommendation:** No free hosted tier. Free = self-host. Hosted = paid, always. Free hosted users cost GPU money and never convert.

### MVP for Beta
The minimum that makes an exec say "holy shit":
1. ✅ Voice works ("Hey Luna, what's in my inbox?")
2. ✅ Email triage shows up (even read-only — just the summary is valuable)
3. ✅ Calendar shows today (even without rescheduling)
4. ❌ Documents can wait — email + calendar is the hook

**Cut documents from Sprint 8. Ship email + calendar read-only. Add document creation in Sprint 9.** The MVP is: voice → email triage → calendar view. That's the "holy shit" moment.

### Competitive Positioning
> [!WARNING]
> We're NOT competing with ChatGPT/Claude (general AI) or Copilot (enterprise bundle). We're competing with **the exec's current lack of any AI at all.** Most executives don't use AI today because it's too technical, too generic, or too public. We win by being: simple (voice), personal (companion), private (self-hosted option), and useful (email + calendar).

The danger of "spreading thin" is real but manageable. The companion layer UNIFIES everything — email, calendar, documents, and games all go through the same personality. That's the product thesis.

---

## UX Concerns

### Onboarding is Make-or-Break
The "I have a home PC" vs "Set up for me" fork in onboarding is CRITICAL. If the executive sees anything technical (IP addresses, port numbers, Tailscale), they'll uninstall.

**Hosted onboarding must be:** Email → password → "Setting up your AI..." (30 second animation) → "Meet Luna" → done. That's it. Zero configuration.

### Settings Screen Risk
Don't over-engineer settings. Most users never open settings. Make mode switching discoverable from the HOME screen (maybe a toggle in the header), not buried in settings.

### The "Coming Soon" Problem
If email/calendar APIs return 404 and we show "Coming soon," the exec just paid $50/mo for a chatbot. **Don't launch executive tier until email works.** Start tier: companion-only. Executive tier: behind a waitlist until email triage lands.

---

## Conversion Path

```
App Store listing (lead with executive)
    ↓
Download free app
    ↓
Onboarding: "Set up for me" (hosted)
    ↓
Free 7-day trial of Starter ($15/mo)
    ↓
Email triage wows them → upgrade to Pro ($30/mo)
    ↓
Calendar + docs → upgrade to Executive ($50/mo)
    ↓
Tell their VP of IT → enterprise deal
```

---

## Verdict

✅ **Proceed** — with these adjustments:
1. Rename modes: "Companion" / "Executive" (or Personal / Professional)
2. Cut documents from Sprint 8 — email + calendar is enough for the "holy shit" moment
3. No free hosted tier — free = self-host only
4. Don't show "Coming soon" — use a waitlist for executive features that aren't ready
5. Lead App Store listing with executive use case, reveal companion as the fun secret

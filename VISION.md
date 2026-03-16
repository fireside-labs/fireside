# 🔥 Fireside — Product Vision

> "Atlas stays home. Ember goes with you."

---

## The Core Concept

Every Fireside user has **two characters**:

| Character | Where It Lives | Brain | Role |
|---|---|---|---|
| **Your AI** | Home PC | 7B–35B LLM | The strategist. Runs the guild hall, processes everything, dreams overnight, handles complex tasks. |
| **Your Companion** | Your phone | 1–3B on-device LLM | The scout. Goes everywhere with you, handles basics, relays hard questions home. |

**The relationship:** Your AI is home. Your companion travels with you. When you need something big, your companion checks with your AI. When the PC is off, your companion does what it can on its own — smaller brain, big heart.

**The pitch to a friend:**
> "I've got an AI named Atlas who runs stuff at home, and a fox named Ember who follows me on my phone. When I ask Ember something hard, she checks with Atlas."

---

## Install Flow (install.sh)

```
Step 1: "What should we call you?"
  → Jordan

Step 2: "Choose a companion for your journey"
  → Every journey starts with a friend.
  → 🐱 Cat  🐶 Dog  🐧 Penguin  🦊 Fox  🦉 Owl  🐉 Dragon
  → Name: Ember

Step 3: "How powerful should your AI be?"
  → [1] Compact (3B) · [2] Smart & Fast (7B) · [3] Deep Thinker (35B)

Step 4: "Now, who's running the show at home?"
  → "Every companion has someone at the fireside.
     This is the mind behind Ember — your AI."
  → Name: Atlas
  → Style: Analytical / Creative / Direct / Warm
  → (generates human avatar for guild hall)

Step 5: Confirmation
  ┌─────────────────────────────┐
  │  Owner:      Jordan         │
  │  AI:         Atlas          │
  │  Companion:  🦊 Ember       │
  │  Brain:      Smart (7B)     │
  │  Location:   ~/.fireside    │
  └─────────────────────────────┘

Step 6: "Atlas and Ember are getting ready..."
  → Dashboard opens → Guild hall shows Atlas at the fireside, Ember curled up nearby
```

---

## Three-Tier Intelligence

### Tier 1: Companion Only (phone, no PC)
Your companion's small on-device brain handles:
- ✅ Chat (slower but works)
- ✅ Web browsing (phone has internet + small model summarizes)
- ✅ Guardian (time-check, sentiment, length check)
- ✅ Notes ("remember this for later")
- ✅ Translation (offline language pack)
- ✅ Calendar/Contacts (native iOS APIs)
- ✅ Messages ("tell Ann I'll be late")
- ❌ Complex research, pipelines, dream cycles, marketplace installs

### Tier 2: Companion + AI at Home (phone connected to PC)
Full power. The companion relays to your AI:
- ✅ Everything from Tier 1, but smarter (14B+ responses)
- ✅ Complex multi-step research via pipeline
- ✅ Dream cycle (overnight memory consolidation)
- ✅ Guild hall visualization (see your AI working)
- ✅ Marketplace installs
- ✅ Voice with Kokoro TTS quality

### Tier 3: Hosted Mode (always-on cloud)
For users without a home PC, or who want 24/7 uptime:
- ✅ Everything from Tier 2, always available
- ✅ "Atlas never sleeps"
- 💰 $15–50/month subscription

---

## The Sync Moment

When the companion reconnects to the home AI:

> **Ember:** "Atlas! I'm back. While we were out, Jordan asked me to remember 3 things, I stopped a late-night text, and I queued a research request about competitor pricing. Ready when you are."
>
> **Atlas:** "Got it. Processing the research now. I also dreamed about something interesting last night — want to hear?"

---

## Guild Hall Visualization

The desktop dashboard shows your AI and companion as characters in a themed hall:
- **5 themes:** Valhalla, Office, Space, Cozy, Dungeon
- **AI activities:** writing → at desk, researching → at library, building → at forge
- **Companion:** curled up by fire (idle), alert (task incoming), sleeping (PC off)
- **AI hurt/offline:** bandaged, lying by fire → node is down
- **10 activity animations** with theme-specific descriptions

---

## Competitive Moat

What makes Fireside uncopyable:

1. **Two-character system** — nobody else has an AI person + companion animal relationship
2. **On-device + home PC hybrid** — three tiers of intelligence, works offline
3. **Guild hall visualization** — infrastructure as a game, not a dashboard
4. **Privacy-first architecture** — runs on YOUR hardware, not someone else's cloud
5. **Companion personality evolution** — the AI grows, remembers, develops over months
6. **Marketplace ecosystem** — user-created themes, voices, personalities (30% cut)
7. **Brand identity** — campfire aesthetic, species-specific personalities, the warmth

The feature set can be replicated. The *feeling* can't. A fox that remembers your coffee order, guards your 2AM texts, and checks with Atlas when you need real help — that's a relationship, not a feature.

---

## Sprint Roadmap

| Sprint | Theme | Key Deliverables |
|---|---|---|
| 1–7 | ✅ Foundation → Hardening | 191 tests, full companion surface |
| 8 | ✅ Ship It | Settings, onboarding v2, theme overhaul, waitlist |
| 9 | ✅ Final Polish | Rich action cards, cross-context search, App Store fixes |
| **10** | **Two Characters** | Install flow v2 (AI person + companion), guild hall integration |
| **11** | **The Anywhere Bridge** | Connection Choice (Local/Tailscale/Cloud), embedded `tsnet` node |
| **12** | **Ember Goes Native** | iOS OS integration (Calendar, Health, Contacts, Siri, widgets, proactive alerts) |
| **13** | **On-Device Brain** | Small LLM on phone (1.5B), offline chat, smart routing to Atlas |
| **14** | **Hosted Mode** | RunPod containers, Supabase auth, subscription billing |
| **15** | **Marketplace v2** | Creator toolkit, IAP on mobile, $10K creator fund |

---

*"Day 1, it follows instructions. Day 90, it has instinct."*

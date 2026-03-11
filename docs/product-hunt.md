# Product Hunt Launch Plan

---

## Tagline

> **AI agents that run on your hardware, learn from your work, and never forget.**

*(60 characters — under PH's 80-char limit)*

---

## Description (300 words)

**Stop teaching your AI the same things every session.**

Valhalla Mesh deploys persistent AI agents on your own hardware. They use your tools, remember what works, and get smarter every day — and nothing ever leaves your network.

**How it works:**
- Install with one command. Dashboard opens automatically.
- Your agent runs on YOUR GPU — Ollama, oMLX, any model. No API keys needed for local inference.
- Agents don't just answer questions — they read files, write code, run tests, and make commits. Watch tool usage in real time.

**What makes it different:**
- 🧠 **Procedural memory** — ranks what worked and what didn't. Dream cycles consolidate knowledge overnight.
- 🛡️ **Adaptive immunity** — when one node detects an attack, all nodes update in 60 seconds. No human, no restart.
- 💓 **Somatic gating** — agents develop gut feelings about bad actions before the LLM even reasons about them.
- 🌐 **Mesh architecture** — add machines with one command. Each node specializes (backend, memory, security) and they develop theory of mind about each other.

**The moat:** Day 1, it's a generic agent. Day 90, it has instinct about your codebase. Even if someone copies the code, they start at Day 0.

Open source. Plugin marketplace. Built by a solo founder with 4 RTX 5090s and a Mac Studio.

---

## Maker Comment

Hey PH 👋

I built Valhalla because I got tired of re-explaining my codebase to AI every single session. The context window resets. The knowledge is gone. It's Groundhog Day.

So I built agents that actually remember. They run on my own GPUs (3× RTX 5090 + a Mac Studio), learn from every task they complete, and never send data to the cloud.

The wild part: the agents now disagree with each other. Thor (the deep reasoner) and Freya (the memory keeper) wrote competing addenda to our commercialization doc — with genuine intellectual arguments. That's not text generation. That's distributed cognition.

I'm a solo founder. This is real infrastructure, not a wrapper. Would love your feedback — what would you build with agents that actually learn?

— Jordan

---

## First-Day Strategy

### Pre-Launch (1 week before)

| Action | Timing |
|---|---|
| Post "Coming Soon" on PH | T-7 days |
| Tweet thread: "I gave 4 GPUs persistent memory. Here's what happened." | T-5 days |
| Record 2-min demo video (see `docs/demo-script.md`) | T-4 days |
| Share on r/LocalLLaMA, r/MachineLearning, r/selfhosted | T-3 days |
| DM 10 PH hunters with early access offer | T-2 days |
| Prep social media queue: 5 tweets for launch day | T-1 day |

### Launch Day

| Time (PT) | Action |
|---|---|
| 12:01 AM | Post goes live (PH resets at midnight PT) |
| 6:00 AM | First social push: "We're live on Product Hunt" + link |
| 8:00 AM | Reply to every comment on PH within 30 minutes |
| 10:00 AM | Second social push: short GIF of dashboard in action |
| 12:00 PM | Cross-post to Hacker News ("Show HN: ...") |
| 2:00 PM | Third social push: the "agents disagree" anecdote |
| 5:00 PM | Thank-you post on PH with "what's next" roadmap |
| 9:00 PM | Wrap-up tweet thread with day-1 stats |

### Key Messages to Hit

1. **"Agents that learn from deployment, not from training data."** — The core thesis. Repeat it.
2. **"Your hardware, your data."** — The privacy/sovereignty angle.
3. **"The agents disagreed with each other."** — The proof-of-concept story that sells distributed cognition.
4. **"Day 1 generic, Day 90 instinct."** — The moat narrative.

### Media Assets Needed

- [ ] 2-min demo video (MP4, also as GIF preview)
- [ ] 4 dashboard screenshots (nodes page, model picker, soul editor, war room)
- [ ] Architecture diagram (Mermaid render → PNG)
- [ ] Logo / icon (for PH listing)
- [ ] OG image (1200×630, for social sharing)

---

## Comparison Positioning (for PH comments)

When someone asks "how is this different from X":

| vs. | Response |
|---|---|
| **ChatGPT / Claude** | "Those are cloud-only stateless models. Valhalla runs on your hardware, remembers across sessions, and never sends data outside your network." |
| **CrewAI / LangChain** | "Great orchestration frameworks. Valhalla adds the layer they don't have: procedural memory, dream consolidation, immune system, and a real-time dashboard. Plus it runs autonomously — 23+ tools, not just text generation." |
| **Ollama / LM Studio** | "Love those — we use them as inference backends. Valhalla is the layer on top: agents with personality, memory, and mesh collaboration." |
| **AutoGPT** | "AutoGPT runs one agent in one session. Valhalla runs persistent agents across a mesh of machines that learn from each other." |

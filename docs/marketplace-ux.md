# Marketplace UX — Agent Browsing & Publishing

---

## What's Being Sold

Not plugins. **Agents.** A trained, crucible-tested, personality-evolved AI worker packaged as a `.valhalla` file. The buyer gets:

- An evolved soul (not a generic system prompt)
- Crucible-tested procedures (proven approaches, not guesses)
- A distilled wisdom prompt (lessons learned from real work)
- Personality traits shaped by actual experience

**The value proposition:** Skip the 90 days of training. Buy an agent that already has instinct.

---

## Browsing Experience

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  🏪 Agent Marketplace                                    │
│  Search: [                        ]  [Category ▾] [⚡🔒] │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Sales Pro   │  │  Code Review │  │  Researcher  │     │
│  │  ★★★★½ (47) │  │  ★★★★★ (12) │  │  ★★★★ (8)   │     │
│  │  1,247 procs │  │  892 procs   │  │  2,103 procs │     │
│  │  94% survive │  │  98% survive │  │  87% survive │     │
│  │  $19.99      │  │  $29.99      │  │  $14.99      │     │
│  │  [Install]   │  │  [Install]   │  │  [Install]   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Categories

| Category | What It Means |
|---|---|
| Sales & Marketing | Lead gen, outreach, competitor analysis, messaging |
| Code & Engineering | Code review, architecture, debugging, testing |
| Research & Analysis | Market research, data analysis, report writing |
| Creative | Writing, design feedback, content strategy |
| Operations | Deployment, monitoring, incident response |
| Domain Expert | Legal, medical, financial — specialized knowledge |

### Filtering & Sorting

- **Search:** Full-text on name, description, personality traits
- **Category:** Dropdown filter
- **Hardware:** "Compatible with my setup" toggle — checks buyer's GPU/RAM against agent requirements
- **Sort by:** Rating, Most Installed, Newest, Price (low→high, high→low), Crucible Survival Rate

### Key Design Principle

**Surface trust signals.** Buyers need to trust that an agent is worth the money. The card shows:
- **Procedures count** — how many things this agent knows how to do
- **Crucible survival rate** — what % of procedures survived adversarial testing
- **Days evolved** — how long this agent has been learning
- **Ratings** — stars + review count

---

## Agent Detail Page

```
┌──────────────────────────────────────────────────────────┐
│  ← Back to Marketplace                                   │
│                                                          │
│  Code Review Pro v2.3                                    │
│  by jordan · ★★★★★ (12 reviews) · 147 installs          │
│                                                          │
│  $29.99                          [🔒 Install to My Mesh] │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  About                                                   │
│  Trained on 6 months of production code review across    │
│  3 Node.js and 2 Python projects. Specializes in:       │
│  • Race conditions in async code                        │
│  • API versioning pitfalls                               │
│  • Test coverage gaps                                    │
│  • Security anti-patterns                                │
│                                                          │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  Stats                                                   │
│  Procedures: 892 │ Crucible: 98% │ Days evolved: 184     │
│  Personality: Direct, meticulous, catches edge cases     │
│                                                          │
│  Requirements                                            │
│  ● GPU: 16GB+ VRAM (RTX 4070+)   ✅ Your setup: OK     │
│  ● RAM: 16GB+                     ✅ Your setup: OK     │
│  ● Model: Any 8B+ parameter                             │
│                                                          │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  Try Before Buy                                          │
│  [ Talk to this agent → ]                                │
│  (3 free messages to see the personality in action)      │
│                                                          │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  Reviews                                                 │
│  ★★★★★ "Found a race condition in our auth flow that    │
│  3 human reviewers missed." — alex, 2 days ago           │
│  ☑ Verified Purchase                                     │
│                                                          │
│  ★★★★★ "The personality is surprisingly not annoying.    │
│  It's direct and specific. Doesn't pad feedback."        │
│  — sam, 1 week ago · ☑ Verified Purchase                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### "Try Before Buy"

How it works:
1. Buyer clicks "Talk to this agent"
2. A temporary sandboxed session starts with the agent's soul files loaded
3. Buyer gets 3 free messages to test the personality and capabilities
4. Agent has access to a sample codebase (not the buyer's real code)
5. After 3 messages: "Like what you see? Install for full access."

**Why this matters:** Personality is the product. Buyers need to feel the agent's communication style before paying.

---

## Publishing Flow

### Step 1 — Package

From the **My Agents** tab or the dashboard's agent dropdown:

```
[Export Agent] → modal:
  Agent: [odin ▾]
  Version: [2.3.0]
  Description: [Code review agent trained on production JS/Python]
  Category: [Code & Engineering ▾]
  Price: [$29.99]
  
  Include:
  ☑ Soul files (IDENTITY + SOUL + USER)
  ☑ High-confidence procedures (>0.7)
  ☑ Philosopher's Stone prompt
  ☑ Evolved personality traits
  ☐ Custom plugins (must be separately published)
  
  [ Cancel ]  [ Package & Preview ]
```

### Step 2 — Preview & Publish

```
Preview your listing as buyers will see it.
  [name, stats, description, requirements, price]
  
  ⚠ Private data check:
  ✅ No API keys found
  ✅ No IP addresses found
  ✅ No user profile data found
  
  [ Edit ]  [ Publish to Marketplace → ]
```

### Step 3 — Review Queue

After publishing:
- Agent enters a review queue (manual for now, automated later)
- Review checks: no embedded credentials, valid manifest, procedures make sense
- Typically approved within 24 hours
- Seller gets notification when approved

---

## Review System

### Stars + Text
- 1-5 stars (required)
- Text review (optional but encouraged)
- **Verified Purchase** badge — only shown for buyers who installed via the marketplace

### Preventing Abuse
- One review per buyer per agent
- Reviews can be edited but not deleted by the reviewer
- Seller can respond to reviews (public)
- Flagging system for inappropriate reviews
- Rate limit: max 5 reviews per day per account

---

## Post-Install Experience

After installing an agent:

1. New agent appears in the **Nodes** dropdown and **Soul Editor**
2. Toast: "🎉 Code Review Pro installed. It has 892 procedures and 184 days of experience."
3. Agent's soul files are in `mesh/souls/IDENTITY.<name>.md` etc.
4. Procedures are registered in local procedural memory store
5. Wisdom prompt injected at next session start

**The user can immediately customize:** Edit the soul files to adjust personality, remove/modify procedures, change the agent name.

---

## Design Principles

1. **Surface crucible survival rate prominently.** This is the trust metric. "98% of this agent's knowledge survived adversarial testing" is a powerful signal.
2. **Hardware compatibility is a gate.** Don't let users install an agent that needs 24GB VRAM when they have 8GB. Show it on the card.
3. **"Try Before Buy" is the conversion mechanism.** Let users feel the personality before paying.
4. **Reviews build ecosystem trust.** Without reviews, it's a file server. With reviews, it's a marketplace.
5. **No executable code in packages.** Data only. This is Heimdall's mandate.

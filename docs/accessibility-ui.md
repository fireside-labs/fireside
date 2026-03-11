# Accessibility-First UI Spec

> **Design target:** A 60-year-old retired teacher who uses a Mac to email, browse, and do video calls. She wants AI help writing letters and organizing files. She has never seen a terminal, doesn't know what YAML is, and will close the app if she feels confused for more than 10 seconds.

> **Rule:** If she can't figure it out without reading documentation, we failed.

---

## Design Principles

1. **Goals, not mechanisms.** Show what the user can DO, not how the system WORKS.
2. **One concept per screen.** Never show two unfamiliar things at the same time.
3. **Progressive disclosure.** Simple by default, advanced on demand. The "power user" toggle is always there but never in the way.
4. **No jargon.** Every label gets the grandparent test. If a 65-year-old wouldn't understand it in context, rewrite it.
5. **Undo everything.** Every action should be reversible. No "are you sure?" dialogs — just undo buttons.
6. **Large click targets.** Minimum 44×44px for all interactive elements. Fingers are bigger than cursors.
7. **High contrast.** The dark theme is gorgeous but text contrast needs to be WCAG AA minimum (4.5:1 for body text).

---

## Sidebar Navigation — Before & After

### Before (Current)
```
⚡ Valhalla
  Mission Control

  ⬡  Nodes
  ⚡  Models
  🔄  Pipeline
  🧪  Crucible
  🗣️  Debates
  🜂  Soul Editor
  ⚙  Config
  ⬢  Plugins
  🏪  Marketplace
  ⚔  War Room
```

**Problem:** 10 flat items. No grouping. Jargon-heavy. A non-technical user doesn't know the difference between "Nodes" and "Config" or why "Crucible" matters.

### After (Proposed)
```
⚡ Valhalla
  Your AI: odin ✅ Online

  ── Your AI ──
  💬  Chat
  🧠  Personality
  📱  Connected Devices

  ── Tools ──
  📋  Task Builder
  📊  How It's Learning

  ── Settings ──
  ⚙  Settings
  🧩  Add-ons
  🏪  Store
```

**Changes:**
| Old | New | Why |
|---|---|---|
| "Mission Control" homepage | "Chat" as first item | Chat is what people DO. Make it primary. |
| "Nodes" | "Connected Devices" | Normal people call them devices, not nodes. |
| "Models" | Moved inside Settings | Model choice is a setting, not a daily action. |
| "Pipeline" | "Task Builder" | "Pipeline" is developer jargon. |
| "Crucible" + "War Room" + "Debates" | "How It's Learning" | One page that combines all cognitive visibility. |
| "Soul Editor" | "Personality" | Everyone understands personality. |
| "Config" | "Settings" | Universal UI convention. |
| "Plugins" | "Add-ons" | Chrome uses "extensions," we can use "add-ons." |
| "Marketplace" | "Store" | Everyone knows what a store is. |

**Key reduction:** 10 items → 7 items. Three cognitive pages (Crucible, War Room, Debates) merge into one "How It's Learning" overview.

---

## Page-by-Page Rewrite

### 1. Chat (was: Home / Mission Control)

**Current:** Dashboard showing stat cards, quick action tiles, and a chat input at the bottom. Stat cards show "Nodes Online," "Active Model," "Uptime," "Plugins Loaded."

**Problem:** Stat cards mean nothing to a non-technical user. "Uptime: 4h 23m" — so what? "Plugins Loaded: 5" — what's a plugin?

**Proposed:**

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  Hi Jordan 👋                                        │
│                                                      │
│  Your AI is ready. What can I help you with?         │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │  Type a message...                    [Send]  │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  Try asking:                                         │
│  "Summarize my emails from this week"                │
│  "Help me write a thank-you letter"                  │
│  "What files did I work on yesterday?"               │
│                                                      │
│                                                      │
│  ── What your AI did today ──                        │
│  ✅ Answered 12 questions                            │
│  📁 Read 3 files                                    │
│  🧠 Learned 2 new things                            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Key changes:**
- Chat is the FIRST thing. Not stats. Not tiles.
- Suggested prompts in plain English (not "talk to your agent")
- "What your AI did today" replaces stat cards — shows *outcomes*, not metrics
- No "Uptime," "VRAM," or "Plugins Loaded" — those go in Settings for power users
- Large input field with visible Send button (not just Enter key)

---

### 2. Personality (was: Soul Editor)

**Current:** Split-pane markdown editor with IDENTITY/SOUL/USER tabs showing raw markdown.

**Problem:** A non-technical user sees `## Core Traits` and `**Think deep, not fast.**` and has no idea this is the AI's personality file. It looks like broken formatting.

**Proposed:**

```
┌──────────────────────────────────────────────────────┐
│  🧠 Personality                                      │
│  Change how your AI talks and what it's good at.     │
│                                                      │
│  ── Name & Identity ──                               │
│  Name:        [ Odin                    ]            │
│  Role:        [ Your main assistant  ▾  ]            │
│  Tone:        ○ Casual  ● Friendly  ○ Professional   │
│                ○ Direct  ○ Playful                    │
│                                                      │
│  ── What it's good at ──                             │
│  ☑ Writing & editing                                 │
│  ☑ Answering research questions                      │
│  ☐ Writing code                                      │
│  ☐ Sales & outreach                                  │
│  ☐ Data analysis                                     │
│  [+ Add a custom skill]                              │
│                                                      │
│  ── Boundaries ──                                    │
│  Things your AI should NEVER do:                     │
│  [ Don't share my personal information              ]│
│  [ Always ask before deleting files                 ]│
│  [+ Add rule]                                        │
│                                                      │
│  ── Advanced ──                                      │
│  [📝 Edit raw personality files]                     │
│  (For power users — edit the SOUL, IDENTITY,         │
│   and USER files directly in markdown)               │
│                                                      │
│  [Save Changes]                                      │
└──────────────────────────────────────────────────────┘
```

**Key changes:**
- Form-based input replaces raw markdown
- "Tone" is radio buttons, not a paragraph in a soul file
- Skills are checkboxes, not bullet points in markdown
- Boundaries are plain-English sentences, not `## Boundaries` sections
- "Edit raw personality files" is collapsed under "Advanced" — power users find it, normal users never see it
- Behind the scenes: form values generate SOUL.md / IDENTITY.md / USER.md

---

### 3. Connected Devices (was: Nodes)

**Current:** Grid of node cards showing name, role, status, model, uptime. Technical: "orchestrator," "backend," "100.117.255.38."

**Problem:** "What's an orchestrator?" "Why do I care about an IP address?"

**Proposed:**

```
┌──────────────────────────────────────────────────────┐
│  📱 Connected Devices                                │
│  Your AI runs on these devices.                      │
│                                                      │
│  ┌────────────────────────────┐                      │
│  │  💻 Jordan's MacBook       │ ✅ Online            │
│  │  Running: Odin (main AI)   │                      │
│  │  AI Memory: 16 GB          │                      │
│  │  Connected since: 2 days   │                      │
│  └────────────────────────────┘                      │
│                                                      │
│  ┌────────────────────────────┐                      │
│  │  🖥️ Living Room PC         │ ✅ Online            │
│  │  Running: Thor (helper)    │                      │
│  │  AI Memory: 32 GB          │                      │
│  │  Connected since: 5 days   │                      │
│  └────────────────────────────┘                      │
│                                                      │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐                      │
│  │  + Add another device      │                      │
│  │  Make your AI faster by    │                      │
│  │  adding a second computer  │                      │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘                      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Key changes:**
- "Jordan's MacBook" not "odin." Name the hardware, not the agent.
- "AI Memory: 16 GB" not "VRAM: 16384 MB"
- No IP addresses visible (they're in Settings → Advanced)
- "Connected since" not "Uptime: 48h 12m"
- "Role" names replaced: "main AI," "helper," "memory assistant" — not "orchestrator," "backend," "memory"
- "Add another device" card is always visible as an inviting CTA, not a small button

---

### 4. Settings (was: Config Editor)

**Current:** Raw YAML textarea with line numbers. One wrong indent breaks everything.

**Problem:** Non-technical users literally cannot use this.

**Proposed:**

```
┌──────────────────────────────────────────────────────┐
│  ⚙ Settings                                         │
│                                                      │
│  ── Your AI ──                                       │
│  Name:              [ Odin                    ]      │
│  Role:              [ Main Assistant       ▾  ]      │
│                                                      │
│  ── AI Brain ──                                      │
│  Current brain:     [ Smart & Fast (8B)    ▾  ]      │
│                                                      │
│  Available brains:                                   │
│  ┌────────────────────────────────────────────┐      │
│  │ ⚡ Smart & Fast (8B)           FREE        │ ● ←  │
│  │    Best for quick questions and chat.       │      │
│  ├────────────────────────────────────────────┤      │
│  │ 🧠 Deep Thinker (35B)          FREE        │ ○    │
│  │    Best for complex analysis. Needs 24GB   │      │
│  │    AI Memory. You have: 16GB ⚠️             │      │
│  ├────────────────────────────────────────────┤      │
│  │ 🌙 Cloud Expert (Kimi)         PAID        │ ○    │
│  │    128K memory window. Great for reading   │      │
│  │    long documents. Needs internet.          │      │
│  └────────────────────────────────────────────┘      │
│                                                      │
│  ── Add-ons ──                                       │
│  Model Switching      [  ON  ]  Switch brains by     │
│                                 just asking           │
│  Watchdog              [  ON  ]  Auto-restarts if     │
│                                 something breaks      │
│  Daily Summary         [ OFF ]  Morning email of      │
│                                 what happened          │
│                                 overnight              │
│                                                      │
│  ── Advanced ──                                      │
│  [📝 Edit raw config file (valhalla.yaml)]           │
│                                                      │
│  [Save]                                              │
└──────────────────────────────────────────────────────┘
```

**Key changes:**
- Form fields replace YAML. Name, role, brain (model) as dropdowns.
- "Brain" not "Model." Normal people understand "brain."
- Each brain option has: emoji, name, FREE/PAID badge, one-line explanation, hardware compatibility check
- Add-ons are toggle switches with one-line descriptions — not a YAML list
- Incompatible options show ⚠️ with *why* ("You have 16GB. This needs 24GB.")
- Raw YAML is hidden under "Advanced" — always accessible, never default

---

### 5. Task Builder (was: Pipeline)

**Current:** Pipeline list with iteration counts, stage names (Spec, Build, Test), and "Force Advance" buttons.

**Problem:** "Pipeline" is meaningless. "Iteration 3/10" is meaningless. "Stage: Test · Agent: heimdall" is meaningless.

**Proposed:**

```
┌──────────────────────────────────────────────────────┐
│  📋 Task Builder                                     │
│  Give your AI a job. It'll work on it step by step.  │
│                                                      │
│  [+ Create New Task]                                 │
│                                                      │
│  ── Active ──                                        │
│  ┌────────────────────────────────────────────┐      │
│  │  📝 "Write a privacy policy for my website" │      │
│  │                                              │      │
│  │  Progress: ▓▓▓▓▓▓▓▓░░░░░░░░░  Step 3 of 7   │      │
│  │  Status: Checking quality...                 │      │
│  │  Time so far: 8 minutes                      │      │
│  │                                              │      │
│  │  [View Details]  [Pause]  [Cancel]           │      │
│  └────────────────────────────────────────────┘      │
│                                                      │
│  ── Completed ──                                     │
│  ┌────────────────────────────────────────────┐      │
│  │  ✅ "Organize my family photos by year"     │      │
│  │  Finished in 23 min · 4 steps               │      │
│  │  Lesson learned: "Photos without dates go   │      │
│  │  in an 'Unsorted' folder"                   │      │
│  │                                     [View]  │      │
│  └────────────────────────────────────────────┘      │
│                                                      │
│  ── Needs Your Help ──                               │
│  ┌────────────────────────────────────────────┐      │
│  │  ⚠️ "Update the tax spreadsheet"            │      │
│  │  Your AI got stuck and needs guidance.       │      │
│  │  "I found two different tax rate tables.     │      │
│  │   Which one should I use?"                   │      │
│  │                                              │      │
│  │  [Help Your AI]  [Cancel Task]               │      │
│  └────────────────────────────────────────────┘      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Key changes:**
- "Pipeline" → "Task." Everyone knows what a task is.
- "Iteration 3/10" → "Step 3 of 7." Human language.
- "Stage: Test" → "Checking quality." Describe the *action*, not the *stage name*.
- "Escalated" → "Needs Your Help." Warm, specific.
- The escalation message shows WHAT the AI needs, not technical details
- "Lesson learned" shown on completed tasks — reinforces that the AI grew

### Create New Task wizard:

```
┌──────────────────────────────────────────────────────┐
│  What do you want your AI to do?                     │
│                                                      │
│  [ Write a blog post about our company rebrand      ]│
│                                                      │
│  How important is quality vs speed?                  │
│  Speed ○───○───●───○───○ Quality                     │
│  (Fewer checks,        (More checking,               │
│   faster result)        better result)               │
│                                                      │
│  If the AI gets stuck, how should I tell you?        │
│  ● Show a notification in the dashboard              │
│  ○ Send me a text message                            │
│  ○ Just keep trying                                  │
│                                                      │
│  [Cancel]                      [Start Task →]        │
└──────────────────────────────────────────────────────┘
```

**No mention of:** iterations, max iterations, stages, agents, models, tokens, budgets.
The quality slider maps to max_iterations internally (Speed=3, Balanced=7, Quality=15).

---

### 6. How It's Learning (was: War Room + Crucible + Debates)

Three pages merged into one. Non-technical users don't need to understand the separate systems — they need to see one answer: "Is my AI getting smarter?"

**Proposed:**

```
┌──────────────────────────────────────────────────────┐
│  📊 How It's Learning                                │
│  Your AI learns from every task. Here's what it      │
│  knows and how reliable that knowledge is.           │
│                                                      │
│  ── Overall ──                                       │
│  🧠 Things it knows:              247                │
│  ✅ Reliable knowledge:           231 (94%)          │
│  📈 Getting smarter:              Yes — improved     │
│                                   12% this week      │
│                                                      │
│  ── Recent discoveries ──                            │
│  💡 "Your emails are usually shorter on Fridays"     │
│      Confidence: ████████░░ 82% · Discovered 2d ago  │
│  💡 "Your spreadsheets always have headers in row 1" │
│      Confidence: ██████████ 97% · Discovered 5d ago  │
│  💡 "You prefer bullet points over paragraphs"       │
│      Confidence: ███████░░░ 71% · Discovered 1d ago  │
│                                                      │
│  ── Last night's learning ──                         │
│  🌙 Your AI reviewed yesterday's work at 3:00 AM    │
│  🧪 Tested 247 things it knows — 16 were weak,      │
│     so it studied more.                              │
│  💎 Updated its "big picture" understanding          │
│     of how you work.                                 │
│                                                      │
│  ── Advanced ──                                      │
│  [View hypotheses] [View knowledge tests]            │
│  [View debates] [View raw data]                      │
└──────────────────────────────────────────────────────┘
```

**Key changes:**
- One page instead of three
- "Things it knows" not "Procedures"
- "Reliable knowledge" not "Crucible survival rate"
- "Getting smarter" is a YES/NO with a simple % change
- "Recent discoveries" are hypotheses written in plain English — not formulas
- "Last night's learning" is a 3-line story of the overnight cycle — not three separate system pages
- Advanced links go to the detailed War Room / Crucible / Debate views for power users

---

### 7. Store (was: Marketplace)

**Current labels:** "Crucible survival rate: 98%," "892 procedures," "184 days evolved"

**Proposed labels:** "Reliability: 98%," "Knows 892 things," "6 months of training"

```
┌──────────────────────────────────────────────────────┐
│  🏪 Store                                            │
│  Pre-trained AI assistants ready to use.             │
│                                                      │
│  ┌────────────────────────────────────────────┐      │
│  │  ✍️ Writing Pro                             │      │
│  │  ★★★★½ (47 reviews) · 6 months trained     │      │
│  │  "Great at editing, catches grammar and     │      │
│  │   tone issues. Feels like a real editor."   │      │
│  │  Reliability: 94%  ·  Knows 1,247 things   │      │
│  │  Works with your device: ✅                 │      │
│  │  FREE                        [Install]      │      │
│  └────────────────────────────────────────────┘      │
│                                                      │
│  ┌────────────────────────────────────────────┐      │
│  │  📊 Research Assistant                      │      │
│  │  ★★★★★ (12 reviews) · 4 months trained     │      │
│  │  "Finds relevant info fast. Good at         │      │
│  │   summarizing long documents."              │      │
│  │  Reliability: 98%  ·  Knows 892 things     │      │
│  │  Works with your device: ✅                 │      │
│  │  $14.99                      [Install]      │      │
│  └────────────────────────────────────────────┘      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Onboarding Wizard

This is the most important screen in the entire product. If this fails, nothing else matters.

### Screen 1 — Welcome
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│                      ⚡                               │
│                                                      │
│            Welcome to Valhalla                       │
│                                                      │
│  Your own AI assistant that runs on this computer,   │
│  learns from your work, and never forgets.           │
│                                                      │
│  Let's set it up. Takes about 2 minutes.             │
│                                                      │
│              [Get Started →]                         │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Screen 2 — Name
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  What's your name?                                   │
│                                                      │
│  [ Jordan                                    ]       │
│                                                      │
│  Your AI will use this to personalize                │
│  conversations with you.                             │
│                                                      │
│  [← Back]                          [Next →]          │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Screen 3 — AI Brain (auto-detected)
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  We checked your computer. Here's what we found:     │
│                                                      │
│  💻 MacBook Pro                                      │
│  🧠 Apple M2 Pro — 16 GB AI Memory                  │
│                                                      │
│  Recommended brain:                                  │
│  ⚡ Smart & Fast (Llama 3.1, 8B)                    │
│  Perfect for everyday questions and tasks.           │
│                                                      │
│  ✅ This works great with your computer.             │
│                                                      │
│  [← Back]              [Use this brain →]            │
│                                                      │
│  ───────────────────────────────────────              │
│  Want a different brain? [See all options]            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Screen 4 — Personality
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  How should your AI talk to you?                     │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 😊       │  │ 💼       │  │ ⚡       │          │
│  │ Friendly │  │ Formal   │  │ Direct   │          │
│  │          │  │          │  │          │          │
│  │ Warm,    │  │ Polite,  │  │ Short,   │          │
│  │ chatty,  │  │ proper,  │  │ no fluff,│          │
│  │ uses     │  │ no slang │  │ gets to  │          │
│  │ emoji    │  │          │  │ the point│          │
│  └──────────┘  └──────────┘  └──────────┘          │
│       ●              ○              ○                │
│                                                      │
│  You can change this anytime in Personality.         │
│                                                      │
│  [← Back]                          [Next →]          │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Screen 5 — Ready
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│                      ✅                               │
│                                                      │
│          You're all set, Jordan!                      │
│                                                      │
│  Your AI is named Odin. It's Friendly, runs the     │
│  Smart & Fast brain, and it's ready to help.         │
│                                                      │
│  It'll get smarter every day as it learns            │
│  how you work.                                       │
│                                                      │
│  [Start chatting →]                                  │
│                                                      │
│                                                      │
│  💡 Tip: Try asking "What can you help me with?"    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Total screens: 5. Total time: ~90 seconds.** No terminal. No YAML. No model names.

---

## Master Terminology Map

This is the translation table. Every developer term on the left gets replaced with the human term on the right across the entire dashboard.

| Developer Term | Human Term | Where Used |
|---|---|---|
| Node | Device | Everywhere |
| Mesh | Connected devices | Sidebar, pages |
| Model | Brain | Settings, picker |
| VRAM | AI Memory | Device cards, settings |
| Plugin | Add-on | Settings, store |
| Pipeline | Task | Task builder |
| Iteration | Step | Task progress |
| Stage | (describe the action) | "Checking quality" not "Stage: Test" |
| Escalated | Needs your help | Task cards |
| Soul file | Personality | Sidebar, editor |
| SOUL.md / IDENTITY.md | (hidden) | Only in Advanced view |
| Config / valhalla.yaml | Settings | Sidebar, page |
| Hypothesis | Discovery | Learning page |
| Procedural memory | Things it knows | Learning page |
| Crucible | Knowledge check | Learning page (advanced) |
| Crucible survival rate | Reliability | Store, learning page |
| Dream consolidation | Overnight learning | Learning page |
| Philosopher's Stone | Big picture understanding | Learning page |
| Somatic gating | Gut check | (keep hidden unless triggered) |
| Belief shadow | (remove from UI) | Too abstract for non-technical |
| War Room | How It's Learning | Sidebar |
| Event bus | (hidden) | Internal only |
| Token | (hidden) | Never show to normal users |
| Inference | (hidden) | Internal only |
| API | (hidden) | Internal only |
| YAML | (hidden) | Only in Advanced view |
| Orchestrator | Main AI | Device role |
| Backend | Helper | Device role |
| Memory | Memory assistant | Device role |
| Security | Security guard | Device role |
| Hot-reload | Changes apply immediately | Settings page |
| WebSocket | (hidden) | Internal only |

---

## Implementation Priority (for Freya)

### Must-have (before launch)
1. **Onboarding wizard** — 5 screens, no terminal
2. **Settings form view** — replace YAML default with forms
3. **Personality form** — replace raw markdown with guided input
4. **Terminology rename** — apply the master map across all pages
5. **Chat as homepage** — make the chat input the primary landing

### Should-have (first update)
6. **Merge cognitive pages** — War Room + Crucible + Debates → "How It's Learning"
7. **Sidebar grouping** — 3 sections with headers
8. **Device cards** — friendly names, no IPs
9. **Task Builder** — replace Pipeline jargon with plain language
10. **Store relabeling** — "Reliability" not "Crucible survival rate"

### Nice-to-have (later)
11. **Keyboard shortcuts** — Ctrl+S, Ctrl+Enter
12. **Font size toggle** — accessibility for older eyes
13. **High contrast mode** — beyond default dark theme
14. **Screen reader support** — ARIA labels on all interactive elements
15. **Tutorial tooltips** — first-time hover explanations that auto-dismiss

---

## The Test

After implementing this spec, run this test:

**Find a non-technical person (parent, neighbor, friend who doesn't code). Sit them in front of the dashboard. Say nothing. Watch.**

- Can they start a conversation with the AI in under 30 seconds? → **Chat page test**
- Can they change the AI's name? → **Personality page test**
- Can they understand what the AI learned last night? → **Learning page test**
- Can they add a device? → **Connected Devices test**
- Can they create a task? → **Task Builder test**

If they ask "what does [X] mean?" for any visible label, that label needs to be rewritten.

**The bar:** Every screen should be as intuitive as the iPhone Settings app.

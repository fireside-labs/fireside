# Demo Video Script — 3 Minutes

---

## Format

- **Length:** 3:00 flat
- **Style:** Screen recording with voiceover. No face cam. Dark terminal + dashboard.
- **Music:** Low ambient synth, fades under voiceover
- **Resolution:** 1920×1080, 60fps

---

## Script

### [0:00–0:10] Hook

*Screen: black with ⚡ Valhalla logo fade-in*

**VO:** "What if your AI remembered what it learned yesterday?"

*Logo pulses once, fades to terminal*

---

### [0:10–0:30] Install & Launch

*Screen: terminal, clean dark theme*

**VO:** "One command to install. One command to start."

```
$ brew install valhalla
$ valhalla init
$ valhalla start
```

*Show actual terminal output — green checkmarks cascading, Bifrost starting, "Opening dashboard..." message*

**VO:** "Your agent is live. Running on your GPU. Nothing leaves your machine."

*Browser opens to dashboard — Mission Control with the node card glowing green*

---

### [0:30–0:55] The Agent Does Real Work

*Screen: dashboard chat input*

**VO:** "This isn't a chatbot. Ask it to do something real."

*Type: "Read my last 5 git commits and summarize what I was working on"*

*Show:*
- Node card pulses while thinking
- Tool usage appears: 🔧 git_log, 🔧 file_read
- Response streams in with actual commit analysis

**VO:** "It read your git history. It analyzed your code. It used real tools on your real files — all running locally."

*Quick cut to: token count + "0 API calls" indicator*

---

### [0:55–1:10] The Soul System

*Screen: dashboard Soul Editor page*

**VO:** "Every agent has a personality. Not a system prompt — a soul."

*Show: SOUL.md for Thor, split-pane editor with personality traits on the left, rendered preview on the right*

**VO:** "Identity. Personality. Boundaries. Cognitive systems. Change the soul, change the behavior — same model, completely different agent."

*Click between IDENTITY / SOUL / USER tabs*

---

### [1:10–1:25] The Mesh

*Screen: dashboard Nodes page*

**VO:** "One machine is an agent. Multiple machines are a mesh."

*Show: 3–4 node cards, each with different roles and models, green status indicators pulsing*

**VO:** "Each node specializes. Thor reasons deep on a 5090. Freya manages memory. Heimdall watches for threats."

*Click "Add Node" — show the one-line command appear*

**VO:** "Add a machine with one command. It appears in the dashboard in 30 seconds."

---

### [1:25–2:10] The Pipeline — Watch It Build

*Screen: dashboard Pipeline page*

**VO:** "Now the part that changes everything. Ask it to build something."

*Click "+ New Pipeline". Fill in: title = "Add JWT auth to the API", max iterations = 10. Click "Create Pipeline".*

*Show: pipeline card appears with status "Running"*

**VO:** "The pipeline writes a spec using a cloud model. Then builds using a local model — for free."

*Click into the pipeline detail view. Show:*
- Stage timeline: Spec ✔ → Build 🔄 → Test ○ → Distill ○
- Iteration counter: "Iteration 1"
- Real-time log output streaming

**VO:** "Tests run automatically. First iteration: 6 failures."

*Show: iteration card — "6 tests failed. Missing JWT secret, bcrypt import error."*

*Cut to: iteration 2 appearing, build stage running again*

**VO:** "It reads the failures, writes a fix brief, and rebuilds. No human needed."

*Show: iteration 2 verdict — "PROGRESS. 4 of 6 fixed."*

*Cut to: iteration 4, all tests green*

**VO:** "Four iterations later — all 18 tests passing."

*Show: Socratic review panel appearing — three reviewer personas debating*

**VO:** "Then three reviewers debate it. An architect, a devil's advocate, and an end user — each with their own model."

*Consensus meter fills to 85%*

*Show: completion screen — "7 iterations, 34 minutes, 89,000 local tokens (free), 12,000 cloud tokens"*

**VO:** "Lessons learned: 'JWT refresh needs a mutex.' Stored in memory. The next pipeline starts smarter."

---

### [2:10–2:35] The Overnight Loop

*Screen: dashboard War Room page*

**VO:** "Here's the part nobody else has."

*Show: hypotheses table with confidence bars, prediction accuracy chart, self-model card*

**VO:** "Every night at 3 AM, your agents dream. They compress the day's experiences into principles."

*Show: Mermaid diagram of overnight cycle — Dream → Crucible → Philosopher's Stone → Wake Up Smarter*

**VO:** "At 4:45, the Crucible stress-tests everything they know. 'What if the server is down? What if the input is empty?'"

*Show: crucible results — ✅ unbreakable, ❌ broken, ⚠️ stressed*

**VO:** "Knowledge that breaks gets fixed. Knowledge that survives gets promoted."

*Show: a somatic gating event — node blocking an action with negative valence*

**VO:** "Day 90: it has gut feelings. It blocked a bad deployment before the model even started reasoning. Because it remembered the last three times that pattern failed."

---

### [2:35–2:50] The Moat

*Screen: dark, text appearing line by line*

**VO:** "Day 1, it follows instructions."

*Pause*

**VO:** "Day 90, it has instinct."

*Pause*

**VO:** "Even if someone copies every line of code, they start at Day 0. Your 90 days of accumulated intelligence is the moat — and it deepens every day the system runs."

---

### [2:50–3:00] Close

*Screen: fade to dark with tagline*

**VO:** "Valhalla Mesh. AI that runs on your hardware, learns from your work, and never forgets."

*Show:*
```
brew install valhalla
valhalla start
```

*Text: "Open source. Free to start. valhalla.dev"*

*⚡ logo. Fade to black.*

---

## Production Notes

### Key Shots to Capture
1. Terminal: `valhalla start` with cascading green checkmarks
2. Dashboard: node card green pulse animation
3. Dashboard: agent using tools in real-time (git_log, file_read visible)
4. Soul Editor: split-pane with Thor's SOUL.md
5. Nodes page: 3+ node cards with active status
6. Add Node modal: one-line command
7. **Pipeline page: wizard, stage timeline, iterations streaming live**
8. **Socratic debate: three reviewer personas, consensus meter filling**
9. **Completion screen with cost breakdown + lessons learned**
10. War Room: hypothesis confidence bars + prediction chart
11. **Crucible results: unbreakable/broken/stressed badges**
12. Somatic gating: action-blocked toast/indicator

### Voiceover Style
- Calm, confident, slightly awed at the right moments
- Not salesy. Let the product speak. The VO just narrates what's happening on screen.
- Pauses after key claims to let them land
- The pipeline section should feel like watching something alive iterate — slightly faster pacing

### Cuts
- Every shot is 3–5 seconds max
- No lingering. Movement on every frame — typing, scrolling, animations.
- Transition between dashboard pages with the actual sidebar click animation
- **Pipeline section uses quick cuts between iterations** — show the number incrementing, tests going from red to green

### Music
- Ambient electronic. Think: Tycho, Carbon Based Lifeforms
- Stays underneath VO. Swells slightly at [2:35] moat section.
- Slight tempo increase during pipeline iteration montage
- No beats — this isn't a hype reel, it's a "watch this and be quietly impressed" video

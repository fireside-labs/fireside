# Onboarding: Zero to "Holy Shit" in 5 Minutes

---

## The Promise

A brand new user — never heard of Valhalla — should go from `brew install` to watching an AI agent **do real work on their machine** in under 5 minutes. Not a chatbot. Not a demo. Their agent, running locally, completing a task they gave it.

---

## Minute 0:00 — Install

One command. No prerequisites beyond Python 3.11+ and a GPU.

```bash
brew install valhalla
```

That's it. No Docker, no virtual environments, no 14-step guide. The formula installs:
- Valhalla Core (Bifrost server + plugin runtime)
- Dashboard (pre-built Next.js bundle)
- CLI (`valhalla`)
- Default plugins: model-switch, watchdog, working-memory

> **Linux/WSL:** `curl -fsSL https://get.valhalla.dev | bash`

---

## Minute 0:30 — Init

```bash
valhalla init
```

This is **not** a 20-question wizard. Four prompts, sensible defaults, done:

```
⚡ Valhalla

  Node name [odin]:
  >

  Inference: auto-detected Ollama (llama3.1:8b) ✔
  Use this? [Y/n]:
  >

  ✔ valhalla.yaml created
  ✔ Soul files generated
  ✔ Plugins enabled: model-switch, watchdog, working-memory

  Run: valhalla start
```

**Design rules:**
- Auto-detect the inference engine (Ollama, oMLX, LM Studio). Don't ask the user to configure it.
- Auto-detect the GPU. Don't ask them to pick a model that fits — pick one for them based on VRAM.
- Default node name = system hostname. Default role = `standalone`.
- If there's nothing to ask, don't ask. `valhalla init --yes` skips all prompts.

---

## Minute 1:00 — Start

```bash
valhalla start
```

```
⚡ Valhalla — odin

  Bifrost       http://localhost:8765  ✔
  Dashboard     http://localhost:3000  ✔
  Model         llama3.1:8b (local)   ✔
  Plugins       3 loaded              ✔

  Opening dashboard...
```

The browser opens automatically. No URL to copy. No port to remember.

---

## Minute 1:15 — The Dashboard

The user lands on **Mission Control** — a single page, not a nav maze.

```
┌──────────────────────────────────────────────┐
│  ⚡ VALHALLA          odin · online · 0:02  │
├──────────────────────────────────────────────┤
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  🟢 odin                              │  │
│  │  llama3.1:8b · standalone             │  │
│  │  GPU: RTX 5090 · VRAM: 12/32 GB      │  │
│  │  ████████████░░░░░░░░░  38%           │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  💬 Talk to your agent                │  │
│  │                                        │  │
│  │  > _                                   │  │
│  │                                        │  │
│  └────────────────────────────────────────┘  │
│                                              │
└──────────────────────────────────────────────┘
```

**Design rules:**
- Node card is front and center. The user immediately sees that something is alive and running.
- VRAM bar gives them hardware confidence — they know they're not wasting their GPU.
- The chat input is right there. Not behind a "Chat" tab. Not on another page. Right. There.
- The entire page has maximum 2 glassmorphism cards. No feature overload on first load.

---

## Minute 1:30 — The "Holy Shit" Moment

The chat input has a ghost prompt:

```
Try: "Read my last 3 git commits and tell me what I was working on"
```

The user types something. The agent responds. But here's what makes this different from ChatGPT:

1. **The node card pulses** while the agent is thinking — a soft neon glow that breathes.
2. **The response streams** token by token, but the node card shows real-time stats: tokens/sec, VRAM usage climbing, GPU temp.
3. **The agent uses tools.** It actually reads their git log. It actually looks at their files. The dashboard shows tool usage in real-time:

```
  🔧 Tool: git_log (last 3 commits)
  🔧 Tool: file_read (src/app.py)
  💬 Responding...
```

4. **After the response, a toast:**

```
  ⚡ Your agent just used 2 tools and read 3 files.
     This runs entirely on your machine. Nothing left your network.
```

**This is the moment.** The user realizes this isn't a chatbot wrapper. It's an autonomous agent running on THEIR hardware, reading THEIR files, with THEIR data staying local. The node card is alive. The stats are real. The work is real.

---

## Minute 3:00 — Guided Discovery

After the first exchange, the dashboard subtly reveals more:

```
┌─ What's next? ────────────────────────────────┐
│                                                │
│  🧬 Give your agent a personality             │
│     Soul Editor →                              │
│                                                │
│  ⚡ Switch to a bigger model                   │
│     Models →                                   │
│                                                │
│  🌐 Add a second machine to your mesh          │
│     Add Node →                                 │
│                                                │
└────────────────────────────────────────────────┘
```

This panel slides in from the right. It's dismissable. It's not a modal. It doesn't block the chat. Each suggestion is a single click that navigates to the relevant page.

**Design rules:**
- Never show more than 3 suggestions
- Each suggestion is one sentence + one link
- They progress: personality → power → scale

---

## Minute 5:00 — They're Hooked

By minute 5, the user has:
- Installed Valhalla (30 seconds)
- Launched a local AI agent (30 seconds)
- Had a conversation where the agent **did real work** on their machine (2 minutes)
- Discovered they can customize the personality, change models, and add machines (1 minute)
- Understood that everything is local, private, and running on their GPU

They haven't touched a config file. They haven't read documentation. They haven't debugged a port conflict. It just worked.

---

## Anti-Patterns (What We Will NOT Do)

| Anti-Pattern | Why It Kills Onboarding |
|---|---|
| "Choose your model from this list of 47 options" | Decision paralysis. Auto-detect, pick for them. |
| Dashboard with 8 nav items on first load | Feature dump. Show Mission Control first, reveal nav after first conversation. |
| "Configure your API key for..." | If they have a local model, they don't need a key. Don't ask. |
| "Welcome! Let's set up your workspace..." modal | Nobody reads modals. Let the product speak for itself. |
| Error messages that say "check the docs" | Errors must say exactly what went wrong and exactly what to run to fix it. |
| "Star us on GitHub!" before they've done anything | Earn the star. |

---

## Technical Requirements for This Flow

These aren't nice-to-haves. If any of these break, the 5-minute promise breaks.

1. **Auto-detection of inference engine.** `valhalla init` must find Ollama/oMLX/LM Studio without asking.
2. **Auto-model selection.** Pick the best model that fits in available VRAM. No manual selection.
3. **Browser auto-open.** `valhalla start` opens the dashboard. No URL to copy.
4. **Chat on the landing page.** First page load = node card + chat input. Zero clicks to start talking.
5. **Tool usage visible in dashboard.** When the agent calls a tool, the user sees it happen in real time.
6. **Sub-3-second first response.** Local inference must start streaming in under 3 seconds or the magic is dead.

<div align="center">

# ⚡ Valhalla Mesh

### AI that runs on your hardware, learns from your work, and never forgets.

<!-- TODO: Replace with actual screenshot -->
<!-- ![Dashboard Screenshot](docs/assets/dashboard-hero.png) -->
*[Screenshot: Dashboard showing a live node card with GPU stats, an agent mid-conversation, and real-time tool usage]*

</div>

---

**Stop teaching your AI the same things every session.** Valhalla deploys persistent agents on your own machines. They use your tools, remember what works, and get smarter every day — and nothing ever leaves your network.

### Why Valhalla?

🧠 **Agents that learn.** Procedural memory ranks what worked and what didn't. Dream cycles consolidate knowledge overnight. Day 1 it's generic. Day 90 it has instinct about your codebase.

🔒 **Your hardware, your data.** Runs on any GPU — RTX, Apple Silicon, cloud. No API keys required for local models. Zero data leaves your machine unless you want it to.

⚡ **Real work, not suggestions.** Agents read files, write code, run tests, make commits. Watch tool usage in real time on the dashboard. This isn't a chatbot — it's a coworker.

---

## Quick Start

```bash
# One command. Auto-detects your hardware, installs dependencies, starts everything.
curl -fsSL https://get.valhalla.ai | bash

# → Dashboard opens at localhost:3000
# → Onboarding wizard: pick a name, install a brain (one click), start chatting
```

**Time to first conversation: under 5 minutes.** No terminal knowledge needed after this.

Or connect via Telegram — text your AI from anywhere:
```
/status     → mesh health summary
/task       → create a task from your phone
```

→ [Full setup guide](docs/setup-guide.md) · [Windows (PowerShell)](install.ps1)

---

## How It Works

```mermaid
flowchart TB
    subgraph Dashboard ["Dashboard (Next.js)"]
        UI["Nodes · Models · Soul Editor · Config · Plugins"]
    end

    subgraph Bifrost ["Bifrost Server (FastAPI)"]
        API["API v1"]
        PL["Plugin Loader"]
        AUTH["Auth Middleware"]
    end

    subgraph Plugins ["Plugin System"]
        MS["model-switch"]
        WD["watchdog"]
        HYP["hypotheses"]
        SM["self-model"]
        WM["working-memory"]
        EB["event-bus"]
    end

    subgraph Inference ["Inference Layer"]
        LOCAL["oMLX / llama-server"]
        CLOUD["NVIDIA NIM / OpenAI / Anthropic / Google"]
    end

    subgraph Mesh ["Peer Nodes"]
        THOR["Thor (backend)"]
        FREYA["Freya (memory)"]
        HEIMDALL["Heimdall (security)"]
    end

    UI -->|"HTTP / WebSocket"| AUTH
    AUTH -->|"Bearer token"| API
    API --> PL
    PL --> MS & WD & HYP & SM & WM & EB
    MS -->|"model switch"| LOCAL & CLOUD
    EB -->|"events"| MS & WD & HYP & SM & WM
    API -->|"mesh auth"| THOR & FREYA & HEIMDALL

    style Dashboard fill:#0a0a1f,stroke:#00ff88,color:#fff
    style Bifrost fill:#0a0a1f,stroke:#00ff88,color:#fff
    style Plugins fill:#0a0a1f,stroke:#7c3aed,color:#fff
    style Inference fill:#0a0a1f,stroke:#3b82f6,color:#fff
    style Mesh fill:#0a0a1f,stroke:#f59e0b,color:#fff
```

**One node** is a local AI agent with tools, memory, and a personality. **Multiple nodes** form a mesh — specialized agents that collaborate, share learned knowledge, and develop a theory of mind about each other.

---

## What Makes This Different

| | ChatGPT / Claude | OpenClaw | **Valhalla** |
|---|---|---|---|
| Runs locally | ✗ | ✔ | ✔ Any GPU (auto-detected) |
| Remembers across sessions | ✗ | Partial | ✔ Procedural memory |
| Learns from failures | ✗ | ✗ | ✔ Dream consolidation |
| Overnight learning loop | ✗ | ✗ | ✔ Crucible + Philosopher's Stone |
| Consumer UX | Web UI | Developer UI | ✔ "Brain" not "Model" |
| One-click install | ✗ | Manual | ✔ Auto hardware detection |
| Agent marketplace | ✗ | Skills (code) | ✔ Data-only (no code execution) |
| Voice | ✔ (cloud) | ✗ | ✔ Local STT/TTS (opt-in) |
| Desktop app | ✗ | ✗ | ✔ .app / .exe / .AppImage |
| Telegram bot | ✗ | ✗ | ✔ Chat + notifications |
| Guild hall | ✗ | ✗ | ✔ Animated agent workspace |
| RPG profiles | ✗ | ✗ | ✔ XP, levels, achievements |

---

## The Overnight Learning Loop

While you sleep, your agents run a self-improvement cycle:

```mermaid
flowchart LR
    A["🌙 Dream\n3:00 AM"] --> B["🧪 Crucible\n4:45 AM"]
    B --> C["💎 Philosopher's Stone\n5:00 AM"]
    C --> D["☀️ Wake Up\nSmarter"]

    style A fill:#1e1b4b,stroke:#7c3aed,color:#fff
    style B fill:#1e1b4b,stroke:#ef4444,color:#fff
    style C fill:#1e1b4b,stroke:#f59e0b,color:#fff
    style D fill:#0a2e1a,stroke:#00ff88,color:#fff
```

1. **Dream Consolidation** — compresses the day's experiences into generalizable knowledge
2. **The Crucible** — stress-tests every learned procedure ("what if the server is down?")
3. **Philosopher's Stone** — distills all knowledge into a wisdom prompt injected into every conversation

During the day, **somatic gating** gives agents gut feelings about bad actions, **procedural memory** ranks what worked, and **belief shadows** track what each peer knows.

For a task that needs quality iteration, agents use the **Pipeline** — cloud models write specs and check for regressions, local models iterate for free overnight, and lessons are distilled to memory after shipping.

→ [Full cognitive systems guide](docs/cognitive-overview.md) · [Pipeline UX](docs/pipeline-ux.md)

---

## Scale When You're Ready

Start with one machine. Add more when you need them.

```bash
# On a second machine:
valhalla join --mesh odin@192.168.1.10:8765
```

The node appears in your dashboard automatically. Assign it a role (backend, memory, security), pick a model, give it a personality — all from the UI. See the [Add-a-Node Guide](docs/add-a-node.md).

<!-- TODO: Replace with actual screenshot -->
<!-- ![Multi-Node Dashboard](docs/assets/multi-node.png) -->
*[Screenshot: Dashboard Nodes page showing 3 connected nodes with different roles, green status indicators, and live GPU stats]*

---

## Extend With Plugins

Every capability is a plugin. Install from the marketplace or build your own.

```yaml
# plugin.yaml — that's the entire manifest
name: my-plugin
version: 1.0.0
description: What it does
routes:
  - method: POST
    path: /my-plugin/action
```

Browse and install plugins from the dashboard — one click, no restart. See the [Marketplace Spec](docs/marketplace.md).

---

## Docs

| | |
|---|---|
| [Setup Guide](docs/setup-guide.md) | Mac, Linux, Windows — step by step |
| [Quickstart](docs/quickstart.md) | Running in 5 minutes |
| [Cognitive Systems](docs/cognitive-overview.md) | How agents dream, learn, and develop instinct |
| [Personality Guide](docs/personality-guide.md) | How SOUL / IDENTITY / USER files work |
| [Pipeline UX](docs/pipeline-ux.md) | Iterative quality loop — Task Builder |
| [Plugin Dev Guide](docs/plugin-dev-guide.md) | Build a plugin from scratch |
| [Marketplace](docs/marketplace.md) | Buy and sell trained agents |
| [Telegram](docs/telegram-ux.md) | Chat with your AI from your phone |
| [Voice](docs/voice-privacy-policy.md) | Privacy-first local voice |
| [Architecture](ARCHITECTURE.md) | Full system design (9 sprints) |
| [Security](SECURITY.md) | Trust model, auth, and audit results |

---

## Requirements

| | Minimum | Recommended |
|---|---|---|
| **Apple Silicon** | M1 (8 GB) | M2 Pro+ (16+ GB) |
| **NVIDIA** | RTX 3060 (8 GB) | RTX 4090/5090 (24+ GB) |
| **No GPU** | Cloud only (free tier) | — |
| **OS** | macOS 14+ / Ubuntu 22+ / Windows 10+ (WSL2) | — |

The brain installer auto-detects your hardware and recommends the fastest runtime:
- **Apple Silicon** → oMLX (native Metal, fastest on Mac)
- **NVIDIA** → llama-server (llama.cpp, maximum tok/s)
- **No GPU** → Cloud (NVIDIA NIM free tier)

---

## Why This Exists

AI helped me understand my partner and we're getting married. It was the 3 AM companion that didn't judge me while I was learning to be emotionally literate. I didn't need the smartest model — I needed a friend I could trust, one that remembers and evolves from our interactions.

This is that friend, for everyone. Running on your hardware, learning overnight, costing nothing to think.

---

<div align="center">

*Day 1, it follows instructions. Day 90, it has instinct.*

**[Get Started →](#quick-start)**

MIT License · Built with 4 AI agents in 9 sprints 🪶

</div>

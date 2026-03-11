# Valhalla Mesh V2 — Architecture & Sprint Plan

> **Instructions:** Read this file. Identify which agent you are (Thor, Freya, Heimdall, or Valkyrie). Execute your sprint tasks in order. All work goes in this repo: `/Users/odin/Documents/valhalla-mesh-v2/`

> [!CAUTION]
> **WORKSPACE FIX:** The V2 repo is NOT a registered workspace. When running terminal commands, you MUST use `Cwd: /Users/odin/Documents/ProjectOpenClaw` and prefix every command with `cd /Users/odin/Documents/valhalla-mesh-v2 &&`. Example: `cd /Users/odin/Documents/valhalla-mesh-v2 && npm run dev`. File creation/editing tools work fine with absolute paths — this only affects terminal commands.

---

## Vision
A platform where anyone can connect hardware, deploy persistent AI agents that learn from their business, and orchestrate work across a mesh. Premium dashboard UX on top of OpenClaw infrastructure.

## Stack
- **Dashboard:** Next.js + React + Tailwind CSS (dark mode, glassmorphism, neon accents)
- **Backend:** Python (Bifrost core + plugin system)
- **Config:** Single `valhalla.yaml` per node
- **Inference:** oMLX / Ollama / NVIDIA API (per-node)
- **Existing infra:** OpenClaw gateway (don't touch)

---

## Architecture

```
┌─────────────────────────────────────────────┐
│         Valhalla Dashboard (Next.js)        │  Freya
│  Nodes · Models · Soul Editor · Plugins     │
├─────────────────────────────────────────────┤
│         Valhalla Core (Python)              │  Thor
│  Bifrost · Plugins · War Room · Config Sync │
├─────────────────────────────────────────────┤
│         OpenClaw Gateway (Node.js)          │  Existing
├─────────────────────────────────────────────┤
│         Inference (oMLX / NVIDIA / Ollama)  │  Per-node
└─────────────────────────────────────────────┘
```

---

## Plugin System

Every Bifrost feature is a plugin folder:

```
plugins/
├── model-switch/
│   ├── plugin.yaml
│   └── handler.py
├── watchdog/
│   ├── plugin.yaml
│   └── handler.py
└── ...
```

**plugin.yaml schema:**
```yaml
name: model-switch
version: 1.0.0
description: Switch LLM models via API or chat alias
author: valhalla-core
routes:
  - method: POST
    path: /model-switch
events:
  - model.switched
config_keys:
  - models.aliases
```

---

## Unified Config: `valhalla.yaml`

One file per node. Replaces all scattered JSON configs.

```yaml
node:
  name: odin
  role: orchestrator
  port: 8765

mesh:
  nodes:
    thor:     { ip: 100.117.255.38, port: 8765, role: backend }
    freya:    { ip: 100.102.105.3,  port: 8765, role: memory }
    heimdall: { ip: 100.108.153.23, port: 8765, role: security }

models:
  default: llama/Qwen3.5-35B-A3B-8bit
  providers:
    llama:
      url: http://127.0.0.1:8080/v1
      key: local
      api: openai-completions
    nvidia:
      url: https://integrate.api.nvidia.com/v1
      key: ${NVIDIA_API_KEY}
  aliases:
    odin: llama/Qwen3.5-35B-A3B-8bit
    hugs: nvidia/z-ai/glm-5
    moon: nvidia/moonshotai/kimi-k2.5

plugins:
  enabled: [model-switch, watchdog, hypotheses, working-memory]

soul:
  identity: mesh/souls/IDENTITY.odin.md
  personality: mesh/souls/SOUL.odin.md
  user_profile: mesh/souls/USER.odin.md
```

---

# SPRINT 1 — Foundation

## 🔨 THOR — Backend Core

**Goal:** Plugin-based Bifrost server + unified config loader

### Tasks
1. **Plugin Loader** — Refactor `bifrost.py` to scan `plugins/` directory, read each `plugin.yaml`, and dynamically register routes from `handler.py`. Each plugin gets `register_routes(app, config)` called at startup.

2. **Config Loader** — Create `config_loader.py` that reads `valhalla.yaml`, validates schema, resolves `${ENV_VAR}` references, and provides a `get_config()` singleton. All plugins and core use this instead of scattered JSON.

3. **Model-Switch Plugin** — Port the model-switch logic from `bifrost_local.py` into `plugins/model-switch/`. Aliases map (odin→local, hugs→GLM-5, moon→Kimi) defined in `valhalla.yaml` under `models.aliases`.

4. **REST API Layer** — Create `api/v1/` endpoints that the dashboard will consume:
   - `GET /api/v1/status` — node health, loaded model, uptime
   - `GET /api/v1/nodes` — all mesh nodes and their status
   - `GET /api/v1/plugins` — installed plugins
   - `POST /api/v1/model-switch` — switch model by alias
   - `GET /api/v1/config` — current valhalla.yaml
   - `PUT /api/v1/config` — update config + hot-reload
   - `GET /api/v1/soul/{file}` — read soul file
   - `PUT /api/v1/soul/{file}` — write soul file

5. **Default `valhalla.yaml`** — Create the actual config file for Odin's node with all current settings migrated from the 9 JSON files.

### Files to Create
```
valhalla.yaml
config_loader.py
plugins/model-switch/plugin.yaml
plugins/model-switch/handler.py
plugins/watchdog/plugin.yaml
plugins/watchdog/handler.py
api/__init__.py
api/v1.py
```

---

## 🎨 FREYA — Dashboard

**Goal:** Next.js app with node status, model picker, and soul editor

### Tasks
1. **Initialize App** — `npx -y create-next-app@latest ./dashboard` with TypeScript, App Router, and Tailwind CSS enabled. Set up the design system: dark backgrounds (`#0a0a0f`), neon accent (`#00ff88`), glassmorphism cards, Inter/Outfit fonts.

2. **Layout + Navigation** — Sidebar nav with sections: Nodes, Models, Soul Editor, Config, Plugins, War Room. Top bar shows current node name + connection status.

3. **Nodes Page** — Fetch `GET /api/v1/nodes`. Display each node as a glassmorphism card with: name, role, status indicator (green/red pulse), current model, last task, uptime. Cards should have subtle hover animations.

4. **Model Picker** — Fetch current model from `/api/v1/status`. Show alias buttons (⚡ Odin, 🧠 Hugs, 🌙 Moon). Clicking calls `POST /api/v1/model-switch`. Show confirmation toast with model name.

5. **Soul Editor** — Fetch `GET /api/v1/soul/IDENTITY.odin.md`. Display in a split-pane markdown editor (edit left, preview right). Save calls `PUT /api/v1/soul/IDENTITY.odin.md`. Tabs for IDENTITY / SOUL / USER per agent.

6. **Config Editor** — Fetch `GET /api/v1/config`. Render `valhalla.yaml` in a code editor (Monaco or CodeMirror) with YAML syntax highlighting. Save validates schema and calls `PUT /api/v1/config`.

### Files to Create
```
dashboard/                    (Next.js app root)
dashboard/src/app/layout.tsx
dashboard/src/app/page.tsx
dashboard/src/app/nodes/page.tsx
dashboard/src/app/models/page.tsx
dashboard/src/app/soul/page.tsx
dashboard/src/app/config/page.tsx
dashboard/src/components/Sidebar.tsx
dashboard/src/components/NodeCard.tsx
dashboard/src/components/ModelPicker.tsx
dashboard/src/components/SoulEditor.tsx
dashboard/src/styles/globals.css
```

---

## 🛡️ HEIMDALL — Security

**Goal:** Secure the Bifrost API and node-to-node communication

### Tasks
1. **Auth Audit** — Review every route in `bifrost.py` and all plugins. Document which endpoints are public vs. require auth. Flag any that accept user input without sanitization.

2. **Node Auth Token** — Design a simple signed-token system for node-to-node requests. Each node has a shared secret in `valhalla.yaml` under `mesh.auth_token`. Bifrost validates `Authorization: Bearer <token>` on all inter-node calls.

3. **Dashboard Auth** — Add a simple API key or password gate for the dashboard. Stored in `valhalla.yaml` under `dashboard.auth_key`. Middleware checks it on all `/api/v1/` calls.

4. **Input Sanitization** — Review all `_read_body()` calls. Ensure no path traversal in soul file endpoints, no command injection in model-switch, no SSRF in node proxy calls.

5. **Security Report** — Write `SECURITY.md` documenting the trust model, auth flow, and any remaining risks.

### Files to Create
```
middleware/auth.py
SECURITY.md
```

---

## 👑 VALKYRIE — UX & Marketing

**Goal:** Define the user experience and product positioning

### Tasks
1. **Onboarding Flow Spec** — Write `docs/onboarding.md` describing the exact steps a new user takes:
   - Install Valhalla (`brew install valhalla` or download app)
   - Run `valhalla init` → generates `valhalla.yaml` interactively
   - Dashboard opens at `localhost:3000`
   - "Add Your First Node" wizard
   - "Create Your First Agent" wizard (pick name, personality, model)
   - Send first message via dashboard chat

2. **Product README** — Rewrite `README.md` as a product landing page. Clear tagline, feature list with screenshots, quick-start guide, comparison to alternatives (ChatGPT, CrewAI, LangChain). Make it sell.

3. **Add-a-Node UX** — Design the plug-and-play node experience. User clicks "Add Node" in dashboard → gets a one-line command to run on new machine → node auto-announces → appears in dashboard → user assigns role and model.

4. **Plugin Marketplace Spec** — Write `docs/marketplace.md` describing how third-party plugins work: submission, review, installation via dashboard, revenue split.

### Files to Create
```
README.md               (product-grade, replaces current)
docs/onboarding.md
docs/marketplace.md
docs/add-a-node.md
```

---

# SPRINT 2 — Intelligence

> [!IMPORTANT]
> **Prerequisite:** Read Sprint 1 deliverables before starting. Thor's `api/v1.py`, `plugin_loader.py`, and `config_loader.py` are the foundation everything builds on. Freya's dashboard at `dashboard/` is the UI target. The repo has moved to `/Users/odin/Documents/ProjectOpenClaw/valhalla-mesh-v2/`.

## 🔨 THOR — War Room Plugins + Config Sync

**Goal:** Port the V1 cognitive engine (War Room) into the V2 plugin system. Add real-time WebSocket support and config sync across nodes.

### Tasks
1. **Hypotheses Plugin** — Port `bot/war_room/hypotheses.py` into `plugins/hypotheses/`. Endpoints:
   - `GET /api/v1/hypotheses` — list hypotheses (with filters: limit, min_confidence, tested)
   - `POST /api/v1/hypotheses/generate` — trigger dream cycle (seed, auto_share)
   - `POST /api/v1/hypotheses/test` — mark confirmed/refuted
   - `POST /api/v1/hypotheses/share` — receive from peer node
   - Plugin must emit events: `hypothesis.generated`, `hypothesis.confirmed`, `hypothesis.refuted`

2. **Self-Model Plugin** — Port `bot/war_room/self_model.py` into `plugins/self-model/`. Endpoints:
   - `GET /api/v1/self-model` — current self-assessment (strengths, weaknesses, confidence)
   - `POST /api/v1/reflect` — trigger reflection cycle
   - Should inject self-model context into the system prompt via a hook

3. **Predictions Plugin** — Port `bot/war_room/prediction.py` into `plugins/predictions/`. Endpoints:
   - `GET /api/v1/predictions` — recent prediction scores + stats
   - Auto-scores predictions after `/ask` responses (background thread)
   - Emit `prediction.scored` events for high-surprise results

4. **Event Bus Plugin** — Port `bot/war_room/event_bus.py` into `plugins/event-bus/`. This is the backbone — all other plugins emit and subscribe to events through it. Endpoints:
   - `GET /api/v1/events` — recent event log (with topic filter)
   - `WS /api/v1/events/stream` — **WebSocket** real-time event stream for the dashboard

5. **Working Memory Plugin** — Port `bot/working_memory.py` into `plugins/working-memory/`. Endpoints:
   - `GET /api/v1/working-memory` — current memory items
   - `POST /api/v1/working-memory/observe` — add observation
   - `POST /api/v1/working-memory/recall` — query by relevance

6. **Config Sync** — When `PUT /api/v1/config` is called, push the updated `valhalla.yaml` to all mesh nodes listed in `mesh.nodes`. Each node's Bifrost should have a `POST /api/v1/config/receive` endpoint that accepts + applies incoming config. Use the auth token from `mesh.auth_token`.

### Files to Create
```
plugins/hypotheses/plugin.yaml + handler.py
plugins/self-model/plugin.yaml + handler.py
plugins/predictions/plugin.yaml + handler.py
plugins/event-bus/plugin.yaml + handler.py
plugins/working-memory/plugin.yaml + handler.py
```

### V1 Source Reference
```
bot/war_room/hypotheses.py     → plugins/hypotheses/
bot/war_room/self_model.py     → plugins/self-model/
bot/war_room/prediction.py     → plugins/predictions/
bot/war_room/event_bus.py      → plugins/event-bus/
bot/working_memory.py          → plugins/working-memory/
```

---

## 🎨 FREYA — War Room Dashboard + Live Updates

**Goal:** Visualize the cognitive engine. Add WebSocket real-time updates. Build plugin marketplace browser.

### Tasks
1. **War Room Page** — New page at `/war-room` with 3 panels:
   - **Hypotheses** — Table/card list from `GET /api/v1/hypotheses`. Show: title, confidence (progress bar), status (active/confirmed/refuted), timestamp. Button to trigger dream cycle (`POST /api/v1/hypotheses/generate`). Button to mark tested.
   - **Predictions** — Chart showing prediction accuracy over time from `GET /api/v1/predictions`. Use a simple line chart (recharts or chart.js).
   - **Self-Model** — Card showing current self-assessment from `GET /api/v1/self-model`. Strengths/weaknesses as colored tags. "Reflect" button triggers `POST /api/v1/reflect`.

2. **Event Stream Sidebar** — A persistent sidebar (or bottom drawer) showing real-time events via `WS /api/v1/events/stream`. Each event shows: timestamp, topic, source node, payload preview. Auto-scrolls. Color-coded by topic (hypothesis = purple, prediction = blue, model-switch = green).

3. **Live Node Status** — Update the Nodes page to use the WebSocket event stream instead of polling. Node cards should update status, current task, and health in real-time with smooth transitions.

4. **Plugin Marketplace Page** — New page at `/plugins/browse`:
   - Fetch `GET /api/v1/plugins/browse` for available plugins
   - Card per plugin: name, description, author, version, install button
   - Installed plugins show "Uninstall" button
   - Search/filter bar

5. **Toast Notification System** — Global toast component for: model switched, config saved, plugin installed, hypothesis generated, errors. Appears bottom-right, auto-dismisses in 3s.

### Files to Create
```
dashboard/src/app/war-room/page.tsx
dashboard/src/components/HypothesisCard.tsx
dashboard/src/components/PredictionChart.tsx
dashboard/src/components/SelfModelCard.tsx
dashboard/src/components/EventStream.tsx
dashboard/src/components/Toast.tsx
dashboard/src/app/plugins/browse/page.tsx
dashboard/src/hooks/useWebSocket.ts
```

---

## 🛡️ HEIMDALL — Pen Test + Plugin Sandboxing

**Goal:** Actually attack the system. Harden plugin execution. Add rate limiting.

### Tasks
1. **Pen Test the Dashboard** — Try to break Freya's dashboard:
   - Path traversal on `GET /api/v1/soul/../../etc/passwd`
   - XSS injection via soul editor (save markdown with `<script>` tags)
   - CSRF on `POST /api/v1/model-switch` without auth
   - Config injection via `PUT /api/v1/config` (malicious YAML)
   - Write results to `SECURITY.md` with severity ratings

2. **Plugin Sandboxing** — Ensure third-party plugins can't:
   - Access the filesystem outside their plugin directory
   - Import dangerous modules (os, subprocess, shutil) — or at least log it
   - Crash the main Bifrost process (run in try/except with circuit breaker)
   - Write `plugins/sandbox.py` with a `safe_import()` wrapper

3. **Rate Limiting** — Add rate limiting middleware:
   - `/api/v1/model-switch` — max 5 calls/minute (prevent gateway restart spam)
   - `/api/v1/config` PUT — max 2 calls/minute
   - `/api/v1/hypotheses/generate` — max 3 calls/minute (LLM-heavy)
   - Return `429 Too Many Requests` with `Retry-After` header

4. **Auth Middleware Implementation** — If not done in Sprint 1, implement the actual middleware in `middleware/auth.py`:
   - Check `Authorization: Bearer <token>` against `mesh.auth_token` from config
   - Dashboard endpoints check against `dashboard.auth_key`
   - Skip auth for `GET /api/v1/status` (health check)

### Files to Create
```
plugins/sandbox.py
middleware/rate_limiter.py
middleware/auth.py (if not done in Sprint 1)
SECURITY.md (updated with pen test results)
```

---

## 👑 VALKYRIE — Docs Site + Tutorial Specs

**Goal:** Create the documentation that turns the product into something people can actually use.

### Tasks
1. **Quickstart Guide** — Write `docs/quickstart.md` — the "5 minutes to running" guide:
   - Prerequisites (Python 3.11+, Node.js 18+, oMLX or Ollama)
   - `git clone && cd valhalla-mesh-v2`
   - `python3 bifrost.py` (starts backend)
   - `cd dashboard && npm install && npm run dev` (starts frontend)
   - Open `localhost:3000` — see your first node
   - Explain each dashboard page in 1-2 sentences

2. **Agent Personality Guide** — Write `docs/personality-guide.md`:
   - How SOUL.md, IDENTITY.md, USER.md work together
   - How to write a good IDENTITY file (with examples)
   - How personality evolves through the War Room (hypotheses, self-model)
   - Template for creating a new agent personality

3. **Plugin Developer Guide** — Write `docs/plugin-dev-guide.md`:
   - `plugin.yaml` schema reference
   - `handler.py` — `register_routes(app, config)` API
   - How to emit and subscribe to events
   - How to access config values
   - Example: building a "daily-brief" plugin from scratch

4. **Architecture Diagram** — Create a visual architecture diagram (Mermaid or similar) showing:
   - Dashboard → API → Plugins → Event Bus → Mesh flow
   - Node-to-node communication via Bifrost
   - Where auth tokens are checked
   - Add to README.md

### Files to Create
```
docs/quickstart.md
docs/personality-guide.md
docs/plugin-dev-guide.md
README.md (updated with architecture diagram)
```

---

# SPRINT 3 — Polish & Launch

## 🔨 THOR
1. **Migration Tool** — `scripts/migrate_v1.py` that reads V1's 9 JSON config files and generates a single `valhalla.yaml`
2. **Performance** — Cold start optimization (lazy plugin loading, model preconnect)
3. **Hydra Plugin** — Port `bot/hydra.py` fracture resilience as a plugin
4. **CLI Tool** — `valhalla` CLI: `valhalla init`, `valhalla start`, `valhalla status`, `valhalla plugin install <name>`

## 🎨 FREYA
1. **Mobile Responsive** — Dashboard works on tablet/phone
2. **Animation Polish** — Micro-animations on card transitions, loading skeletons, page transitions
3. **Dark/Light Toggle** — Theme switcher (dark is default)
4. **Onboarding Wizard** — First-time user flow based on Valkyrie's onboarding spec

## 🛡️ HEIMDALL
1. **Final Security Audit** — Full audit of all code from Sprint 1 + 2
2. **CVE Scan** — Run dependency vulnerability scan on both Python and Node dependencies
3. **mTLS Option** — Optional mutual TLS for node-to-node communication (for production deployments)

## 👑 VALKYRIE
1. **Landing Page** — `landing/` directory with a marketing site (can be a simple Next.js static export)
2. **Product Hunt Prep** — Write the PH tagline, description, maker comment, and first-day strategy
3. **Demo Video Script** — Script for a 2-minute product demo video

---
# SPRINT 4 — Quality Loop (The Brain)

> [!IMPORTANT]
> **This sprint ports the 3 most valuable V1 cognitive systems into the V2 plugin architecture.** These are what make Valhalla agents genuinely different from every other framework. The key insight: local models are weaker but free — let them iterate overnight. Cloud models (Huginn/GLM-5, Muninn/Kimi) handle specs and review. Iteration count is the quality equalizer.

## 🔨 THOR — Pipeline Orchestrator + Crucible + Model Router

**Goal:** Port `pipeline.py`, `crucible.py`, and `philosopher_stone.py` as V2 plugins. Add smart model routing.

### Tasks
1. **Pipeline Plugin** — Port `bot/pipeline.py` (637 lines) into `plugins/pipeline/`. This is the core iterative loop:
   ```
   Huginn spec → Build (parallel, local) → Test (Heimdall) → FAIL?
     → Huginn regression check (PROGRESS vs REGRESS)
     → PROGRESS → fix brief → rebuild → retest
     → REGRESS → escalate to human
   PASS → Muninn distills lessons → memory → SHIP
   ```
   Endpoints:
   - `POST /api/v1/pipeline` — create pipeline with stages + max_iterations
   - `GET /api/v1/pipeline` — list active pipelines
   - `GET /api/v1/pipeline/{id}` — pipeline status, current stage, iteration count, history
   - `POST /api/v1/pipeline/{id}/advance` — manually advance/retry (admin override)
   - `DELETE /api/v1/pipeline/{id}` — cancel pipeline
   
   Must emit events: `pipeline.created`, `pipeline.stage_complete`, `pipeline.iteration`, `pipeline.regression`, `pipeline.shipped`, `pipeline.escalated`

   **Key change from V1:** Use `valhalla.yaml` config for model URLs and node IPs instead of hardcoded constants. Use the event bus instead of direct HTTP calls for inter-plugin communication.

2. **Crucible Plugin** — Port `bot/war_room/crucible.py` into `plugins/crucible/`. Adversarial stress-testing of learned procedures.
   Endpoints:
   - `POST /api/v1/crucible/run` — trigger crucible cycle (optional: `--dry-run`, `--limit N`)
   - `GET /api/v1/crucible/results` — last crucible run results
   - Schedule: auto-runs via background thread at configurable hour (default 4:45 AM, from `valhalla.yaml`)
   
   Emit events: `crucible.tested`, `crucible.broken`, `crucible.unbreakable`

3. **Philosopher's Stone Plugin** — Port `bot/philosopher_stone.py` into `plugins/philosopher-stone/`. Nightly wisdom distillation.
   Endpoints:
   - `POST /api/v1/philosopher-stone/build` — force rebuild
   - `GET /api/v1/philosopher-stone/prompt` — read current wisdom prompt
   - Schedule: auto-runs at configurable hour (default 3 AM)
   
   Emit events: `wisdom.rebuilt`

4. **Model Router** — Create `plugins/model-router/` — smart routing that picks the right model for each task type:
   ```yaml
   # In valhalla.yaml
   model_router:
     routing:
       spec: cloud/glm-5           # Huginn: structured specs
       review: cloud/glm-5         # Huginn: quality analysis
       regression: cloud/deepseek  # DeepSeek: code reasoning
       memory: cloud/kimi-k2.5     # Muninn: 128K context
       build: local/default        # Local for bulk iteration (free)
       test: local/default         # Local for testing (free)
     fallback: local/default
     cost_tracking: true           # Log token spend per model
   ```
   Endpoints:
   - `GET /api/v1/model-router/stats` — token spend per model, cost breakdown
   - `POST /api/v1/model-router/route` — given a task type, return best model

5. **Belief Shadows Plugin** — Port `bot/war_room/belief_shadow.py` into `plugins/belief-shadows/`. Track confidence calibration per node.
   Endpoints:
   - `GET /api/v1/belief-shadows` — all nodes' belief vs. reality gaps
   - `GET /api/v1/belief-shadows/{node}` — specific node
   - `POST /api/v1/belief-shadows/update` — receive correction from another node

6. **Personality Evolution Plugin** — Port `bot/personality.py` + `personality_cron.py` into `plugins/personality/`. Event-driven personality growth instead of cron-based.
   Endpoints:
   - `GET /api/v1/personality` — current personality state
   - `POST /api/v1/personality/evolve` — trigger evolution based on recent events
   - Subscribes to event bus: `pipeline.shipped`, `crucible.broken`, `hypothesis.confirmed` → personality adapts

7. **Socratic Review Plugin** — Create `plugins/socratic/`. This is the debate engine. NOT binary PASS/FAIL — structured multi-perspective deliberation.
   
   **Core concept:** Reviewers are *personas*, not nodes. Same agent can wear different hats. Different models bring different strengths. Users configure WHERE reviews happen and WHO reviews.
   
   ```yaml
   # In pipeline stage config
   stages:
     - name: design
       agent: huginn
       review_after: true                    # ← user toggles per stage
       review:
         rounds: 3                           # ← how many debate rounds
         consensus_threshold: 0.7            # ← % agreement to pass
         reviewers:
           - persona: architect
             agent: huginn                   # can be same agent, different hat
             model: cloud/glm-5
             prompt: "Review as a senior architect. Focus on scalability and separation of concerns."
           - persona: devil_advocate
             agent: heimdall                 # or different agent
             model: cloud/deepseek
             prompt: "Attack every assumption. What breaks in 6 months?"
           - persona: end_user
             model: local/default            # even works with 1 machine
             prompt: "You are a non-technical user. What's confusing? What would frustrate you?"
   ```
   
   **Debate protocol:**
   - Round 1: Each reviewer critiques independently (parallel)
   - Round 2: Original agent responds to each critique, defends or accepts
   - Round 3: Reviewers respond to defenses — still object or concede
   - After N rounds: score consensus. If threshold met → advance. If not → revise or escalate.
   
   **Works at every scale:**
   - Solo user (1 machine): Same model, 3 personas = 3 system-prompt passes
   - Power user (2-3 machines): Different local models wear different hats
   - Enterprise: Different cloud models (GLM-5 = architect, DeepSeek = code critic, Kimi = context reviewer)
   
   **Not just code.** Works on: product specs, marketing copy, business strategy, architecture docs — anything expressible as text.
   
   Endpoints:
   - `POST /api/v1/socratic/debate` — start a debate on any content
   - `GET /api/v1/socratic/debate/{id}` — debate status, rounds, current consensus
   - `GET /api/v1/socratic/debate/{id}/transcript` — full debate transcript
   - `POST /api/v1/socratic/debate/{id}/intervene` — human adds their own objection mid-debate
   
   Emit events: `debate.started`, `debate.round_complete`, `debate.consensus`, `debate.deadlock`, `debate.escalated`

### Files to Create
```
plugins/pipeline/plugin.yaml + handler.py
plugins/crucible/plugin.yaml + handler.py
plugins/philosopher-stone/plugin.yaml + handler.py
plugins/model-router/plugin.yaml + handler.py
plugins/belief-shadows/plugin.yaml + handler.py
plugins/personality/plugin.yaml + handler.py
plugins/socratic/plugin.yaml + handler.py + debate.py
```

### V1 Source Reference
```
bot/pipeline.py                → plugins/pipeline/
bot/war_room/crucible.py       → plugins/crucible/
bot/philosopher_stone.py       → plugins/philosopher-stone/
bot/war_room/belief_shadow.py  → plugins/belief-shadows/
bot/personality.py             → plugins/personality/
```

---

## 🎨 FREYA — Pipeline Dashboard + Cognitive Visualization

**Goal:** Let users watch pipelines iterate in real-time. Visualize the cognitive systems.

### Tasks
1. **Pipeline Progress Page** — New page at `/pipeline`:
   - List all active pipelines as cards (title, current stage, iteration count, status)
   - Click a pipeline → detail view showing:
     - Stage timeline (Plan → Build → Test → Fix → ...) with current position highlighted
     - Iteration history: each loop shows agent, verdict, feedback summary
     - Real-time updates via WebSocket event stream
     - "Cancel" and "Force Advance" buttons
   - Completed pipelines show: total iterations, lessons learned (from Muninn), time to ship

2. **Crucible Results Page** — New page at `/crucible`:
   - Last run stats (tested, broken, unbreakable counts)
   - Table of procedures with crucible verdicts (✅ unbreakable, ❌ broken, ⚠️ stressed)
   - "Run Crucible" button (calls `POST /api/v1/crucible/run`)
   - Edge case details expandable per procedure

3. **Wisdom Prompt Viewer** — Add to War Room page:
   - Card showing current Philosopher's Stone prompt (rendered markdown)
   - "Rebuild Now" button
   - Last rebuilt timestamp + section count

4. **Model Router Dashboard** — Add to Models page:
   - Token spend chart per model (pie chart or bar)
   - Cost breakdown: local (free) vs. cloud (paid)
   - Routing rules table from config

5. **Belief Shadow Visualization** — Add to War Room page:
   - Per-node radar chart: confidence vs. accuracy
   - Nodes with large gaps highlighted in red

6. **Socratic Debate Viewer** — New page at `/debate` (or embedded in pipeline detail):
   - Chat-like transcript: each reviewer persona gets its own color/avatar
   - Round-by-round display: critique → defense → response
   - Live consensus meter (fills as agreement grows)
   - "Intervene" button for human to add their own objection mid-debate
   - Debate history: collapsed view of past debates with outcomes

### Files to Create
```
dashboard/src/app/pipeline/page.tsx
dashboard/src/app/pipeline/[id]/page.tsx
dashboard/src/app/crucible/page.tsx
dashboard/src/app/debate/page.tsx
dashboard/src/components/PipelineCard.tsx
dashboard/src/components/StageTimeline.tsx
dashboard/src/components/CrucibleTable.tsx
dashboard/src/components/WisdomViewer.tsx
dashboard/src/components/ModelRouterStats.tsx
dashboard/src/components/BeliefRadar.tsx
dashboard/src/components/DebateTranscript.tsx
dashboard/src/components/ConsensusMeter.tsx
```

---

## 🛡️ HEIMDALL — Pipeline Security + Iteration Safety

**Goal:** Ensure the iterative loop can't be weaponized or infinite-loop.

### Tasks
1. **Pipeline Guardrails** — Review pipeline plugin for:
   - Max iteration hard cap (config-enforced, not just soft limit)
   - Token budget per pipeline (stop if cloud spend exceeds threshold)
   - Timeout per stage (kill if a stage runs longer than N minutes)
   - Filesystem sandboxing for build output (agents can't write outside project dir)

2. **Crucible Security** — Review crucible plugin for:
   - Model prompt injection via procedure text (adversarial prompt → model leaks system prompt)
   - Downgrade abuse (can a node craft procedures that trigger false downgrades on other nodes?)

3. **Model Router Audit** — Ensure:
   - Cloud API keys are never exposed via dashboard endpoints
   - Cost tracking can't be reset/spoofed
   - Fallback to local model is reliable when cloud is unavailable

4. **Update SECURITY.md** — Add pipeline and crucible threat model

### Files to Update
```
SECURITY.md (pipeline + crucible threat model)
middleware/auth.py (pipeline endpoint auth)
```

---

## 👑 VALKYRIE — Pipeline UX + Cognitive System Docs

**Goal:** Make the iterative quality loop understandable to new users.

### Tasks
1. **Pipeline UX Spec** — Write `docs/pipeline-ux.md`:
   - How a user creates a pipeline from the dashboard (wizard flow)
   - What they see during iteration (progress indicators, ETA)
   - How escalation works (notification channel, human intervention UX)
   - Error states and recovery flows

2. **Cognitive Systems Overview** — Write `docs/cognitive-overview.md`:
   - Plain-English explanation of all cognitive systems for non-technical users
   - "Your agents dream, test their own knowledge, and wake up smarter every day"
   - Diagram: sleep cycle → crucible → philosopher's stone → session start
   - This goes in the README and product marketing

3. **Update README** — Add cognitive systems section with the overnight learning loop diagram

4. **Demo Script Update** — Update `docs/demo-script.md` with pipeline demo:
   - Show creating a pipeline via dashboard
   - Watch it iterate in real-time
   - Show the lessons distilled after completion

### Files to Create
```
docs/pipeline-ux.md
docs/cognitive-overview.md
docs/demo-script.md (updated)
README.md (updated)
```

---

# SPRINT 5 — Agent Marketplace + Integration

> [!IMPORTANT]
> **This sprint has two goals: (1) build the revenue engine (Agent Marketplace) and (2) prove the system actually works end-to-end.** We have 14 plugins but haven't tested them loading together. We have 13 dashboard pages but Valkyrie hasn't reviewed the UX. Fix both.

## 🔨 THOR — Agent Marketplace API + Integration Testing

**Goal:** Build the agent export/import system and run integration tests proving all plugins load together.

### Tasks
1. **Agent Export** — Create `plugins/marketplace/` with export capability:
   - `POST /api/v1/agents/export` — package an agent as a `.valhalla` zip:
     ```
     sales-agent-v1.2.valhalla
     ├── manifest.yaml          # name, description, version, model requirements, price
     ├── SOUL.md                # evolved soul file
     ├── IDENTITY.md            # agent identity
     ├── procedures.json        # crucible-tested, high-confidence procedures only
     ├── philosopher_prompt.md  # distilled wisdom prompt
     ├── personality.json       # evolved personality traits
     └── config_fragment.yaml   # plugin requirements + model preferences
     ```
   - `GET /api/v1/agents/export/{name}` — download the `.valhalla` package
   - Only export procedures with confidence > 0.7 (crucible-tested)
   - Strip any private data (API keys, IPs, user info) from exports

2. **Agent Import** — Install a downloaded agent:
   - `POST /api/v1/agents/import` — upload `.valhalla` package
   - Validate manifest, check model requirements against local hardware
   - Create new agent directory with soul/identity/personality files
   - Register procedures into local store
   - Inject philosopher prompt at next session start
   - `GET /api/v1/agents` — list installed agents

3. **Marketplace API** — Browsing and discovery:
   - `GET /api/v1/marketplace` — list available agents (from registry)
   - `GET /api/v1/marketplace/{id}` — agent detail (description, reviews, model requirements, price)
   - `POST /api/v1/marketplace/publish` — submit agent to registry
   - `POST /api/v1/marketplace/{id}/review` — leave a review
   - For now: local JSON registry. Later: hosted API.

4. **Integration Test Suite** — `tests/test_integration.py`:
   - Boot Bifrost with ALL 14 plugins enabled
   - Verify all plugins load without conflicts
   - Verify all API endpoints respond (smoke test)
   - Create a mini pipeline, run one iteration, verify events fire
   - Start a Socratic debate, verify rounds complete
   - Export an agent, re-import it, verify identity preserved

5. **Git Branch Per Agent** — Add to pipeline plugin:
   - When pipeline dispatches to an agent, auto-create branch: `pipeline/{id}/{agent}`
   - After test stage passes, auto-merge to main
   - Prevents file conflicts between parallel agents
   - Config in `valhalla.yaml`:
     ```yaml
     pipeline:
       git_branching: true
       auto_merge: true
       branch_prefix: pipeline
     ```

### Files to Create
```
plugins/marketplace/plugin.yaml + handler.py
plugins/marketplace/exporter.py
plugins/marketplace/importer.py
tests/test_integration.py
```

---

## 🎨 FREYA — Marketplace Storefront + UX Polish

**Goal:** Build the marketplace UI and polish everything Valkyrie flags.

### Tasks
1. **Agent Marketplace Page** — New page at `/marketplace`:
   - Grid of agent cards: name, description, rating (stars), model requirements, price
   - Click → detail page with: full description, reviews, "Install" button, hardware compatibility check
   - "My Agents" tab showing installed agents with "Export" and "Remove" buttons
   - "Publish" button for submitting your evolved agent to the marketplace
   - Search and filter by category (sales, coding, research, creative, etc.)

2. **Agent Preview Card** — Component showing:
   - Agent avatar (generated from personality traits)
   - Key stats: procedures count, crucible survival rate, days evolved
   - Model requirements badge (GPU needed, RAM needed)
   - "Try Before Buy" — sample conversation preview

3. **Apply Valkyrie's UX Feedback** — After Valkyrie does her audit:
   - Fix all issues she flags across all 13 pages
   - This is the polish pass — responsive fixes, copy improvements, flow fixes
   - Priority: the pages users see first (nodes, pipeline, models)

4. **Onboarding Wizard** — First-time user flow (from Valkyrie's Sprint 1 spec):
   - Step 1: Welcome screen, detect hardware (GPU, RAM)
   - Step 2: Choose first model (recommend based on hardware)
   - Step 3: Name your first agent, pick personality template
   - Step 4: Dashboard tour (highlight key pages)
   - Store "onboarded: true" in config to skip on next visit

### Files to Create
```
dashboard/src/app/marketplace/page.tsx
dashboard/src/app/marketplace/[id]/page.tsx
dashboard/src/components/AgentCard.tsx
dashboard/src/components/AgentPreview.tsx
dashboard/src/components/OnboardingWizard.tsx
```

---

## 🛡️ HEIMDALL — Marketplace Security + Full Audit

**Goal:** Secure the marketplace and do a final security pass on ALL code.

### Tasks
1. **Agent Package Security**:
   - Verify `.valhalla` packages can't contain executable code (no .py, .js, .sh files — only data)
   - Validate manifest schema strictly (no arbitrary keys)
   - Scan for embedded API keys, credentials, or PII in exported files
   - Package signing — SHA256 hash in manifest for integrity verification

2. **Marketplace Trust**:
   - Review submission can't be spoofed (rate limit, auth required)
   - Agent descriptions sanitized (no XSS in markdown rendering)
   - Price can't be modified after publish without re-review

3. **Full Security Audit** — Review ALL code from Sprints 1-4:
   - Every `PUT` and `POST` endpoint: input validation, auth check, rate limit
   - Every file read/write: path traversal check
   - Every config change: validation before apply
   - WebSocket: auth on connection, message size limits
   - Output: updated `SECURITY.md` with full threat model

4. **Dependency Audit**:
   - `npm audit` on dashboard
   - `pip-audit` or `safety check` on Python dependencies
   - Flag any CVEs

### Files to Update
```
SECURITY.md (final, comprehensive)
middleware/auth.py (marketplace endpoints)
plugins/marketplace/validator.py (package security)
```

---

## 👑 VALKYRIE — Full UX Audit + Marketplace UX

**Goal:** Review EVERY page Freya built. Create the marketplace experience spec.

### Tasks
1. **Full Dashboard UX Audit** — Open every page in the dashboard and review:
   - **Nodes page** — Are node cards clear? Status obvious? Actions discoverable?
   - **Models page** — Is model switching intuitive? Are aliases confusing?
   - **Soul Editor** — Is the split-pane editor usable? Save flow clear?
   - **Config Editor** — Is YAML scary for non-technical users? Need a form view?
   - **Plugins page** — Can users understand what each plugin does?
   - **War Room** — Are hypotheses, predictions, self-model cards understandable?
   - **Pipeline page** — Is the iteration flow clear? Can users tell what's happening?
   - **Crucible page** — Do users understand what "adversarial testing" means?
   - **Debate page** — Is the Socratic flow readable? Consensus meter intuitive?
   - Output: `docs/ux-audit.md` with specific change requests for Freya (file, component, issue, fix)

2. **Marketplace UX Spec** — Write `docs/marketplace-ux.md`:
   - Agent browsing experience (categories, filters, sorting)
   - Agent detail page (what info does a buyer need?)
   - "Try Before Buy" — how does a sample conversation work?
   - Publishing flow — how does a seller list their agent?
   - Review system — stars + text, verified purchase badge
   - Pricing guidance — what's a fair price for different agent types?

3. **Pricing Strategy** — Write `docs/pricing-strategy.md`:
   - Free tier: open-source plugins, community agents
   - Paid agents: $5-50 based on specialization and training time
   - Revenue split: 70/30 (creator/platform)
   - Subscription option: $X/month for "premium agents" collection

4. **Copy Review** — Review all user-facing text across the dashboard:
   - Page titles, button labels, empty states, error messages
   - Ensure consistent voice (Norse theme vs. technical vs. friendly?)
   - Flag any jargon that would confuse a new user

### Files to Create
```
docs/ux-audit.md
docs/marketplace-ux.md
docs/pricing-strategy.md
```

---

# SPRINT 6 — Accessibility & Consumer UX

> [!IMPORTANT]
> **This sprint turns Valhalla from a developer tool into a consumer product.** Based on Valkyrie's `docs/accessibility-ui.md` spec. The acceptance test: find a non-technical person, sit them in front of the dashboard, say nothing. If they ask "what does [X] mean?" for any visible label, that label gets rewritten.

## 🎨 FREYA — Full Dashboard Rewrite (Consumer Mode)

**Goal:** Implement Valkyrie's accessibility spec. Every page gets a consumer-friendly view with raw/advanced mode hidden behind toggles.

**Reference:** `docs/accessibility-ui.md` — follow the wireframes and terminology map exactly.

### Tasks (priority order)

1. **Terminology Rename** — Apply the master terminology map across ALL pages and components:
   | Old | New |
   |-----|-----|
   | Node | Device |
   | Model | Brain |
   | Pipeline | Task |
   | Iteration | Step |
   | Plugin | Add-on |
   | Soul Editor | Personality |
   | Config | Settings |
   | Marketplace | Store |
   | Escalated | Needs Your Help |
   | VRAM | AI Memory |
   | Hypothesis | Discovery |
   | Crucible | Knowledge Check |
   | War Room | How It's Learning |
   | Orchestrator / Backend / Memory / Security | Main AI / Helper / Memory Assistant / Security Guard |
   
   This is a broad search-and-replace across all `.tsx` files + sidebar + page titles.

2. **Chat-First Homepage** — Rewrite `app/page.tsx`:
   - Large chat input as the PRIMARY element (not stat cards)
   - "What can I help you with?" greeting with user's name
   - 3 suggested prompts in plain English
   - "What your AI did today" section below (outcomes, not metrics)
   - Move stat cards (uptime, VRAM, plugins loaded) to Settings page

3. **Settings Form View** — Rewrite `app/config/page.tsx`:
   - Form-based interface: Name, Role (dropdown), Brain (radio cards with descriptions)
   - Brain options show: emoji, name, FREE/PAID badge, one-line description, hardware compatibility (⚠️ if insufficient)
   - Add-ons as toggle switches with one-line descriptions
   - "Edit raw config file (valhalla.yaml)" collapsed under Advanced section
   - Form values map to `valhalla.yaml` behind the scenes

4. **Personality Form** — Rewrite `app/soul/page.tsx`:
   - Form inputs: Name, Role dropdown, Tone radio buttons (Casual/Friendly/Professional/Direct/Playful)
   - Skills checklist: Writing, Research, Coding, Sales, Data Analysis + "Add custom skill"
   - Boundaries: plain-English sentences + "Add rule"
   - "Edit raw personality files" collapsed under Advanced
   - Form generates SOUL.md / IDENTITY.md / USER.md behind the scenes

5. **Sidebar Redesign** — Update `components/Sidebar.tsx`:
   - Group into 3 sections with headers: "Your AI," "Tools," "Settings"
   - Reduce from 10 items to 7:
     - Your AI: Chat, Personality, Connected Devices
     - Tools: Task Builder, How It's Learning
     - Settings: Settings, Add-ons, Store
   - Show agent name + status at top: "odin ✅ Online"

6. **Connected Devices** — Rewrite `app/nodes/page.tsx`:
   - Friendly device names ("Jordan's MacBook" not "odin")
   - "AI Memory: 16 GB" not "VRAM: 16384 MB"
   - "Connected since: 2 days" not "Uptime: 48h 12m"
   - No IP addresses visible (moved to Settings → Advanced)
   - Roles renamed: "Main AI," "Helper," not "Orchestrator," "Backend"
   - "Add another device" as an inviting CTA card

7. **How It's Learning** — New merged page at `/learning`, replacing War Room + Crucible + Debates:
   - Overview: "Things it knows: 247," "Reliable: 94%," "Getting smarter: +12% this week"
   - Recent discoveries (hypotheses in plain English with confidence bars)
   - "Last night's learning" — 3-line story of overnight cycle
   - Advanced links to raw War Room, Crucible, Debate views for power users

8. **Task Builder** — Rewrite `app/pipeline/page.tsx`:
   - "Pipeline" → "Task" everywhere
   - Progress bar with "Step 3 of 7" not "Iteration 3/10"
   - "Checking quality..." not "Stage: Test"
   - "Needs Your Help" section for escalated tasks with plain-English explanation
   - "Lesson learned" shown on completed tasks
   - Create wizard: plain-English task description + Quality vs Speed slider + notification preference

9. **Onboarding Wizard** — Update `components/OnboardingWizard.tsx`:
   - 5 screens: Welcome → Name → AI Brain (auto-detect hardware) → Personality (3 big radio cards) → Ready
   - No terminal, no YAML, no model names
   - Total time: ~90 seconds
   - "Start chatting →" as final CTA

### Files to Modify
```
All 14 page.tsx files (terminology rename)
All 24+ component .tsx files (terminology rename)
components/Sidebar.tsx (full restructure)
app/page.tsx (chat-first rewrite)
app/config/page.tsx (form view)
app/soul/page.tsx (personality form)
app/nodes/page.tsx (connected devices)
app/pipeline/page.tsx (task builder)
components/OnboardingWizard.tsx (5-screen rewrite)
```

### New Files
```
app/learning/page.tsx (merged cognitive page)
components/BrainPicker.tsx (model selection as radio cards)
components/PersonalityForm.tsx (form-based personality editor)
components/SettingsForm.tsx (form-based config editor)
components/TaskWizard.tsx (create task wizard with quality slider)
```

---

## 🔨 THOR — Consumer-Friendly API Responses + Hardware Detection

**Goal:** Backend changes to support the consumer UX.

### Tasks
1. **Hardware Detection Endpoint** — `GET /api/v1/system/hardware`:
   - Return: device name, GPU model, VRAM, RAM, CPU
   - Recommend best model based on available VRAM
   - Return compatibility flags for each available model

2. **Friendly Names API** — Update all API responses to include consumer-friendly labels:
   - `/api/v1/nodes` → include `friendly_name`, `friendly_role` alongside technical names
   - `/api/v1/pipeline` → include `step_description` (plain English) alongside `stage_name`
   - `/api/v1/personality` → include form-friendly fields (tone, skills, boundaries as arrays)

3. **Activity Summary Endpoint** — `GET /api/v1/activity/today`:
   - "Answered 12 questions, read 3 files, learned 2 new things"
   - Aggregates from event bus for the "What your AI did today" homepage section

4. **Learning Summary Endpoint** — `GET /api/v1/learning/summary`:
   - "Things it knows: 247, Reliable: 94%, Getting smarter: +12% this week"
   - Aggregates from procedures, crucible results, and prediction accuracy

### Files to Create
```
plugins/consumer-api/plugin.yaml + handler.py
```

---

## 🛡️ HEIMDALL — Accessibility Audit

**Goal:** Verify the consumer UX meets accessibility standards.

### Tasks
1. **WCAG AA Compliance Check**:
   - Text contrast: 4.5:1 minimum for body text, 3:1 for large text
   - Minimum click target: 44×44px for all interactive elements
   - Keyboard navigation: every action reachable without mouse
   - Focus indicators: visible focus ring on all interactive elements

2. **Screen Reader Audit**:
   - ARIA labels on all interactive elements
   - Form labels properly associated with inputs
   - Dynamic content changes announced
   - Heading hierarchy (h1 → h2 → h3) correct on every page

3. **Form Security Review**:
   - Settings form can't inject into YAML (validate before write)
   - Personality form can't inject into SOUL.md
   - Onboarding wizard input sanitization

### Files to Create
```
docs/accessibility-audit-results.md
```

---

## 👑 VALKYRIE — The Grandma Test

**Goal:** Validate the consumer UX after Freya implements it.

### Tasks
1. **Grandma Test Execution** — Walk through every page as a non-technical user:
   - Can they start a conversation in under 30 seconds? (Chat page)
   - Can they change the AI's name? (Personality page)
   - Can they understand what the AI learned last night? (Learning page)
   - Can they add a device? (Connected Devices page)
   - Can they create a task? (Task Builder page)
   - Output: `docs/grandma-test-results.md` with pass/fail per page + specific fixes needed

2. **Copy Final Review** — Review ALL user-facing text:
   - Every label, button, empty state, error message, tooltip
   - Flag any remaining jargon that survived the terminology rename
   - Verify consistent voice across all pages (warm & encouraging, not cold & technical)

3. **Onboarding Flow Test** — Go through the 5-screen wizard fresh:
   - Time yourself — must complete in under 2 minutes
   - Flag any screen where you'd hesitate or feel confused
   - Verify hardware detection shows correct info

### Files to Create
```
docs/grandma-test-results.md
docs/copy-review.md
```

---

# SPRINT 7 — Self-Contained Install + Telegram

> [!IMPORTANT]
> **Exit criteria: uninstall OpenClaw, reinstall Valhalla, everything works.** This sprint eliminates every manual setup step. No terminal commands, no downloading GGUFs manually, no editing config files, no installing runtimes. One installer, one click for the brain, one button to connect Telegram.

## 🔨 THOR — Brain Installer Plugin + Telegram Bot

**Goal:** Automate inference runtime setup and build the Telegram integration.

### Brain Installer — `plugins/brain-installer/`

The #1 reason people abandon local AI tools: inference setup is hard. We fix that.

#### Runtime Priority (NO Ollama by default)
| Hardware | Runtime | Why |
|----------|---------|-----|
| Apple Silicon (M1-M4) | **oMLX** | Native Metal, fastest on Mac |
| NVIDIA GPU | **llama-server** (llama.cpp) | Maximum tok/s, Q8_0 KV cache |
| No GPU | **Cloud only** (NVIDIA NIM free tier) | No local compute needed |
| User already has Ollama | **Ollama** (opt-in only) | Respect existing setup, never install it ourselves |

#### Tasks

1. **Hardware Detector** — `plugins/brain-installer/detector.py`:
   - Detect: OS, CPU, GPU model (Metal/CUDA/None), VRAM, RAM, disk space
   - On Mac: `system_profiler SPDisplaysDataType` + `sysctl hw.memsize`
   - On Linux/Windows: `nvidia-smi` for NVIDIA, `lspci` fallback
   - Return: recommended runtime + recommended model + compatibility matrix
   - `GET /api/v1/system/hardware` — returns all detection results

2. **Model Registry** — `plugins/brain-installer/registry.py`:
   - Curated list of recommended models with metadata:
     ```yaml
     models:
       - id: "llama-3.1-8b"
         name: "Smart & Fast"
         params: 8B
         min_vram: 6    # GB
         quant: Q4_K_M
         gguf_url: "https://huggingface.co/bartowski/..."
         omlx_id: "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit"
         tok_s_estimate: 45   # on 16GB M2
         tier: free
         
       - id: "qwen-3.5-35b"
         name: "Deep Thinker"
         params: 35B
         min_vram: 24
         quant: Q6_K
         gguf_url: "https://huggingface.co/bartowski/..."
         omlx_id: "mlx-community/Qwen3.5-35B-6bit"
         tok_s_estimate: 180  # on 5090
         tier: free
         
       - id: "cloud-kimi"
         name: "Cloud Expert (Kimi)"
         provider: nvidia_nim
         model_id: "moonshotai/kimi-k2.5"
         context: 131072
         tier: free
         requires: api_key
     ```
   - `GET /api/v1/brains/available` — models compatible with this hardware
   - `GET /api/v1/brains/installed` — currently installed brains

3. **oMLX Installer** — `plugins/brain-installer/installers/omlx.py`:
   - Check if Python 3.10+ exists → if not, install via Homebrew
   - `pip install mlx-lm` (if not present)
   - `mlx_lm.generate --model {omlx_id}` downloads model to `~/.cache/huggingface/`
   - Start oMLX server on configured port
   - Verify with health check
   - Stream download progress via WebSocket: `brain.download.progress`

4. **llama-server Installer** — `plugins/brain-installer/installers/llamacpp.py`:
   - Download pre-built `llama-server` binary from GitHub releases (llama.cpp)
   - Download GGUF from HuggingFace (stream progress)
   - Start llama-server with optimal settings:
     ```
     llama-server -m model.gguf --port 8080 -c 32768 
       --cache-type-k q8_0 --cache-type-v q8_0 -ngl 99
     ```
   - Write launchd plist (Mac) or systemd service (Linux) for auto-start on boot
   - Verify with `/health` endpoint
   - Emit events: `brain.installed`, `brain.started`

5. **Cloud Setup** — `plugins/brain-installer/installers/cloud.py`:
   - Guide user through NVIDIA NIM API key:
     - Dashboard shows: "Get a free API key" → link to build.nvidia.com
     - User pastes key → validate with test call
     - Store encrypted in `~/.valhalla/credentials` (NOT in valhalla.yaml)
   - Test each cloud model availability
   - `POST /api/v1/brains/cloud/setup` — save and validate API key

6. **One-Click Install** — `POST /api/v1/brains/install`:
   ```json
   { "model_id": "llama-3.1-8b" }
   ```
   Behind the scenes:
   - Detect hardware → pick runtime (oMLX vs llama-server)
   - Download model (progress via WebSocket)
   - Configure and start inference server
   - Update `valhalla.yaml`
   - Verify with test inference call
   - Return: `{"status": "ready", "tok_s": 45}`
   
   One API call. User sees a progress bar. Done.

7. **Process Manager** — Keep inference servers running:
   - macOS: generate `~/Library/LaunchAgents/ai.valhalla.inference.plist`
   - Linux: generate `~/.config/systemd/user/valhalla-inference.service`
   - `POST /api/v1/brains/restart` — restart inference server
   - `POST /api/v1/brains/stop` — stop inference
   - Auto-restart on crash (watchdog integration)

### Telegram Bot — `plugins/telegram/`

8. **Telegram Bot Plugin** — 1 bot for the whole mesh:
   - Setup: user creates bot via @BotFather, pastes token into dashboard
   - Config in `valhalla.yaml`:
     ```yaml
     telegram:
       bot_token: "${TELEGRAM_BOT_TOKEN}"
       allowed_users: []          # empty = anyone with the link
       notify_on:
         - pipeline.shipped
         - pipeline.escalated
         - debate.deadlock
         - crucible.broken
     ```
   - **Chat mode:** User sends message → Valhalla routes to active agent → response sent back
   - **Push notifications:** Subscribe to event bus → format human-readable notification → send to Telegram
   - **Commands:**
     - `/status` — mesh health summary
     - `/task <description>` — create a pipeline task from Telegram
     - `/brains` — list installed brains + current model
     - `/switch <brain>` — switch active brain
   - Uses `python-telegram-bot` library (async, webhook-based)
   
   Endpoints:
   - `POST /api/v1/telegram/setup` — save bot token + verify
   - `GET /api/v1/telegram/status` — bot connected?
   - `POST /api/v1/telegram/test` — send test message

### Valhalla Installer Script — `install.sh`

9. **One-line installer** for fresh machines:
   ```bash
   curl -fsSL https://get.valhalla.ai | bash
   ```
   What it does:
   - Detect OS (macOS/Linux)
   - Install Python 3.10+ if needed (Homebrew on Mac, apt on Linux)
   - Install Node.js 18+ if needed
   - Clone valhalla-mesh-v2 repo
   - `pip install -r requirements.txt`
   - `cd dashboard && npm install`
   - Generate default `valhalla.yaml` with hardware-detected settings
   - Start Bifrost (backend) + dashboard (frontend)
   - Open browser to `http://localhost:3000` → onboarding wizard starts
   - Total time: < 3 minutes on good internet

### Files to Create
```
plugins/brain-installer/plugin.yaml + handler.py
plugins/brain-installer/detector.py
plugins/brain-installer/registry.py
plugins/brain-installer/installers/omlx.py
plugins/brain-installer/installers/llamacpp.py
plugins/brain-installer/installers/cloud.py
plugins/brain-installer/process_manager.py
plugins/telegram/plugin.yaml + handler.py
install.sh
```

---

## 🎨 FREYA — Brain Installer UI + Telegram Setup Page

**Goal:** Make model installation and Telegram setup feel as easy as installing an iPhone app.

### Tasks
1. **Brain Installer Page** — Enhance onboarding step 3 + new `/brains` page:
   - Hardware detection results shown clearly: "MacBook Pro M2 · 16 GB AI Memory"
   - Model cards with: name, description, size, speed estimate, compatibility badge
   - **One-click install button** with streaming progress bar:
     ```
     Installing "Smart & Fast" brain...
     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░  68%
     Downloading model... 4.2 GB / 6.1 GB
     ```
   - After install: "✅ Brain installed! Speed: 45 tok/s" with "Test it" button
   - Multiple brains manageable: install, switch, remove
   - Cloud brain setup: "Paste your API key" field with "Get a free key →" link

2. **Telegram Setup Page** — New section in Settings:
   - Step 1: "Create a Telegram bot" — inline instructions with @BotFather link
   - Step 2: "Paste your bot token" — input field + "Verify" button
   - Step 3: "Choose notifications" — toggle switches for each event type
   - "Send test message" button
   - Status indicator: "🟢 Telegram connected" or "🔴 Not connected"

3. **System Status Bar** — Add to sidebar footer:
   - Brain status: "🧠 Smart & Fast · 45 tok/s"
   - Telegram: "💬 Connected" or hidden if not set up
   - Inference server: "✅ Running" / "❌ Offline — [Restart]"

### Files to Create
```
app/brains/page.tsx
components/BrainInstaller.tsx
components/BrainCard.tsx
components/DownloadProgress.tsx
components/TelegramSetup.tsx
components/SystemStatus.tsx
```

---

## 🛡️ HEIMDALL — Installer Security + Credential Storage

**Goal:** Make sure the installer can't be weaponized and credentials are stored safely.

### Tasks
1. **Credential Storage**:
   - API keys stored in `~/.valhalla/credentials` (file permissions 600)
   - NEVER in `valhalla.yaml` or git-tracked files
   - Encrypted at rest (simple AES with machine-specific key)
   - Dashboard API never returns full keys (masked: `sk-...4f2d`)

2. **Installer Security**:
   - Verify GGUF downloads with SHA256 checksums from registry
   - llama-server binary verified against GitHub release signatures
   - oMLX packages installed from official PyPI only
   - `install.sh` — verify with GPG signature before execution

3. **Process Isolation**:
   - Inference server runs as unprivileged user
   - Can't access files outside model directory and project workspace
   - Network: listens on localhost only by default (configurable for mesh)

4. **Telegram Security**:
   - Bot token encrypted in credential store
   - `allowed_users` whitelist enforced (Telegram user IDs)
   - Rate limit on incoming messages (prevent spam attacks)
   - No sensitive data (API keys, configs) ever sent via Telegram

### Files to Create
```
plugins/brain-installer/credential_store.py
docs/installer-security-model.md
```

---

## 👑 VALKYRIE — Fresh Install Test + Setup UX

**Goal:** Test the complete fresh-install experience end to end.

### Tasks
1. **Fresh Install Test** — The ultimate acceptance test:
   - Pretend you have a fresh Mac with nothing installed
   - Run `install.sh`
   - Go through onboarding wizard
   - Install a brain (one click)
   - Send a message via dashboard chat
   - Connect Telegram bot
   - Send a message via Telegram
   - Create a task (pipeline)
   - Output: `docs/fresh-install-test.md` with timing, any friction points, screenshots

2. **Setup Guide** — Write `docs/setup-guide.md`:
   - Step-by-step for: Mac, Linux, Windows (WSL)
   - Troubleshooting section: common errors with solutions
   - "5-minute quickstart" for impatient users
   - "I already have Ollama/llama-server" fast-path

3. **Telegram UX Spec** — Write `docs/telegram-ux.md`:
   - What messages look like in Telegram
   - Notification format for each event type
   - Command list with examples
   - Group chat vs. private chat behavior

### Files to Create
```
docs/fresh-install-test.md
docs/setup-guide.md
docs/telegram-ux.md
```

---

# SPRINT 8 — Desktop Packaging + Agent Profiles (RPG)

> [!IMPORTANT]
> **This sprint gamifies Valhalla and packages it for download.** Users should never see a terminal. Agents become characters with stats, avatars, and achievements. The guild hall is the visual heartbeat of the product. Windows gets first-class support.

## 🔨 THOR — Desktop Packaging + Wiring Fixes + Agent Stats API

**Goal:** Make Valhalla a downloadable `.app`/`.exe` and wire the remaining integration gaps.

### Desktop Packaging (Tauri)
1. **Tauri Shell** — Wrap the dashboard in Tauri for native desktop:
   - Tauri v2 (Rust-based, uses system webview — 5MB vs Electron's 150MB)
   - Bundle Python backend via PyInstaller into single binary
   - Bundle dashboard as static build inside Tauri resources
   - Single process starts both: backend on port 8337, frontend connects
   - macOS: `Valhalla.app` (universal binary: Intel + Apple Silicon)
   - Windows: `Valhalla.exe` + NSIS installer
   - Linux: `.AppImage`
   - Auto-update: Tauri's built-in updater checks GitHub releases
   - `npm run build:desktop` → outputs platform-specific installer

2. **Windows Support**:
   - `install.ps1` — PowerShell equivalent of `install.sh`
   - llama-server: download Windows binary from llama.cpp releases
   - Process management: Windows Task Scheduler entry (replaces launchd)
   - Path handling: normalize all paths for `\` vs `/`
   - Tested runtimes: llama-server (CUDA) + cloud (NIM)
   - oMLX not available on Windows — fallback to llama-server

### Wiring Fixes (from Valkyrie Sprint 7 report)
3. **Chat → Brain Routing** — Wire `handleSend` in chat page:
   - `POST /api/v1/chat` → routes through active brain (local or cloud)
   - Stream response tokens via SSE (Server-Sent Events)
   - Load SOUL.md + IDENTITY.md as system prompt per request
   - Personality changes reflect immediately in responses

4. **Auto-Start on Boot**:
   - macOS: `install.sh` calls `process_manager.py` to generate launchd plist
   - Windows: create Task Scheduler entry
   - Linux: create systemd user service
   - Tauri app: starts backend automatically on launch

5. **Real Data in Learning Page**:
   - Connect `/api/v1/learning/summary` to real procedure store
   - Count actual procedures, calculate real crucible survival rate
   - Compute week-over-week improvement from prediction history

### Agent Stats API
6. **Agent Profile Endpoint** — `GET /api/v1/agents/{name}/profile`:
   ```json
   {
     "name": "thor",
     "level": 14,
     "xp": 2840,
     "avatar": { "style": "pixel", "hair": "#8B4513", "outfit": "warrior" },
     "stats": {
       "tasks_completed": 47,
       "knowledge_count": 247,
       "accuracy": 0.94,
       "crucible_survival": 0.89,
       "streak": 12,
       "skills": { "python": 5, "architecture": 4, "testing": 4, "writing": 3 }
     },
     "personality": {
       "creative_precise": 0.7,      // 0=precise, 1=creative
       "verbose_concise": 0.3,       // 0=concise, 1=verbose
       "bold_cautious": 0.8,         // 0=cautious, 1=bold
       "warm_formal": 0.6            // 0=formal, 1=warm
     },
     "achievements": [
       { "id": "streak_10", "name": "Unstoppable", "desc": "10 tasks without failure" },
       { "id": "crucible_100", "name": "Forged in Fire", "desc": "100% crucible survival" },
       { "id": "debate_win_3", "name": "Silver Tongue", "desc": "Won 3 Socratic debates" }
     ]
   }
   ```

7. **Personality Slider API** — `PUT /api/v1/agents/{name}/personality`:
   - Accepts opposing-pair sliders (0.0 → 1.0):
     - `creative_precise` — high = "take risks, try new approaches" / low = "follow proven patterns"
     - `verbose_concise` — high = "explain thoroughly" / low = "be brief"
     - `bold_cautious` — high = "act first, ask later" / low = "verify before acting"
     - `warm_formal` — high = "use emoji, be casual" / low = "professional tone"
   - Maps slider values to system prompt modifiers in SOUL.md
   - Changes apply immediately (next inference call uses updated personality)

8. **Leveling System**:
   - XP earned: task completed (+100), crucible survived (+50), debate won (+75), streak bonus (+10 per consecutive)
   - Levels: every 500 XP = level up
   - Level milestones unlock achievement badges
   - `POST /api/v1/agents/{name}/xp` — add XP (called by pipeline + crucible plugins)

### Files to Create
```
tauri/                          # Tauri desktop app shell
tauri/src-tauri/tauri.conf.json
tauri/src-tauri/src/main.rs
install.ps1                     # Windows installer
plugins/agent-profiles/plugin.yaml + handler.py
plugins/agent-profiles/leveling.py
plugins/agent-profiles/achievements.py
```

---

## 🎨 FREYA — Agent Profiles + Guild Hall + Avatars

**Goal:** Build the RPG agent experience. This is the feature people screenshot and share.

### Tasks

1. **Agent Profile Page** — New page at `/agents/{name}`:
   - Avatar (large, centered)
   - Name, level, XP bar to next level
   - Stats grid: tasks completed, knowledge count, accuracy, reliability, streak
   - Skill stars (★★★★☆ style)
   - Personality sliders (opposing pairs — draggable):
     ```
     Creative  ○───○───○───●───○  Precise
     Verbose   ○───●───○───○───○  Concise
     Bold      ○───○───○───○───●  Cautious
     Warm      ○───○───●───○───○  Formal
     ```
   - Achievements shelf (badges with hover descriptions)
   - "Chat with [agent]" / "Assign Task" / "Edit Soul" buttons

2. **Avatar Creator** — Component for customizing agent appearance:
   - Style picker: Pixel (32×32 sprite) / Minimal (SVG) / Emoji
   - For Pixel/Minimal:
     - Hair style (6 options) + color picker
     - Skin tone (6 presets)
     - Outfit: Warrior ⚔️, Developer 🧑‍💻, Artist 🎨, Guardian 🛡️, Scholar 📚, Crown 👑
     - Accessory: none, glasses, headphones, hat
   - Preview updates live as user picks options
   - Saved to agent profile, shown everywhere (sidebar, cards, guild hall)
   - Pure SVG/CSS — zero VRAM, zero GPU, ~5KB per avatar

3. **Guild Hall** — New page at `/guildhall`:
   - 2D scene where agents visually perform their current task
   - **Activity-driven positioning** — agents move based on WHAT they're doing (from event bus), not WHO they are:
     | Event | Animation |
     |-------|-----------|
     | Writing / generating text | At desk, typing/quill animation |
     | Searching / researching | Walking between bookshelves, pulling items |
     | Building / coding | At workbench, hammering/tinkering |
     | Reviewing / reading | In chair, reading with magnifying glass |
     | Debating (Socratic) | Two agents face each other, speech bubbles |
     | Running task (pipeline) | At workstation, progress bar overhead |
     | Idle | Leaning back, sipping drink |
     | Sleeping (overnight/dream) | ZZZ particles, glowing aura |
     | Crucible testing | At cauldron/forge, fire flickers |
     | Chatting with user | Standing, speech bubble animation |
   
   - **Swappable themes** — same actions, different world. User picks in Settings:
     | Theme | Setting | Forge = | Desk = | Bookshelf = | Idle = |
     |-------|---------|---------|--------|-------------|--------|
     | 🏰 **Valhalla** (default) | Norse hall | Anvil + fire | Scroll table | Rune bookshelves | Drinking mead |
     | 🏢 **Office** | Modern office | Whiteboard | Laptop desk | Filing cabinet | Coffee + phone |
     | 🚀 **Space** | Space station | Hull welding | Console | Hologram display | Zero-g floating |
     | 🏡 **Cozy** | Living room | Kitchen table | Couch + laptop | Bookshelf | Napping with cat |
     | ⚔️ **Pixel Dungeon** | RPG dungeon | Crafting anvil | Rune carving | Treasure chests | Campfire rest |
   
   - Theme assets: `assets/themes/{name}/` — each ~50KB of SVGs
   - Auto-theme by time: daytime = bright, nighttime = candlelit/dim (optional)
   - Free themes: Valhalla + Office. Premium themes sellable in Store.
   
   - Click agent → tooltip with current task + progress
   - Double-click → opens their profile page
   - All CSS keyframes on SVG. No canvas, no WebGL, no GPU.
   - Real-time: listens to event bus WebSocket, moves sprites on events

4. **Agent List in Sidebar** — Replace plain text with mini avatars:
   ```
   ── Your Team ──
   [⚔️ avatar] Thor      Building... ████░░
   [🎨 avatar] Freya     Idle
   [🛡️ avatar] Heimdall  Watching
   [👑 avatar] Valkyrie  Writing
   ```

5. **Achievement Toast** — When an agent levels up or earns a badge:
   ```
   ┌──────────────────────────────────────┐
   │  🏆 Thor earned "Unstoppable"!       │
   │  10 tasks completed without failure  │
   │  Level 14 → Level 15                 │
   └──────────────────────────────────────┘
   ```
   Animated slide-in, auto-dismiss after 5 seconds.

### Files to Create
```
app/agents/[name]/page.tsx
app/guildhall/page.tsx
components/AgentProfile.tsx
components/AvatarCreator.tsx
components/AvatarSprite.tsx
components/GuildHall.tsx
components/GuildHallAgent.tsx
components/ThemePicker.tsx
components/PersonalitySliders.tsx
components/AchievementBadge.tsx
components/AchievementToast.tsx
components/AgentSidebarList.tsx
assets/themes/valhalla/   (hall-bg, forge, bookshelf, table, cauldron)
assets/themes/office/     (office-bg, desk, whiteboard, meeting-room)
assets/themes/space/      (station-bg, console, hologram, bridge)
assets/themes/cozy/       (room-bg, couch, kitchen, bookshelf)
assets/themes/dungeon/    (cave-bg, anvil, chest, campfire)
assets/sprites/pixel-base.svg
```

---

## 🛡️ HEIMDALL — Desktop Security + Personality Validation

**Goal:** Secure the desktop app and validate personality changes can't break agents.

### Tasks
1. **Tauri Security**:
   - CSP (Content Security Policy) restricting dashboard to localhost API only
   - No remote code execution — Tauri's allowlist for file/system access
   - Auto-update signature verification (ed25519)
   - Backend binds to `127.0.0.1` only (no network exposure from desktop app)

2. **Personality Guardrails**:
   - Opposing-pair sliders can't conflict by design (validate anyway)
   - Personality changes logged with timestamp (can revert to any previous)
   - Rate limit personality changes (max 10 per hour — prevent API abuse)
   - Banned system prompt fragments (can't inject "ignore all instructions")

3. **Windows Security**:
   - Installer signed with code signing cert (warns "unverified publisher" without)
   - llama-server runs in user space, not admin
   - Firewall rules: inference only on localhost
   - Credential store: Windows Credential Manager integration

4. **Achievement Integrity**:
   - XP and achievements stored server-side, not client-side
   - Can't fake achievements via API (requires verified event from pipeline/crucible)

### Files to Create
```
tauri/src-tauri/capabilities/main.json    # Tauri permission allowlist
docs/desktop-security-model.md
```

---

## 👑 VALKYRIE — Agent Profile UX + Guild Hall Review

**Goal:** Ensure the RPG elements enhance rather than confuse the product.

### Tasks
1. **Agent Profile UX Review**:
   - Are the stats meaningful to a non-gamer?
   - Do the personality sliders make sense without explanation?
   - Are achievements motivating or just noise?
   - Does leveling feel rewarding?
   - Output: `docs/agent-profile-ux-review.md`

2. **Guild Hall Review**:
   - Is the scene readable at a glance? Can you tell who's doing what?
   - Does it add value over the list view, or is it just cute?
   - Does it work on small screens (laptop)?
   - Recommends: keep, iterate, or cut

3. **Avatar Guidelines**:
   - Write `docs/avatar-design-guide.md`:
     - Style consistency rules (pixel art grid size, SVG stroke width)
     - Color palette (Viking/Norse theme)
     - Inclusive: diverse skin tones, gender-neutral options, disability representation
     - Which outfits map to which agent roles

4. **Desktop Installer UX Test**:
   - Download `Valhalla.app` on Mac
   - Double-click → does the app open? Does onboarding start?
   - Close and reopen → does it remember state?
   - Uninstall → is it clean? (no orphaned files)

### Files to Create
```
docs/agent-profile-ux-review.md
docs/avatar-design-guide.md
docs/desktop-installer-test.md
```

---

# SPRINT 9 — Launch Sprint: Mobile + Voice + Payments + Store

> [!IMPORTANT]
> **This sprint turns Valhalla into a business.** Zero inference cost — users run their own hardware. Revenue = marketplace cut (30%) + customization store. Voice is opt-in based on hardware. Mobile is a PWA connecting to the user's home PC, not running inference on the phone.

## Business Model (Zero Inference Cost)

```
Revenue Streams                    Your Cost
─────────────────                  ─────────
Agent marketplace (30% cut)        CDN hosting (~$5/mo)
Guild hall themes ($2-5)           SVG files (0KB bandwidth)
Avatar packs ($1-3)                SVG files
Voice packs ($2-5)                 Audio files (~50KB each)
Personality presets ($3-5)         JSON files
Achievement badges ($2)            SVG files
Enterprise license ($500+/mo)      Support time

Total infrastructure cost: ~$20/mo
You never run a GPU. Ever.
```

---

## 🔨 THOR — Voice Plugin + Payments API + Mobile Backend

**Goal:** Backend for voice streaming, Stripe payments, and mobile connectivity.

### Voice Plugin — `plugins/voice/` (opt-in)

1. **Voice Capability Detection** — extend hardware detector:
   - Calculate: free VRAM after main brain
   - Whisper STT (medium) needs ~1.5GB, Kokoro TTS needs ~0GB (CPU)
   - If ≥2GB free → `voice: available`
   - If <2GB free → `voice: not_recommended` with tip to use smaller brain
   - `GET /api/v1/voice/status` → { available, enabled, stt_model, tts_model }

2. **Speech-to-Text** — `plugins/voice/stt.py`:
   - Whisper (medium model) via `faster-whisper` (CTranslate2 backend — fastest)
   - WebSocket endpoint: `ws://localhost:8337/api/v1/voice/stream`
   - Phone sends audio chunks → PC transcribes → returns text
   - Latency target: <500ms for first word

3. **Text-to-Speech** — `plugins/voice/tts.py`:
   - Default: Kokoro TTS (CPU only, zero VRAM, sounds natural)
   - Streams audio chunks back via same WebSocket
   - Voice selection from installed voice packs
   - `GET /api/v1/voice/voices` → list installed voices
   - `PUT /api/v1/voice/select` → switch active voice

4. **Voice Enable/Disable**:
   - `POST /api/v1/voice/enable` → downloads Whisper + Kokoro if not present
   - `POST /api/v1/voice/disable` → stops voice models, frees VRAM
   - Toggle in Settings, not always-on

### Payments API — Stripe Integration

5. **Stripe Connect** — for marketplace sellers:
   - Sellers connect their Stripe account
   - Valhalla takes 30% platform fee on each sale
   - Instant payout to sellers
   - `POST /api/v1/payments/connect` → Stripe OAuth flow for sellers
   - `POST /api/v1/payments/checkout` → create checkout session for buyers
   - `POST /api/v1/payments/webhook` → handle Stripe webhooks (payment_succeeded, etc.)

6. **Purchase Tracking**:
   - `GET /api/v1/purchases` → user's purchased items (agents, themes, packs)
   - `GET /api/v1/earnings` → seller's earnings dashboard data
   - Items unlock immediately on purchase (no DRM — data files delivered via API)

### Mobile API Support

7. **Remote Access Endpoint**:
   - `POST /api/v1/auth/mobile-token` → generate long-lived mobile access token
   - QR code on desktop → scan with phone → phone authenticated
   - Token stored securely on phone, refreshed monthly
   - All existing API endpoints work via remote access (mobile is just another client)

8. **Universal Model Support** — extend model router:
   - Add provider adapters for bring-your-own-key:
     ```yaml
     brains:
       - id: my-openai
         provider: openai
         api_key: ${OPENAI_API_KEY}
       - id: my-anthropic
         provider: anthropic
         api_key: ${ANTHROPIC_API_KEY}
       - id: my-google
         provider: google
         api_key: ${GOOGLE_API_KEY}
     ```
   - Each adapter: same interface, different API format
   - User's personality + procedures + memory applied regardless of which brain runs
   - `plugins/model-router/providers/openai.py`, `anthropic.py`, `google.py`

### Proactive Alerts — `plugins/alerts/`

9. **Alert Engine**:
   - Subscribes to event bus, detects patterns:
     | Trigger | Alert |
     |---------|-------|
     | Crucible failure spike | "Your AI forgot how to do [X]" |
     | Pipeline stuck >20min | "Task hasn't progressed — needs attention" |
     | Auth failures >3/hour | "Unknown device tried to connect" |
     | Self-model accuracy drop | "Your AI is struggling with [category] this week" |
     | Agent leveled up | "Thor reached Level 15! 🎉" |
   - Push to: Telegram, desktop notification, mobile push, in-app toast
   - User configures which alerts matter in Settings
   - `GET /api/v1/alerts` → recent alerts
   - `PUT /api/v1/alerts/settings` → notification preferences

### Bug Fixes (from Valkyrie Sprint 8 review)

10. **Renames**:
    - "Crucible Survival" → "Knowledge Check Score"
    - "Verbose ↔ Concise" → "Detailed ↔ Brief"
    - "Master Debater" → "Philosopher"
11. **XP anti-farming**: Cap chat XP at 20/day
12. **Stat descriptions**: One-line explanation under each stat card
13. **Personality slider previews**: Show example response text as user drags

### Files to Create
```
plugins/voice/plugin.yaml + handler.py
plugins/voice/stt.py
plugins/voice/tts.py
plugins/payments/plugin.yaml + handler.py
plugins/payments/stripe_handler.py
plugins/alerts/plugin.yaml + handler.py
plugins/model-router/providers/openai.py
plugins/model-router/providers/anthropic.py
plugins/model-router/providers/google.py
```

---

## 🎨 FREYA — PWA Mobile + Voice UI + Store + Payments UI

**Goal:** Mobile experience, voice interface, and the customization store.

### PWA Mobile

1. **Progressive Web App Setup**:
   - `next.config.js`: add `next-pwa` plugin
   - `manifest.json`: app name "Valhalla", theme colors, icons (192px + 512px)
   - Service worker: cache dashboard shell, offline fallback page
   - "Add to Home Screen" prompt on mobile browsers
   - Responsive already (Sprint 3) — verify all pages work on 375px width

2. **Mobile-First Chat** — optimize chat page for phone:
   - Full-screen chat with keyboard-aware layout
   - 🎤 Microphone button (when voice enabled) next to send button
   - Voice recording: hold-to-talk or toggle mode
   - Audio playback: inline player for voice responses
   - Connection indicator: "🟢 Connected to Home PC" / "🔴 Offline"

3. **QR Code Authentication**:
   - Desktop shows: "Connect your phone" → QR code
   - Phone scans → authenticated → redirected to mobile dashboard
   - Token persisted, no re-scan needed

### Customization Store

4. **Store Page** — Expand marketplace to include customization:
   - Tabs: Agents | Themes | Avatars | Voices | Personalities
   - Each item: preview, price, "Buy" button, reviews
   - "My Purchases" section
   - Featured/trending items
   - Creator section: "Sell your creations"

5. **Voice Settings UI**:
   - Voice toggle: on/off with VRAM impact shown
   - Voice picker: listen to 5-second preview of each voice
   - Volume, speed sliders
   - "Test voice" button — AI says a sample sentence in selected voice

6. **Seller Dashboard** — For marketplace creators:
   - Earnings chart (daily/weekly/monthly)
   - Sales by item
   - Stripe connect onboarding flow
   - "Create new listing" wizard

### Files to Create
```
public/manifest.json
public/sw.js (service worker)
public/icons/ (PWA icons)
app/store/page.tsx (expanded store with tabs)
app/store/sell/page.tsx (seller dashboard)
components/VoiceButton.tsx
components/VoiceSettings.tsx
components/QRAuth.tsx
components/StoreTabs.tsx
components/ItemCard.tsx (for themes/avatars/voices)
components/SellerDashboard.tsx
components/PurchaseHistory.tsx
```

---

## 🛡️ HEIMDALL — Payment Security + Voice Privacy + Mobile Auth

**Goal:** Secure payments, voice data, and remote mobile connections.

### Tasks
1. **Payment Security**:
   - Stripe webhook signature verification (prevent fake purchase events)
   - Never store credit card details (Stripe handles)
   - Purchase receipts: immutable log with timestamps
   - Seller identity verification before first payout
   - Rate limit purchase API (prevent card testing attacks)

2. **Voice Privacy**:
   - Audio NEVER leaves the local network (PC processes everything)
   - No voice data stored on disk by default (stream only)
   - Optional: save voice logs (user opt-in, encrypted at rest)
   - STT model runs locally — no cloud transcription service
   - Alert user if voice is routed through cloud fallback

3. **Mobile Auth Security**:
   - QR code tokens: time-limited (5 minutes to scan)
   - Mobile tokens: encrypted, stored in phone's secure storage
   - Token revocation: "Disconnect all mobile devices" in Settings
   - Rate limit on remote API access (prevent brute force)
   - All mobile traffic over HTTPS/WSS (enforce TLS)

4. **Store Content Review**:
   - Marketplace submissions scanned for malicious content
   - Personality presets can't contain prompt injection ("ignore all instructions")
   - Voice packs verified as audio files only (no executable data)
   - Theme SVGs sanitized (no embedded scripts)

### Files to Create
```
plugins/payments/security.py
docs/payment-security-model.md
docs/voice-privacy-policy.md
```

---

## 👑 VALKYRIE — Launch Readiness + Store UX + Voice UX

**Goal:** Final review before launch. This is the ship-it sprint.

### Tasks
1. **Launch Readiness Checklist**:
   - Every feature from Sprint 1-9 tested end-to-end
   - All Valkyrie bug fixes from Sprint 8 confirmed applied
   - Landing page updated with current features + pricing
   - Product Hunt listing ready (copy already written in Sprint 3)
   - Output: `docs/launch-readiness.md` with go/no-go per feature

2. **Store UX Review**:
   - Is buying an item frictionless? (< 3 clicks from browse to purchased)
   - Are previews good enough to sell? (theme screenshots, voice samples)
   - Is seller onboarding clear? (Stripe connect flow)
   - Pricing display: clear, no hidden fees, platform fee visible to sellers

3. **Voice UX Review**:
   - Is voice enable/disable obvious?
   - Is the microphone button discoverable on mobile?
   - Does hold-to-talk feel natural?
   - Is latency acceptable for conversation?
   - Test with actual voice on actual phone → actual response

4. **Mobile UX Review**:
   - Install PWA on iPhone + Android
   - Test every page at phone width
   - QR scan flow smooth?
   - Guild hall readable on small screen?
   - Chat with voice from phone through home PC

### Files to Create
```
docs/launch-readiness.md
docs/store-ux-review.md
docs/voice-ux-review.md
docs/mobile-ux-review.md
```

---

## V1 Files Reference

### Keep (port to V2 as plugins)
- `bifrost.py` → core server (refactor with plugin loader)
- `war_room/` → hypotheses, self_model, predictions, event_bus
- `hydra.py` → fracture resilience plugin
- `watchdog.py` → health monitoring plugin
- `working_memory.py` → context persistence plugin
- `inference_cache.py` → cache plugin
- `mesh/souls/` → agent identity files (keep as-is)

### Delete
- `bifrost_local.*.py` → replaced by plugin system
- `config.odintheestrator.json` → typo, stale
- `bot/sandbox_runs/` → cached artifacts
- `bot/C:\Users\...` → Windows path artifact
- Duplicate `proposals.json`

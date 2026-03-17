# Pipeline UX — The Orchestration Engine

---

## How Pipelines Work

The user **just talks**. The system does the rest.

```
User: "Draft a letter to the board about our Q4 results"
  ↓
orchestrator.classify() → "complex"
  ↓
classify_template() → "drafting" (matched "draft", "letter")
  ↓
mesh_active()? → single-node → local sub-agents with system prompts
              → multi-node  → War Room dispatch to real agents
  ↓
Pipeline runs: context → draft → review (on_fail: goto:draft)
  ↓
User gets a polished letter
```

There is no "create pipeline" button in the default flow. The user types a message in chat, the AI decides it's complex, picks the right template, and runs it. The dashboard wizard exists for power users who want manual control.

---

## Template Auto-Detection

The system ships 6 built-in templates. The right one is selected automatically based on what the user says:

| User Says | Template | Stages |
|---|---|---|
| "Build me an API" | ⚡ **Coding** | spec → build ═ (parallel backend + frontend) → test → review |
| "Research AI safety" | 🔍 **Research** | gather → analyze → write |
| "Draft a letter to investors" | ✉️ **Drafting** | context → draft → review |
| "Make a presentation about Q4" | 📊 **Presentation** | outline → content → design → review |
| "Show me the trends in our data" | 📈 **Analysis** | gather → analyze → insights → report |
| "Help me organize my day" | 📋 **General** | plan → execute → review |

**How detection works:** Zero-latency keyword scoring. Each template has signal words (e.g., "api", "backend", "deploy" → Coding). Highest score wins. No match → General. Users can also create custom templates in `~/.valhalla/pipelines/`.

---

## Single-Node vs Multi-Node

The same template works in both modes. The orchestrator auto-detects:

### Single-Node (most users)
No mesh peers → **local sub-agents**:
- Each stage role becomes a system prompt personality
- "backend" → "You are a backend engineer. You build APIs, databases..."
- "reviewer" → "You are a quality reviewer. You check for completeness..."
- All stages run on the same local model (omlx / llama.cpp)
- Stages are chained: each stage receives the previous stage's output

### Multi-Node (mesh users)
Mesh peers detected → **War Room dispatch**:
- Each stage role maps to a real node via `bot/router.py`
- "backend" → Thor (best backend skills, checked via VRAM load)
- Parallel stages run on different GPUs simultaneously
- Huginn generates the spec, Muninn distills lessons
- Nodes talk to each other via the War Room, not through a central orchestrator

---

## Failure Handling (on_fail)

Each stage has an `on_fail` action that fires when a stage returns VERDICT: FAIL:

| Action | What Happens |
|---|---|
| `retry` | Retry the same stage (default) |
| `goto:build` | Jump back to the build stage with the failure feedback |
| `stop` | Halt the pipeline, escalate to human |

Built-in routing:
- **Coding:** test fails → goto:build, review fails → goto:test
- **Research:** analysis fails → goto:gather (re-research)
- **Drafting:** review fails → goto:draft (rewrite)
- **Presentation:** review fails → goto:content (revise slides)
- **Analysis:** insights fail → goto:analyze (re-analyze)
- **General:** review fails → goto:execute (redo)

---

## Dashboard: Creating a Pipeline (Power Users)

### Default Path (from Chat)
The user types something complex → pipeline auto-creates → they watch it on the Pipeline page.

### Manual Path (Dashboard Wizard)
From the **Pipeline** page, click **+ New Pipeline**:

```
┌────────────────────────────────────────────────────┐
│  ⚡ New Pipeline                            [ × ]  │
│                                                    │
│  What should we build?                             │
│  ┌──────────────────────────────────────────┐      │
│  │ Build a real-time chat app with auth     │      │
│  └──────────────────────────────────────────┘      │
│  ↑ As they type, template auto-selects below       │
│                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ ⚡ Code  │ │ 🔍 Rsrch │ │ ✉️ Draft │           │
│  │  ●═●─●─● │ │  ●─●─●   │ │  ●─●─●   │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 📊 Pres  │ │ 📈 Anlys │ │ 📋 Genrl │           │
│  │  ●─●─●─● │ │  ●─●─●─● │ │  ●─●─●   │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│  ↑ selected card: neon border + glow               │
│                                                    │
│  Stage Preview:                                    │
│  Spec → Build ═══ → Test → Review                  │
│         ├ Backend                                  │
│         └ Frontend                                 │
│                                                    │
│  Max Iterations: [━━━━━●━━━━━] 3  ▸ Advanced      │
│                                                    │
│  [ Cancel ]               [ ⚡ Create Pipeline ]   │
└────────────────────────────────────────────────────┘
```

**UX Rules:**
- Template cards auto-highlight as the user types (live keyword detection)
- Selected card: neon green border + `box-shadow: 0 0 20px rgba(0, 255, 136, 0.15)`
- Cards on hover: `translateY(-2px)` with shadow lift
- Stage preview uses `StageTimeline` component, stagger-in animation (50ms/stage)
- "Advanced" expands: stage toggles, on_fail overrides, model selection per stage
- On mobile: cards stack 1-column, stage preview scrolls horizontal, button sticky at bottom

### Stage Configuration (Advanced, Optional)

Clicking "Advanced" expands:

```
┌────────────────────────────────────────────────────┐
│  Stages                                            │
│                                                    │
│  1. ☑ Spec     role: planner   on_fail: retry      │
│  2. ☑ Build    ═ parallel      on_fail: retry      │
│  3. ☑ Test     role: tester    on_fail: goto:build  │
│  4. ☑ Review   role: reviewer  on_fail: goto:test   │
│                                                    │
│  Each stage can be toggled on/off. On_fail can      │
│  be changed to: retry | goto:[stage] | stop        │
└────────────────────────────────────────────────────┘
```

Most users leave this alone. Defaults are good.

---

## Watching a Pipeline Run

### Pipeline Card (List View)

```
┌────────────────────────────────────────────────────┐
│  🔄 Add user auth to the API          Iteration 3  │
│                                                    │
│  ▇▇▇▇▇▇▇▇▇░░░░░░░░░░░  Stage: Test   30%         │
│                                                    │
│  Spec ✔ → Build ✔ → Test 🔄 → Review              │
│                                                    │
│  Template: ⚡ Coding  ·  ETA: ~12 min              │
│  Mode: 🖥️ Local sub-agents                         │
│                                    [ View Details ] │
└────────────────────────────────────────────────────┘
```

### Pipeline Detail View (`/pipeline/{id}`)

```
┌────────────────────────────────────────────────────────────┐
│  ⚡ Add user auth to the API                              │
│  Status: Running · Iteration 3/10 · Started 14 min ago    │
│  Template: Coding · Mode: Local sub-agents                │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Stage Timeline                                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  ✔ Spec      ✔ Build     🔄 Test      ○ Review            │
│  (planner)   (═ parallel) (tester)    (reviewer)           │
│                                                            │
│  Iteration History                                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Iteration 3 (current)                              │  │
│  │  Stage: Test · Role: tester                         │  │
│  │  Running tests... 12/18 passing                     │  │
│  │  on_fail: goto:build                                │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Iteration 2 · PROGRESS                             │  │
│  │  on_fail triggered: goto:build (test failed)        │  │
│  │  Build fixed 4 of 6 test failures.                  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Iteration 1 · FAIL                                 │  │
│  │  6 tests failed. Missing JWT secret config.         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  [ Cancel Pipeline ]              [ Force Advance ]        │
└────────────────────────────────────────────────────────────┘
```

**Real-time updates:** Detail view subscribes to `WS /api/v1/events/stream`. No polling.

---

## Socratic Debate (In-Pipeline Review)

When review stages fire, the AI debates itself using different role perspectives:

```
┌──────────────────────────────────────────────────────────┐
│  🗣️ Socratic Review — Design Stage                      │
│  Round 2/3 · Consensus: 45%                              │
│  ━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░  45%                │
│                                                          │
│  🏛️ Planner (spec)                                       │
│  "The auth middleware is solid but the token refresh      │
│  flow has a race condition..."                           │
│                                                          │
│  😈 Tester (quality)                                     │
│  "What happens in 6 months when you have 50 endpoints?   │
│  This middleware pattern requires manual annotation..."   │
│                                                          │
│  👤 Reviewer (final)                                      │
│  "The error messages are cryptic. 'Invalid JWT' tells     │
│  me nothing..."                                          │
│                                                          │
│  [ 🖐️ Intervene — Add Your Take ]                       │
└──────────────────────────────────────────────────────────┘
```

**Human intervention:** Click **Intervene** to add your own input to the debate.

---

## Escalation

When regression is detected (on_fail: stop, or max iterations reached):

### Dashboard Notification
```
┌──────────────────────────────────────┐
│  ⚠️ Pipeline Escalated              │
│  "Add user auth" — Regression at    │
│  iteration 5. Human review needed.  │
│  [ View Pipeline ]                   │
└──────────────────────────────────────┘
```

### Options
- **🔄 Retry from Last Good** — revert and retry with new instructions
- **📝 Give Guidance** — free-text instructions for the next iteration
- **❌ Cancel Pipeline** — stop, keep work done so far

---

## Completion

```
┌──────────────────────────────────────────────────────┐
│  ✅ Pipeline Complete                                │
│  "Add user auth to the API"                         │
│  Template: ⚡ Coding · Mode: Local sub-agents       │
│                                                      │
│  Iterations: 7 · Time: 34 min                       │
│  Cloud tokens: 12.4K · Local tokens: 89K (free)     │
│  Tests: 18/18 passing                                │
│                                                      │
│  Lessons Learned (by Muninn):                        │
│  • "JWT token refresh needs mutex to prevent races"  │
│  • "Always test login flow after auth changes"       │
│                                                      │
│  [ View Diff ]  [ View Lessons ]  [ New Pipeline ]   │
└──────────────────────────────────────────────────────┘
```

---

## Custom Templates

Power users create custom templates in `~/.valhalla/pipelines/`:

```json
{
  "name": "Onboarding",
  "version": 1,
  "description": "Create employee onboarding materials",
  "icon": "🎓",
  "on_fail": "retry",
  "stages": [
    {"name": "research", "role": "researcher", "prompt": "Gather role requirements and company context"},
    {"name": "design", "role": "planner", "prompt": "Design the onboarding program structure"},
    {"name": "content", "role": "writer", "prompt": "Write all onboarding materials"},
    {"name": "review", "role": "reviewer", "on_fail": "goto:content", "prompt": "Review for completeness and tone"}
  ],
  "max_iterations": 2
}
```

Custom templates appear in the dashboard wizard alongside built-ins.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/pipeline/templates` | GET | List all templates (built-in + custom) |
| `/api/v1/orchestrate` | POST | Submit task. Auto-detects template. Accepts optional `template` field |
| `/api/v1/pipeline` | POST | Create pipeline (title, description, stages, template) |
| `/api/v1/pipeline` | GET | List active pipelines |
| `/api/v1/pipeline/{id}` | GET | Pipeline detail (status, stages, iterations) |
| `/api/v1/pipeline/{id}/advance` | POST | Force advance to next stage |
| `/api/v1/pipeline/{id}` | DELETE | Cancel pipeline |
| `/api/v1/socratic/debate/{id}` | GET | Debate status and rounds |
| `/api/v1/socratic/debate/{id}/intervene` | POST | Human adds input to debate |

---

## Roles Reference

These roles are used across all templates. On single-node, each becomes a system prompt persona:

| Role | Specialty |
|---|---|
| `planner` | Breaks tasks into sub-tasks, thinks about dependencies |
| `backend` | APIs, databases, server logic, security |
| `frontend` | UI, components, responsive design, accessibility |
| `tester` | Unit tests, integration tests, edge cases |
| `reviewer` | Quality, completeness, accuracy, professionalism |
| `researcher` | Information gathering, source evaluation, citations |
| `analyst` | Strategic patterns, trends, critical thinking |
| `data_analyst` | Statistics, visualizations, data quality |
| `writer` | Clear prose, key takeaways, tone matching |
| `designer` | Visual layout, typography, color, hierarchy |
| `executor` | Takes plans and implements them methodically |

# Pipeline UX — The Iterative Quality Loop

---

## What Is a Pipeline?

A pipeline is Valhalla's way of turning a task into a shipped result through structured iteration. Instead of one-shot generation, the system:

1. **Specs** the task (cloud model — Huginn / GLM-5)
2. **Builds** in parallel (local model — free)
3. **Tests** the output (Heimdall)
4. If it fails → **checks for progress or regression** (cloud model)
5. If progress → **fixes and rebuilds** (local model)
6. If regression → **escalates to a human**
7. If it passes → **distills lessons** (Muninn / Kimi) → **ships**

The insight: local models are weaker but free. Let them iterate 20 times overnight. Cloud models handle the parts that need real intelligence — specs, reviews, regression checks. Iteration count is the quality equalizer.

---

## Creating a Pipeline (Dashboard Wizard)

### Step 1 — New Pipeline

From the **Pipeline** page, click **+ New Pipeline**. A wizard modal opens:

```
┌────────────────────────────────────────────────────┐
│  ⚡ New Pipeline                                   │
│                                                    │
│  Title:                                            │
│  [ Add user auth to the API              ]         │
│                                                    │
│  Description (optional):                           │
│  [ JWT-based auth on all /api/v1 endpoints.        │
│    Include registration, login, and token   ]      │
│    refresh.                                        │
│                                                    │
│  Max Iterations:                                   │
│  [ 10 ▾ ]  (hard cap — pipeline stops here)        │
│                                                    │
│  Escalation Channel:                               │
│  ● Dashboard notification                          │
│  ○ Telegram                                        │
│  ○ Email                                           │
│                                                    │
│  [ Cancel ]                  [ Create Pipeline → ] │
└────────────────────────────────────────────────────┘
```

**Design rules:**
- Title is mandatory. Description is optional but recommended.
- Max iterations defaults to 10. The Heimdall-enforced hard cap is 25.
- Escalation channel default = dashboard notification (always on). Telegram/email are additive.
- Advanced options (collapsed by default): token budget, stage timeout, custom reviewer personas.

### Step 2 — Stage Configuration (Advanced, Optional)

For power users, clicking "Advanced" expands stage configuration:

```
┌────────────────────────────────────────────────────┐
│  Stages                                            │
│                                                    │
│  1. ☑ Spec        agent: huginn   model: glm-5     │
│  2. ☑ Build       agent: local    model: default   │
│  3. ☑ Test        agent: heimdall model: default   │
│  4. ☑ Review      rounds: 3      threshold: 0.7    │
│  5. ☑ Distill     agent: muninn   model: kimi      │
│                                                    │
│  Each stage can be toggled on/off. Reviewers        │
│  are configurable via Socratic debate settings.     │
└────────────────────────────────────────────────────┘
```

Most users leave this alone. Defaults are good.

### Step 3 — Pipeline Created

Clicking **Create Pipeline** calls `POST /api/v1/pipeline` and the pipeline card appears on the Pipeline page with status "Running."

---

## Watching a Pipeline Run (Progress UI)

### Pipeline Card (List View)

```
┌────────────────────────────────────────────────────┐
│  🔄 Add user auth to the API          Iteration 3  │
│                                                    │
│  ▇▇▇▇▇▇▇▇▇░░░░░░░░░░░  Stage: Test   30%         │
│                                                    │
│  Spec ✔ → Build ✔ → Test 🔄 → Fix → Distill       │
│                                                    │
│  ETA: ~12 min remaining          [ View Details ]  │
└────────────────────────────────────────────────────┘
```

### Pipeline Detail View

Clicking **View Details** opens the full pipeline page (`/pipeline/{id}`):

```
┌────────────────────────────────────────────────────────────┐
│  ⚡ Add user auth to the API                              │
│  Status: Running · Iteration 3/10 · Started 14 min ago    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Stage Timeline                                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  ✔ Spec      ✔ Build     🔄 Test      ○ Fix     ○ Distill │
│  (huginn)    (local)     (heimdall)                        │
│                                                            │
│  Iteration History                                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Iteration 3 (current)                              │  │
│  │  Stage: Test · Agent: heimdall                      │  │
│  │  Running tests... 12/18 passing                     │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Iteration 2 · PROGRESS                             │  │
│  │  Build fixed 4 of 6 test failures.                  │  │
│  │  Huginn verdict: "Clear progress. JWT signing now   │  │
│  │  works. Remaining: token refresh endpoint."         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Iteration 1 · FAIL                                 │  │
│  │  6 tests failed. Missing JWT secret config,         │  │
│  │  bcrypt import error, no token refresh endpoint.    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  [ Cancel Pipeline ]              [ Force Advance ]        │
└────────────────────────────────────────────────────────────┘
```

**Real-time updates:** The detail view subscribes to `WS /api/v1/events/stream` and updates live. No polling. Users see test results appear, iteration verdicts stream in, and the stage timeline advance — all without refreshing.

**Design rules:**
- Stage timeline uses color coding: ✔ green (passed), 🔄 blue (running), ❌ red (failed), ○ gray (pending)
- Iteration history shows most recent first
- Each iteration card is collapsible — click to expand full agent output
- ETA is estimated from average iteration time × remaining iterations

---

## Socratic Debate (In-Pipeline Review)

When a pipeline stage has `review_after: true`, the Socratic debate fires. The pipeline detail view shows a sub-panel:

```
┌──────────────────────────────────────────────────────────┐
│  🗣️ Socratic Review — Design Stage                      │
│  Round 2/3 · Consensus: 45%                              │
│  ━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░  45%                │
│                                                          │
│  🏛️ Architect (huginn/glm-5)                             │
│  "The auth middleware is solid but the token refresh      │
│  flow has a race condition. If two requests hit          │
│  /refresh simultaneously..."                             │
│                                                          │
│  😈 Devil's Advocate (heimdall/deepseek)                 │
│  "What happens in 6 months when you have 50 endpoints?   │
│  This middleware pattern requires manual annotation       │
│  on every route..."                                      │
│                                                          │
│  👤 End User (local)                                      │
│  "The error messages are cryptic. 'Invalid JWT' tells     │
│  me nothing. What expired? What do I do?"                │
│                                                          │
│  💬 Thor's Defense                                        │
│  "Good catch on the race condition — adding mutex.        │
│  Re: route annotation — I'll add a decorator pattern.     │
│  Re: error messages — agreed, will add context."         │
│                                                          │
│  [ 🖐️ Intervene — Add Your Take ]                       │
└──────────────────────────────────────────────────────────┘
```

**Human intervention:** Clicking **Intervene** lets the user add their own objection to the debate. The reviewers respond to it in the next round. This is the human-in-the-loop approval flow.

---

## Escalation

When Huginn's regression check returns **REGRESS** (the fix made things worse), the pipeline escalates.

### Dashboard Notification

A toast appears in the bottom-right:

```
┌──────────────────────────────────────┐
│  ⚠️ Pipeline Escalated              │
│  "Add user auth" — Regression at    │
│  iteration 5. Human review needed.  │
│  [ View Pipeline ]                   │
└──────────────────────────────────────┘
```

The pipeline card turns amber with a "🖐 Needs Review" badge. The detail view shows:

```
┌──────────────────────────────────────────────────────┐
│  ⚠️ REGRESSION DETECTED — Iteration 5               │
│                                                      │
│  Huginn's analysis:                                  │
│  "Iteration 4 fixed token refresh but broke the      │
│  original login flow. The bcrypt hash comparison      │
│  was removed during refactor. This is a net loss."   │
│                                                      │
│  Previous passing tests now failing:                 │
│  ❌ test_login_valid_credentials                     │
│  ❌ test_password_hash_verification                  │
│                                                      │
│  Options:                                            │
│  [ 🔄 Retry from Last Good ]  [ 📝 Give Guidance ]  │
│  [ ❌ Cancel Pipeline ]                              │
└──────────────────────────────────────────────────────┘
```

**Retry from Last Good:** Reverts to iteration 4 state and retries with new fix instructions.
**Give Guidance:** Opens a text input where the user can write specific instructions for the next iteration.
**Cancel:** Stops the pipeline. Work done so far stays accessible.

### Telegram Notification (if configured)

```
⚠️ Pipeline "Add user auth" hit regression at iteration 5.
Huginn: "Fixed token refresh but broke login flow."
→ Dashboard: http://odin:3000/pipeline/abc123
```

---

## Completion

When the pipeline passes all tests:

```
┌──────────────────────────────────────────────────────┐
│  ✅ Pipeline Complete                                │
│  "Add user auth to the API"                         │
│                                                      │
│  Iterations: 7                                       │
│  Time: 34 minutes                                    │
│  Cloud tokens: 12,400 (GLM-5: 8,200 · Kimi: 4,200) │
│  Local tokens: 89,000 (free)                         │
│  Tests: 18/18 passing                                │
│                                                      │
│  Lessons Learned (by Muninn):                        │
│  • "JWT token refresh needs mutex to prevent races"  │
│  • "Always test login flow after auth changes"       │
│  • "bcrypt.checkpw is the correct API, not ==  "     │
│                                                      │
│  These lessons are stored in procedural memory       │
│  and will be available in future pipelines.          │
│                                                      │
│  [ View Diff ]  [ View Lessons ]  [ New Pipeline ]   │
└──────────────────────────────────────────────────────┘
```

**Design rules:**
- Show cost breakdown: cloud (paid) vs. local (free). Reinforces the value prop.
- Lessons learned are shown prominently — this is the learning that competitors don't have.
- "View Diff" shows the actual code changes. "View Lessons" shows what was distilled to memory.

---

## Error States

| State | What the User Sees | What They Can Do |
|---|---|---|
| **Max iterations reached** | "Pipeline reached 10 iterations without passing all tests." | Increase max iterations, give guidance, or cancel |
| **Token budget exceeded** | "Cloud spend reached $2.50 limit." | Increase budget or switch to local-only mode |
| **Stage timeout** | "Build stage exceeded 15-minute timeout." | Retry or check if the task is too large |
| **Model unavailable** | "NVIDIA API returned 503. Falling back to local." | Automatic — user sees a toast, pipeline continues |
| **Escalation with no human response (24h)** | "Pipeline has been waiting for review for 24 hours." | Auto-cancels with notification |

---

## API Reference (for Thor)

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/pipeline` | POST | Create pipeline (title, description, max_iterations, stages) |
| `/api/v1/pipeline` | GET | List active pipelines |
| `/api/v1/pipeline/{id}` | GET | Pipeline detail (status, stage, iterations, history) |
| `/api/v1/pipeline/{id}/advance` | POST | Force advance to next stage (admin) |
| `/api/v1/pipeline/{id}` | DELETE | Cancel pipeline |
| `/api/v1/socratic/debate/{id}` | GET | Debate status, rounds, consensus |
| `/api/v1/socratic/debate/{id}/intervene` | POST | Human adds objection to debate |

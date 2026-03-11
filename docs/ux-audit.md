# Dashboard UX Audit

> **Audited by Valkyrie — Sprint 5.** Every page and component in `dashboard/app/` and `dashboard/components/` reviewed against actual source code.

---

## Summary

| Area | Pages Reviewed | Issues Found | Critical | Medium | Low |
|---|---|---|---|---|---|
| Navigation & Layout | 1 | 5 | 1 | 3 | 1 |
| Home / Mission Control | 1 | 4 | 0 | 2 | 2 |
| Nodes | 1 | 3 | 0 | 2 | 1 |
| Models | 1 | 2 | 0 | 1 | 1 |
| Soul Editor | 1 | 3 | 0 | 2 | 1 |
| Config Editor | 1 | 3 | 1 | 1 | 1 |
| Pipeline | 2 | 4 | 1 | 2 | 1 |
| War Room | 1 | 3 | 0 | 2 | 1 |
| Crucible | 1 | 3 | 0 | 2 | 1 |
| Debate | 1 | 3 | 0 | 2 | 1 |
| Plugins / Marketplace | 2 | 3 | 0 | 2 | 1 |
| Copy & Voice | All | 6 | 0 | 3 | 3 |
| **Total** | **13** | **42** | **3** | **24** | **15** |

---

## 🔴 Critical Issues

### C1 — Sidebar navigation order is wrong
**File:** `components/Sidebar.tsx` (line 8-19)
**Issue:** 10 nav items in a flat list with no grouping. The cognitive tool pages (Pipeline, Crucible, Debates) are interleaved with system pages (Config, Plugins). A new user can't distinguish "things I use daily" from "advanced cognitive features."
**Fix:** Group nav items with section headers:
```
── Core ──
  Nodes, Models, Soul Editor, Config
── Cognitive ──
  Pipeline, Crucible, Debates, War Room
── Ecosystem ──
  Plugins, Marketplace
```

### C2 — Config editor is a raw YAML textarea
**File:** `app/config/page.tsx`
**Issue:** Non-technical users see raw YAML with no syntax highlighting (it's a plain `<textarea>`). One indentation mistake breaks the config. No validation before save.
**Fix:** Add a "Form View" toggle that shows key sections (node, mesh, models, plugins) as labeled form fields. Raw YAML is the "advanced" mode. Add YAML validation before save (catch parse errors client-side).

### C3 — Pipeline page has no "New Pipeline" wizard implementation
**File:** `app/pipeline/page.tsx`
**Issue:** The "→ New Pipeline" button exists but has no `onClick` handler or modal. It renders but does nothing.
**Fix:** Implement the wizard modal as specified in `docs/pipeline-ux.md` — title, description, max iterations, escalation channel.

---

## 🟡 Medium Issues

### M1 — Home page stat cards don't link anywhere
**File:** `app/page.tsx` → `StatCard` component (line 156-179)
**Issue:** The stat cards (Nodes Online, Active Model, Uptime, Plugins) are informational but not clickable. Users expect cards to navigate to their detail pages.
**Fix:** Wrap each `StatCard` in a `<Link>` to its corresponding page.

### M2 — Nodes page doesn't show "Add Node" button
**File:** `app/nodes/page.tsx`
**Issue:** There's no way to add a new node from the nodes page. The "Add-a-Node" flow (generating a join command) is the key expansion feature but has no entry point.
**Fix:** Add "→ Add Node" button in the header. On click, modal shows the generated one-line join command from `POST /api/v1/mesh/join-token`.

### M3 — Nodes page has no empty state
**File:** `app/nodes/page.tsx`
**Issue:** If no nodes are returned from the API, the user sees a blank grid. No guidance on what to do.
**Fix:** Show an illustrated empty state: "No nodes connected yet. Run `valhalla join odin@<ip>:8765` on another machine to add your first node."

### M4 — Model picker doesn't show which model is local vs cloud
**File:** `components/ModelPicker.tsx`
**Issue:** Alias buttons (⚡ Odin, 🧠 Hugs, 🌙 Moon) don't indicate whether the model is local (free) or cloud (paid). Users don't know the cost implication of switching.
**Fix:** Add a small badge: "LOCAL" (green) or "CLOUD" (blue/amber) on each alias button.

### M5 — Soul Editor has no "which agent am I editing?"
**File:** `components/SoulEditor.tsx`
**Issue:** The editor shows IDENTITY/SOUL/USER tabs but doesn't indicate which agent these files belong to. In a multi-agent mesh, this is confusing.
**Fix:** Add an agent dropdown at the top of the editor: "Editing: odin ▾" — lists all agents from the mesh config.

### M6 — Soul Editor markdown preview doesn't render markdown
**File:** `components/SoulEditor.tsx`
**Issue:** The "preview" pane shows raw markdown text, not rendered HTML. Defeats the purpose of the split-pane.
**Fix:** Use a markdown renderer (react-markdown or similar) in the right pane.

### M7 — War Room hypotheses have no empty state
**File:** `app/warroom/page.tsx`
**Issue:** If no hypotheses exist yet, the user sees blank space where hypothesis cards should be. No call to action.
**Fix:** Show: "No hypotheses yet. Click 🧪 Dream Cycle to generate hypotheses from today's activity."

### M8 — War Room predictions chart has no data explanation
**File:** `components/PredictionChart.tsx`
**Issue:** The chart shows prediction accuracy over time but doesn't explain what "prediction accuracy" means in this context.
**Fix:** Add a one-line subtitle: "How well your agent predicted the outcome of tasks before executing them."

### M9 — Crucible page doesn't explain what it does
**File:** `app/crucible/page.tsx`
**Issue:** The page title is "🧪 Crucible" with subtext about last run stats, but no explanation of what the Crucible actually does. "Adversarial stress-testing" is jargon.
**Fix:** Add a one-line help text below stats: "The Crucible stress-tests your agent's learned procedures by throwing edge cases at them. Unbreakable procedures are reliable. Broken ones need fixing."

### M10 — Debate page has no "Start New Debate" button
**File:** `app/debate/page.tsx`
**Issue:** Users can only view existing debates. There's no way to start a new debate on arbitrary content.
**Fix:** Add "→ New Debate" button in the header. Modal with: topic text input, reviewer persona selection, max rounds.

### M11 — Pipeline cards don't show ETA
**File:** `components/PipelineCard.tsx`
**Issue:** Pipeline cards show status and iteration count but no time-based estimate ("~12 min remaining").
**Fix:** Calculate ETA from average iteration time × remaining max iterations. Show in the card footer.

### M12 — Crucible "Run Crucible" gives no progress feedback
**File:** `app/crucible/page.tsx`
**Issue:** Clicking "Run Crucible" shows a toast "Crucible cycle started" but the page doesn't update until the cycle completes. No progress indicator.
**Fix:** After clicking, show a spinning indicator on the button and/or a progress bar if the API supports partial results.

### M13 — Debate intervention input has no styling feedback
**File:** `app/debate/page.tsx`
**Issue:** The intervention input field at the bottom of the debate view is a bare `<input>` with no visible border or background — hard to see in dark mode.
**Fix:** Add a subtle border/background matching the glass-card style. Use `glass-card` class on the input wrapper.

### M14 — Plugin/marketplace pages missing from sidebar grouping  
**File:** `components/Sidebar.tsx`
**Issue:** "Plugins" and "Marketplace" are two separate sidebar items but they're conceptually one section. "Marketplace" should be nested under Plugins or they should be merged.
**Fix:** Either nest (Plugins → Installed / Browse) or rename: "Installed" for the plugins list page and keep "Marketplace" for browsing.

---

## 🟢 Low Priority

### L1 — Home page `GuidedDiscovery` component always shows
Users who've been using the app for weeks still see "Getting Started" tips. Add a dismiss button or hide after first week.

### L2 — Node card role text isn't capitalized
"orchestrator" → "Orchestrator". Small but looks unfinished.

### L3 — Config reference section at bottom of config page is too sparse
Only shows 4 top-level keys. Add `soul.`, `war_room.`, `model_router.` sections.

### L4 — War Room event stream has no "clear" or "filter" option
Events accumulate. No way to filter by topic or clear old events.

### L5 — Crucible stat cards: "Stressed" label is ambiguous
"⚠️ Stressed" could mean many things. Better: "⚠️ Edge Cases Found"

### L6 — All loading states use different patterns
Some pages use `<SkeletonCard>`, some use `animate-pulse`, Config page uses text "Loading config...". Standardize on skeleton loading.

### L7 — Missing keyboard shortcuts
No `Ctrl+S` to save in Config Editor or Soul Editor. Power users expect this.

### L8 — ThemeToggle in sidebar footer has no tooltip
Users don't know what the toggle does without hovering.

### L9 — Home page chat input has no "who am I talking to?" context
`ChatInput` says "Talk to your agent" but doesn't say which agent.

---

## Copy Review

### Voice Inconsistencies

| Location | Current | Issue | Suggested Fix |
|---|---|---|---|
| Sidebar header | "Mission Control" | Mixed Norse/military metaphors. Good — keep. | — |
| Nodes page header | "⬡ Mesh Nodes" | Good. Clear. | — |
| Models page header | "⚡ Model Picker" | "Picker" is developer jargon | "⚡ Models" or "⚡ Active Model" |
| Soul Editor header | "🜂 Soul Editor" | 🜂 is an obscure alchemy symbol. Most users won't recognize it. | Use 🧬 or keep 🜂 but add tooltip |
| Config Editor header | "⚙ Config Editor" | Good | — |
| War Room header | "⚔ War Room" | Good — Norse + military. Fits the brand. | — |
| Crucible header | "🧪 Crucible" | No explanation. New users won't know what this is. | Add subtitle: "Adversarial knowledge testing" |
| Pipeline header | "⚡ Pipelines" | Same icon ⚡ as Models page | Use 🔄 (which the sidebar already uses!) |
| Debate header | "🗣️ Socratic Debates" | Good. Clear and descriptive. | — |

### Jargon Flags

| Term | Where Used | Issue | Suggestion |
|---|---|---|---|
| "Dream Cycle" | War Room button | Non-obvious. What does dreaming mean? | Tooltip: "Analyzes today's activity and generates hypotheses about patterns" |
| "Philosopher's Stone" | War Room / Wisdom | Heavy metaphor. Users need context. | Add one-line explanation below the card |
| "Somatic gating" | Not in dashboard yet | Academic term. If added, explain. | "Gut check" or "Instinct check" with tooltip |
| "Belief shadows" | War Room radar chart | Theory of Mind jargon | "Peer Knowledge Map" or keep but add subtitle |
| "VRAM" | Node cards (implied) | Technical. Non-GPU users won't know. | "GPU Memory" with VRAM in parentheses |
| "Hot-reload" | Config page | Developer jargon. Users don't care how it works. | "Changes apply immediately" |

### Empty State Copy (Missing)

| Page | Current Empty State | Suggested |
|---|---|---|
| Nodes | (none — blank grid) | "No nodes connected. Run `valhalla join` on another machine to expand your mesh." |
| Pipeline | (none — blank list) | "No pipelines running. Click + New Pipeline to create an iterative build task." |
| War Room hypotheses | (none — blank cards) | "No hypotheses yet. Click Dream Cycle to analyze today's activity." |
| Debate | (none — shows "Select a debate") | "No debates yet. Debates are triggered during pipeline review stages." |
| Crucible | (none — shows skeleton) | "No crucible results. Click Run Crucible to stress-test your agent's knowledge." |

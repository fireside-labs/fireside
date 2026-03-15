---
description: Run a full sprint cycle with gated agent handoffs (Thor → Freya → Heimdall → Valkyrie → Odin)
---

// turbo-all

# Valhalla Sprint Pipeline

This workflow runs a gated sprint cycle across 5 agents. You (Odin) are the orchestrator.

## Agent Roster

| Alias | Role | Writes Code? |
|-------|------|----------|
| **Odin** (this chat) | Orchestrator — reads Valkyrie's report, plans next sprint | No |
| **Thor** | Backend engineer — Python, APIs, plugins, models | Yes |
| **Freya** | Frontend engineer — React, Next.js, dashboard, mobile UI | Yes |
| **Heimdall** | Security auditor — reviews code for vulnerabilities | No (writes audit reports) |
| **Valkyrie** | UX & Business Analyst — usability, resonance, completeness | No (writes UX reports) |

## Sprint Directory Structure

All sprint artifacts live in `sprints/current/`:

```
sprints/
  current/
    SPRINT.md              ← Sprint goals & tasks (Odin writes this)
    SPRINT_THOR.md         ← Thor's specific tasks
    SPRINT_FREYA.md        ← Freya's specific tasks
    gates/
      gate_thor.md         ← Thor drops when done
      gate_freya.md        ← Freya drops when done
      gate_heimdall.md     ← Heimdall drops when audit passes
      gate_valkyrie.md     ← Valkyrie drops when review complete
      audit_heimdall.md    ← Heimdall's security audit report
      review_valkyrie.md   ← Valkyrie's UX/business review report
      poll_heimdall.sh     ← Heimdall's polling script (watches for Thor+Freya gates)
      poll_valkyrie.sh     ← Valkyrie's polling script (watches for Heimdall gate)
  archive/
    sprint_01/             ← Completed sprints get archived here
    sprint_02/
```

---

## Phase 0: Sprint Setup (Odin)

1. Create fresh sprint directory:

```bash
mkdir -p sprints/current/gates && mkdir -p sprints/archive
```

2. Write `sprints/current/SPRINT.md` with sprint number, goals, and task breakdown for Thor and Freya.

3. Write `sprints/current/SPRINT_THOR.md` with Thor's specific backend tasks.

4. Write `sprints/current/SPRINT_FREYA.md` with Freya's specific frontend tasks.

5. If a previous sprint had Valkyrie findings, prepend them to the relevant task files so Thor/Freya address them.

---

## Phase 1: Build (Thor + Freya, parallel)

Thor and Freya work simultaneously on their tasks. Each agent:

1. Reads their `SPRINT_THOR.md` or `SPRINT_FREYA.md` task file.
2. Implements all tasks with `// turbo-all` auto-run enabled.
3. When ALL tasks are complete, drops a gate file:

**Thor drops:**
```bash
echo "# Thor Gate — Build Complete" > sprints/current/gates/gate_thor.md && echo "Sprint tasks completed at $(date)" >> sprints/current/gates/gate_thor.md
```

**Freya drops:**
```bash
echo "# Freya Gate — Build Complete" > sprints/current/gates/gate_freya.md && echo "Sprint tasks completed at $(date)" >> sprints/current/gates/gate_freya.md
```

---

## Phase 2: Security Audit (Heimdall)

At the START of the sprint, Heimdall creates and runs a polling script. This script checks every 60 seconds for both Thor and Freya gate files.

1. Create and run the Heimdall polling script:

```bash
cat > sprints/current/gates/poll_heimdall.sh << 'POLL'
#!/bin/bash
# Heimdall Gate Poller — checks for Thor + Freya completion every 60s
GATES_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[Heimdall] 🛡️ Polling for Thor + Freya gates every 60s..."
while true; do
  if [ -f "$GATES_DIR/gate_thor.md" ] && [ -f "$GATES_DIR/gate_freya.md" ]; then
    echo "[Heimdall] ✅ Both gates found! Thor and Freya have completed their work."
    echo "[Heimdall] Beginning security audit..."
    exit 0
  fi
  THOR="⬜"; FREYA="⬜"
  [ -f "$GATES_DIR/gate_thor.md" ] && THOR="✅"
  [ -f "$GATES_DIR/gate_freya.md" ] && FREYA="✅"
  echo "[Heimdall] $(date +%H:%M:%S) — Thor: $THOR | Freya: $FREYA | Waiting..."
  sleep 60
done
POLL
bash sprints/current/gates/poll_heimdall.sh
```

2. Once the poller exits (both gates found), Heimdall performs a full security audit. The audit checks:
   - Input validation and sanitization
   - Authentication and authorization
   - Sensitive data exposure
   - API security (rate limiting, CORS, error handling)
   - Dependency vulnerabilities
   - XSS/injection risks in frontend

3. Write audit results to `sprints/current/gates/audit_heimdall.md` with ✅ / ⚠️ / ❌ for each check.

4. **If audit PASSES** (no ❌ critical issues):

```bash
echo "# Heimdall Gate — Audit Passed" > sprints/current/gates/gate_heimdall.md && echo "Security audit passed at $(date)" >> sprints/current/gates/gate_heimdall.md
```

5. **If audit FAILS** (any ❌ critical issues):
   - Delete Thor and Freya gate files so they know to redo work:

```bash
rm -f sprints/current/gates/gate_thor.md sprints/current/gates/gate_freya.md
echo "[Heimdall] ❌ Audit FAILED. Deleted Thor + Freya gates. See audit_heimdall.md for required fixes."
```

   - Thor and Freya must read `audit_heimdall.md`, fix the issues, and re-drop their gate files.
   - Restart the polling script (go back to step 1 of Phase 2).

---

## Phase 3: UX & Business Review (Valkyrie)

At the START of the sprint, Valkyrie creates and runs a polling script that watches for Heimdall's gate.

1. Create and run the Valkyrie polling script:

```bash
cat > sprints/current/gates/poll_valkyrie.sh << 'POLL'
#!/bin/bash
# Valkyrie Gate Poller — checks for Heimdall's audit gate every 60s
GATES_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[Valkyrie] 👁️ Polling for Heimdall audit gate every 60s..."
while true; do
  if [ -f "$GATES_DIR/gate_heimdall.md" ]; then
    echo "[Valkyrie] ✅ Heimdall audit passed! Beginning UX & business review..."
    exit 0
  fi
  echo "[Valkyrie] $(date +%H:%M:%S) — Heimdall: ⬜ | Waiting..."
  sleep 60
done
POLL
bash sprints/current/gates/poll_valkyrie.sh
```

2. Once the poller exits, Valkyrie reviews:
   - **Usability:** Is the UX intuitive? Does the flow make sense for a consumer?
   - **Resonance:** Would a real user be excited by this? Does it feel premium?
   - **Completeness:** Are frontend and backend properly connected?
   - **Layout:** Is the responsive design correct? Mobile-first?
   - **Business Alignment:** Does this sprint move toward commercialization goals?

3. Write review results to `sprints/current/gates/review_valkyrie.md`.

4. Drop the completion gate:

```bash
echo "# Valkyrie Gate — Review Complete" > sprints/current/gates/gate_valkyrie.md && echo "UX review completed at $(date)" >> sprints/current/gates/gate_valkyrie.md
```

> [!IMPORTANT]
> Valkyrie writes NO code. Her findings that require code changes are carried forward to the NEXT sprint by Odin. She does NOT block the current sprint from completing — she reports and moves on.

---

## Phase 4: Sprint Completion (Odin)

1. Read `sprints/current/gates/review_valkyrie.md`.
2. Any deficiencies or findings become tasks in the NEXT sprint.
3. Archive the completed sprint:

```bash
SPRINT_NUM=$(head -1 sprints/current/SPRINT.md | grep -oE '[0-9]+') && mv sprints/current "sprints/archive/sprint_${SPRINT_NUM}" && mkdir -p sprints/current/gates
```

4. Begin Phase 0 for the next sprint, incorporating Valkyrie's findings.

---

## Quick Status Check

Run this at any time to see pipeline status:

```bash
echo "=== Valhalla Sprint Pipeline ===" && echo "" && GATES="sprints/current/gates" && for agent in thor freya heimdall valkyrie; do if [ -f "$GATES/gate_${agent}.md" ]; then echo "  ✅ ${agent}"; else echo "  ⬜ ${agent}"; fi; done
```

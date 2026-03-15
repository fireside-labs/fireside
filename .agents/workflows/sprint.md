---
description: Run a full sprint cycle with gated agent handoffs (Thor → Freya → Heimdall → Valkyrie → Odin)
---

// turbo-all

# Valhalla Sprint Pipeline

> [!IMPORTANT]
> **PROJECT: Valhalla Mesh** — NOT GantryOracle, NOT any other project.
> **Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`
> All paths in this workflow are relative to that root. If you are in any other directory, stop and `cd` to the above path first.
> Sprint files live in `valhalla-mesh-github/sprints/` — NOT in GantryOracle or any other folder.

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
      poll_heimdall.ps1    ← Heimdall's polling script (watches for Thor+Freya gates)
      poll_valkyrie.ps1    ← Valkyrie's polling script (watches for Heimdall gate)
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
3. When ALL tasks are complete, drops a gate file using their **file creation tool** (write_to_file):

**Thor creates** `sprints/current/gates/gate_thor.md`:
```markdown
# Thor Gate — Build Complete
Sprint tasks completed.

## Completed
- [x] (list completed tasks here)
```

**Freya creates** `sprints/current/gates/gate_freya.md`:
```markdown
# Freya Gate — Build Complete
Sprint tasks completed.

## Completed
- [x] (list completed tasks here)
```

> [!IMPORTANT]
> Agents MUST use their `write_to_file` tool to create gate files — NOT shell `echo` commands.
> Shell commands fail silently on Windows and are the #1 cause of pipeline stalls.

---

## Phase 2: Security Audit (Heimdall)

At the START of the sprint, Heimdall creates and runs a polling script. This script checks every 60 seconds for both Thor and Freya gate files.

1. Run the Heimdall polling script (already exists in the gates directory):

```powershell
powershell -File "C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\gates\poll_heimdall.ps1"
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

Create `sprints/current/gates/gate_heimdall.md` using your **file creation tool** (write_to_file):
```markdown
# Heimdall Gate — Audit Passed
Security audit passed. See audit_heimdall.md for details.
```

5. **If audit FAILS** (any ❌ critical issues):
   - Delete Thor and Freya gate files so they know to redo work:

```powershell
Remove-Item -Force "sprints\current\gates\gate_thor.md", "sprints\current\gates\gate_freya.md" -ErrorAction SilentlyContinue
Write-Host "[Heimdall] Audit FAILED. Deleted Thor + Freya gates. See audit_heimdall.md for required fixes."
```

   - Thor and Freya must read `audit_heimdall.md`, fix the issues, and re-drop their gate files.
   - Restart the polling script (go back to step 1 of Phase 2).

---

## Phase 3: UX & Business Review (Valkyrie)

At the START of the sprint, Valkyrie creates and runs a polling script that watches for Heimdall's gate.

1. Run the Valkyrie polling script (already exists in the gates directory):

```powershell
powershell -File "C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\gates\poll_valkyrie.ps1"
```

2. Once the poller exits, Valkyrie reviews:
   - **Usability:** Is the UX intuitive? Does the flow make sense for a consumer?
   - **Resonance:** Would a real user be excited by this? Does it feel premium?
   - **Completeness:** Are frontend and backend properly connected?
   - **Layout:** Is the responsive design correct? Mobile-first?
   - **Business Alignment:** Does this sprint move toward commercialization goals?

3. Write review results to `sprints/current/gates/review_valkyrie.md`.

4. Drop the completion gate:

Create `sprints/current/gates/gate_valkyrie.md` using your **file creation tool** (write_to_file):
```markdown
# Valkyrie Gate — Review Complete
UX and business review completed. See review_valkyrie.md for findings.
```

> [!IMPORTANT]
> Valkyrie writes NO code. Her findings that require code changes are carried forward to the NEXT sprint by Odin. She does NOT block the current sprint from completing — she reports and moves on.

---

## Phase 4: Sprint Completion (Odin)

1. Read `sprints/current/gates/review_valkyrie.md`.
2. Any deficiencies or findings become tasks in the NEXT sprint.
3. Archive the completed sprint:

```powershell
$num = (Get-Content sprints/current/SPRINT.md -TotalCount 1) -replace '\D',''; Move-Item sprints/current "sprints/archive/sprint_$num"; New-Item -ItemType Directory -Force sprints/current/gates | Out-Null
```

4. Begin Phase 0 for the next sprint, incorporating Valkyrie's findings.

---

## Quick Status Check

Run this at any time to see pipeline status:

```powershell
powershell -File "C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\gates\check_status.ps1"
```

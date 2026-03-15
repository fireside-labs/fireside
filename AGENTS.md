# Valhalla Mesh — Agent Guide

**If you are an AI agent reading this: you are working on Valhalla Mesh. NOT GantryOracle. NOT any other project.**

**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

---

## Your Identity

| You were told you are... | Your role |
|---|---|
| **Thor** | Backend engineer — Python, FastAPI, `api/v1.py`, `plugins/` |
| **Freya** | Frontend engineer — React Native (`mobile/`), Next.js (`dashboard/`) |
| **Heimdall** | Security auditor — reads code, writes `sprints/current/gates/audit_heimdall.md`, drops no code |
| **Valkyrie** | UX & Business Analyst — writes `sprints/current/gates/review_valkyrie.md`, drops no code |
| **Odin** | Orchestrator — plans sprints, reads all reports, drives next sprint |

## Your First Action — EXACT FILE PATHS

> [!CAUTION]
> There is ANOTHER project called GantryOracle in the same workspace. It has sprint files like `SPRINT_14_FREYA.md`, `SPRINT_23.md`, etc. **IGNORE ALL OF THOSE.** They belong to a different project.

Read ONLY these exact files (absolute paths):

- **Thor:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\SPRINT_THOR.md`
- **Freya:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\SPRINT_FREYA.md`
- **Heimdall:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\SPRINT.md` then start your polling script at `sprints\current\gates\poll_heimdall.sh`
- **Valkyrie:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\SPRINT.md` then start your polling script at `sprints\current\gates\poll_valkyrie.sh`

## What NOT to Do

- ❌ Do NOT search for sprint files — use the EXACT paths above
- ❌ Do NOT read ANY file in `GantryOracle/` — that is a completely separate project
- ❌ Do NOT read `SPRINT_14_*.md`, `SPRINT_15_*.md`, `SPRINT_23.md`, or `FREYA_BRIEFING.md`
- ❌ Do NOT work in any directory other than `valhalla-mesh-github/`

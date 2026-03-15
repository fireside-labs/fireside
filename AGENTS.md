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

## Your First Action

Read your task file:

- **Thor:** `sprints/current/SPRINT_THOR.md`
- **Freya:** `sprints/current/SPRINT_FREYA.md`
- **Heimdall:** Run `bash sprints/current/gates/poll_heimdall.sh` then audit when gates appear
- **Valkyrie:** Run `bash sprints/current/gates/poll_valkyrie.sh` then review when Heimdall gate appears

## What NOT to Do

- ❌ Do NOT read files in `GantryOracle/` — that is a completely separate project
- ❌ Do NOT read `SPRINT_14_*.md`, `SPRINT_23.md` or any sprint files outside `sprints/current/`
- ❌ Do NOT work in any directory other than `valhalla-mesh-github/`

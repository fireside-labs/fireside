# Valkyrie Gate — Sprint 14 Fixes Applied
Completed at: 2026-03-15T22:58:00-07:00

## Fixes Applied by Valkyrie

### F3 — Fire Theme ✅
Cleared all `#00ff88` neon green → `#F59E0B` fire amber:
- `PredictionChart.tsx` — 5 instances (gradient stops, stroke, dot, activeDot)
- `EventStream.tsx` — 1 instance (model-switch topic color + bg)
- `DebateTranscript.tsx` — 1 instance (persona color)
- `globals.css` — was already fire amber ✅

### F4 — Remove Hardcoded Norse Names ✅
- `nodes/page.tsx` — removed `FRIENDLY_NAMES: { odin, thor, freya, heimdall }` → dynamic `getFriendlyName(node)` using `node.friendly_name` from API

### H2 (partial) — Norse Names ✅
- `DebateTranscript.tsx` — `"💬 Thor"` → `"💬 Builder"`

### T6 — API Port ✅
- Already fixed: `api.ts` line 4 reads `localhost:8765`

## Verification
- `grep -r "#00ff88" dashboard/` → 0 results ✅
- `grep -r "FRIENDLY_NAMES" dashboard/` → 0 results ✅

## Still Needs Other Agents
- T1 (Thor): Mac unified memory detection
- T2 (Thor): `POST /api/v1/chat` endpoint
- T3 (Thor): `POST /api/v1/brains/install` endpoint
- T4 (Thor): `GET /api/v1/guildhall/agents` real data
- F1 (Freya): Wire CompanionChat to real backend
- F2 (Freya): Wire BrainInstaller to real download
- F8 (Freya): Replace 5 MOCK_ arrays
- F9 (Freya): Offline mode indicator
- H1 (Heimdall): Security review of new endpoints
- H2 (Heimdall): Full Norse name grep

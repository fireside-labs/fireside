# Valkyrie — Sprint 14 End-to-End Test Report

**Sprint:** "Last Mile" Wiring
**Tester:** Valkyrie (QA)
**Date:** 2026-03-15
**Status:** 🟡 BASELINE ESTABLISHED — This is the pre-agent snapshot. All 22 tasks are correctly identified.

---

## V1. End-to-End Test Results (Pre-Agent Baseline)

### Checkpoint 1: Fresh install via .exe → system specs correct?

**Status: ✅ FIXED (by owner)**

The owner already fixed `main.rs`:
- RAM: `wmic` → `Get-CimInstance` (PowerShell)
- GPU: same fix
- Added `vram_gb` field

**Remaining (T1):** Mac unified memory detection still returns `0.0` on non-Windows — needs Thor.

---

### Checkpoint 2: Onboarding → config files written?

**Status: ✅ WORKING**

The InstallerWizard (Sprint 13) writes `valhalla.yaml`, `companion_state.json`, and `onboarding.json` via Tauri Rust commands. The 6-step flow collects name, companion, brain, AI agent.

---

### Checkpoint 3: Dashboard loads → no hardcoded agent names visible?

**Status: ❌ FAIL — Norse names still present**

| File | Hardcoded Names | Sprint 14 Task |
|------|----------------|----------------|
| `nodes/page.tsx` L14-19 | `FRIENDLY_NAMES: { odin: "Your MacBook", thor: "Office PC", freya: "Living Room PC", heimdall: "Security Server" }` | F4 |
| `DebateTranscript.tsx` L9 | `"💬 Thor": "#00ff88"` | H2 |
| `InstallerWizard.tsx` L9 | Comment: "Calls Thor's Tauri commands" (non-user-facing) | H2 (low) |

**Owner fix:** `AgentSidebarList.tsx` was already fixed ✅ — now dynamic from localStorage.

---

### Checkpoint 4: Chat → real LLM response (not canned)?

**Status: ❌ FAIL — Still canned**

`CompanionChat.tsx` still uses `PET_RESPONSES` (L39-82) — hardcoded species-specific strings. The `/api/v1/chat` endpoint does not exist in `v1.py` yet.

| File | Issue | Sprint 14 Task |
|------|-------|----------------|
| `CompanionChat.tsx` L39 | `PET_RESPONSES` canned strings | F1 |
| `api/v1.py` | No `POST /api/v1/chat` endpoint | T2 |

---

### Checkpoint 5: Brains page → real hardware shown?

**Status: ✅ FIXED (by owner)**

`brains/page.tsx` — removed hardcoded "MacBook Pro / M3 Max / 36GB" → real detection via Tauri/API.

**Remaining (T3):** `BrainInstaller.tsx` still uses `runSimulatedInstall()` (fake 6-second progress bar). Real download endpoint `POST /api/v1/brains/install` doesn't exist yet.

---

### Checkpoint 6: Fire theme consistent throughout?

**Status: ❌ FAIL — Dashboard still neon green**

| File | Issue | Sprint 14 Task |
|------|-------|----------------|
| `globals.css` L15 | `--color-neon: #00ff88` (should be `#F59E0B`) | F3 |
| `PredictionChart.tsx` L40,41,72,75,76 | 5 instances of `#00ff88` | F3 |
| `EventStream.tsx` L13 | `#00ff88` + `rgba(0,255,136,0.12)` | F3 |
| `DebateTranscript.tsx` L9 | `#00ff88` | F3 |

The Tauri installer uses fire amber (`#F59E0B`/`#D97706`). The dashboard uses neon green (`#00ff88`). Transition between them is jarring.

---

## Additional Issues Found

### API Port Mismatch (T6)
```
dashboard/lib/api.ts:4 → API_BASE = "http://localhost:8766"
```
Backend starts on port `8765`. This means the dashboard can't reach the backend out of the box.

### Mock Data Still Active (F8)
5 components still use inline mock data:

| Component | Mock Constant |
|-----------|--------------|
| `PurchaseHistory.tsx` | `MOCK_PURCHASES` |
| `TaskQueue.tsx` | `MOCK_TASKS` |
| `WeeklyCard.tsx` | `MOCK_INSIGHTS` |
| `InventoryGrid.tsx` | `MOCK_INVENTORY` |
| `AdventureCard.tsx` | `MOCK_ADVENTURES` |

### GuildHall Fallback (T4)
`GuildHall.tsx` L85 — still uses `FALLBACK_AGENTS` with hardcoded Atlas. Needs to fetch from `GET /api/v1/guildhall/agents`.

### No Offline Indicator (F9)
`api.ts` has ~800 lines of mock fallback data that loads silently. User has no idea they're seeing cached/fake data.

---

## Summary: What Works vs What Needs Agents

| Area | Status | Blocking Tasks |
|------|--------|---------------|
| System detection (Windows) | ✅ Owner fixed | — |
| Brains page hardware | ✅ Owner fixed | — |
| Agent sidebar dynamic | ✅ Owner fixed | — |
| Mac VRAM detection | ❌ | T1 (Thor) |
| Chat endpoint | ❌ | T2 (Thor) + F1 (Freya) |
| Brain download | ❌ | T3 (Thor) + F2 (Freya) |
| GuildHall real data | ❌ | T4 (Thor) |
| API port | ❌ | T6 (Thor) |
| Fire theme | ❌ | F3 (Freya) |
| Norse names | ❌ | F4 (Freya) + H2 (Heimdall) |
| Mock data | ❌ | F8 (Freya) |
| Offline indicator | ❌ | F9 (Freya) |

**22 tasks correctly identified. Owner's 3 fixes verified. Ready for agents to execute.**

---

— Valkyrie 👁️

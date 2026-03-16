# Sprint 14 — "Last Mile" Wiring

> **Goal:** Make the app work end-to-end for a first-time user.  
> **Sources:** Ullr audit (2026-03-15), old dashboard_audit.md, first user test findings  
> **Priority:** Install → See correct specs → Chat → See real data

---

## Already Fixed (this session)
- [x] `main.rs` — RAM: `wmic` → `Get-CimInstance`, GPU: same, added `vram_gb` field
- [x] `AgentSidebarList.tsx` — removed hardcoded Thor/Freya/Heimdall/Valkyrie → dynamic from localStorage
- [x] `brains/page.tsx` — removed hardcoded "MacBook Pro / M3 Max / 36GB" → real detection via Tauri/API

---

## 🔨 Thor (Backend + Tauri)

### T1. Fix Mac unified memory detection 🔴
`main.rs` VRAM detection returns `0.0` on non-Windows. For Mac: use `sysctl hw.memsize` for total unified memory. For Linux: try `nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits`.
- File: `tauri/src-tauri/src/main.rs` (lines 130-145 vram_gb block)

### T2. Implement `POST /api/v1/chat` endpoint 🔴
Chat page sends to this endpoint but it doesn't exist in `v1.py`. Proxy to local llama.cpp at `http://127.0.0.1:8080/completion`. Stream response via SSE. Use companion personality from `~/.fireside/companion_state.json`.
- File: `api/v1.py`
- Ref: Ullr audit §2 — CompanionChat uses canned `PET_RESPONSES` array

### T3. Implement `POST /api/v1/brains/install` endpoint 🔴
`BrainInstaller.tsx` calls this but falls back to `runSimulatedInstall()` (fake 6-second progress bar). Real endpoint should: accept `{ model_id, url }`, download GGUF to `~/.fireside/models/`, stream progress via SSE.
- File: `api/v1.py`
- Ref: Ullr audit §3 — brains page

### T4. Implement `GET /api/v1/guildhall/agents` endpoint 🟡
Returns user's actual agents. Currently falls back to `FALLBACK_AGENTS = [{ name: "Atlas", activity: "idle" }]`. Should return agents from config with real activity status.
- File: `api/v1.py`

### T5. Implement `POST /api/v1/nodes` (register new node) 🟡
Old audit flagged: "Add another device" card is purely decorative (no onClick). Need endpoint to register a new device to the mesh.
- File: `api/v1.py`

### T6. Fix API port mismatch 🔴
Old audit found: `api.ts` has `API_BASE = localhost:8766` but install starts backend on `8765`. Verify and unify.
- File: `dashboard/lib/api.ts` (line ~5)

---

## 🎨 Freya (Dashboard Frontend)

### F1. Wire CompanionChat to real backend 🔴
Replace `PET_RESPONSES` canned strings (lines 39-82) with `POST /api/v1/chat`. Show typing indicator during LLM response. Falls back to canned responses if backend unreachable.
- File: `dashboard/components/CompanionChat.tsx`

### F2. Wire BrainInstaller to real download 🔴
Replace `runSimulatedInstall()` with real `POST /api/v1/brains/install` SSE stream. Show actual download progress (bytes/total). Remove hardcoded speed results (line 47, 79).
- File: `dashboard/components/BrainInstaller.tsx`

### F3. Fire theme across dashboard 🟡
Transition from installer → dashboard is jarring. Installer uses 🔥 amber (`#F59E0B`/`#D97706`/`#92400E`), dashboard uses 💎 neon green (`#00FF88`). Update:
- `globals.css` — change `--color-neon: #00ff88` → warm amber `#F59E0B`, update all rgba() references
- `--color-neon-glow` → `rgba(245, 158, 11, 0.15)`
- Glass card hover border → amber instead of green
- Light theme: adjust `--color-neon` similarly
- File: `dashboard/app/globals.css`

### F4. Remove hardcoded node names 🟡
`nodes/page.tsx` has `FRIENDLY_NAMES: { odin: "Your MacBook", thor: "Office PC", freya: "Living Room PC" }`. Replace with actual node names from config or let user set friendly names.
- File: `dashboard/app/nodes/page.tsx`

### F5. Wire "Add Node" button 🟡
Add `onClick` to the "Add another device" card (currently a static div, lines 119-125). Should open a dialog with mesh join token flow (endpoint `POST /mesh/join-token` already exists).
- File: `dashboard/app/nodes/page.tsx`

### F6. Wire save buttons (no-ops → real API) 🟡
- Soul page: `console.log("Personality saved")` → `PUT /api/v1/soul/identity.md` (endpoint exists)
- Config page: `console.log("Settings saved")` → `PUT /api/v1/config` (endpoint exists)
- Personality slider: `console.log` → `POST /api/v1/soul/personality`
- Files: `dashboard/app/soul/page.tsx`, `dashboard/app/config/page.tsx`

### F7. Wire SystemStatus to real polling 🟡
Currently hardcodes `{ brain: "Smart & Fast", tokS: 45, inference: "running" }` with `// In production, poll` comment. Poll `GET /api/v1/status` every 5s. "Restart" button → actually restart backend.
- File: `dashboard/components/SystemStatus.tsx`

### F8. Remove/replace mock companion components 🟡
Old audit found these inline-mock components:
- `WeeklyCard.tsx` — `MOCK_INSIGHTS` → wire to real learning stats or hide
- `InventoryGrid.tsx` — `MOCK_INVENTORY` → wire to localStorage
- `TaskQueue.tsx` — `MOCK_TASKS` → wire to pipeline status
- `AdventureCard.tsx` — `MOCK_ADVENTURES` → wire or hide
- `PurchaseHistory.tsx` — `MOCK_PURCHASES` → wire to store

### F9. Mock fallback indicator 🟡
`api.ts` has ~800 lines of mock data that silently loads when API is unreachable. Add a visible "⚠️ Offline mode — showing cached data" banner so users know what's real.
- File: `dashboard/lib/api.ts`

### F10. Guided onboarding tour 🟡
Lock sidebar tabs until user visits each section. Steps: Companion → Chat → Brains → Unlock all. "Skip Tour" for power users.
- Files: [NEW] `dashboard/components/GuidedTour.tsx`, `dashboard/components/Sidebar.tsx`

---

## 🛡️ Heimdall (Audit)

### H1. Security review of new endpoints
- `POST /api/v1/chat` — sanitize input before LLM, rate limit
- `POST /api/v1/brains/install` — validate download URLs (no SSRF), verify GGUF checksums
- `POST /api/v1/nodes` — auth token validation

### H2. Verify no hardcoded Norse names remain
Grep entire codebase for "odin", "thor", "freya", "heimdall", "valkyrie" in non-sprint/non-test files. All should be dynamic or removed.

---

## 📋 Valkyrie (QA)

### V1. End-to-end test
1. Fresh install via .exe → system specs correct?
2. Onboarding → name + companion → config files written?
3. Dashboard loads → no hardcoded agent names visible?
4. Chat → real LLM response (not canned)?
5. Brains page → real hardware shown?
6. Fire theme consistent throughout?

---

## Gate Criteria
- [ ] `npm run build` passes locally (27/27 pages)
- [ ] `cargo tauri build` produces .exe
- [ ] Correct RAM/GPU shown in installer AND brains page
- [ ] Mac: unified memory shown correctly
- [ ] No "Thor/Freya/Odin/Heimdall/Valkyrie" visible to user
- [ ] Fire theme (amber) consistent from installer → dashboard
- [ ] Chat sends messages to real backend (when backend running)
- [ ] API port unified (8765 everywhere)

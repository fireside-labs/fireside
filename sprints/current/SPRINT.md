# Sprint 15 — "Ship It"

> **Goal:** A new user can install, onboard, chat, browse the store, and never see mock data or broken UI.  
> **Timeline:** 2 days  
> **Source:** User test round 2 (2026-03-15 11:45 PM)

---

## 🔨 Thor (Backend + Tauri)

### T1. Backend auto-start from Tauri 🔴
Biggest blocker. Without the backend running, everything shows "Offline mode." Tauri should:
- Launch `bifrost.py` as a child process on app start
- Manage lifecycle (restart on crash, kill on app close)
- Show status in system tray
- File: `tauri/src-tauri/src/main.rs` — add `setup()` hook

### T2. Verify nvidia-smi VRAM detection 🔴
Sprint 14 fix may not be in the .exe user tested. Verify:
- `nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits` → should return `32607` (MB)
- Convert to GB: 31.8 GB
- **Test:** rebuild .exe, fresh install, check system check screen shows ~32GB VRAM + ~64GB RAM
- File: `tauri/src-tauri/src/main.rs` (vram_gb block, ~line 117)

### T3. Store backend — plugin registry + purchases 🔴
Current store is 100% mock (`MOCK_MARKETPLACE`, 8 fake plugins). Need:
- `GET /api/v1/store/plugins` — real plugin registry (can start with local JSON file)
- `POST /api/v1/store/purchase` — record purchase, validate, download plugin
- `GET /api/v1/store/purchases` — user's purchase history
- Payment integration can be v1.1, but the listing/install flow must work
- File: `api/v1.py`

### T4. Config sync endpoint 🟡
Onboarding saves `agent_name`, `agent_style`, `companion_name`, `companion_species`, `brain` via `write_config`. Need:
- `GET /api/v1/config/onboarding` — returns all onboarding choices
- Dashboard reads from this instead of scattered localStorage keys
- File: `api/v1.py`

---

## 🎨 Freya (Dashboard Frontend)

### F1. Fix Guided Tour — Next button + lock tabs 🔴
Current state: Step 1/3 shows, "Next" button doesn't advance, tabs are NOT locked.
- Wire `onClick` on Next button to advance tour step
- Disable/grey out sidebar tabs until tour completes (or user clicks "Skip")
- Tour steps: Dashboard → Brains → Chat → Done (unlock all)
- Files: `dashboard/components/GuidedTour.tsx`, `dashboard/components/Sidebar.tsx`

### F2. Settings brain picker matches onboarding 🔴
Onboarding shows "Smart & Fast" / "Deep Thinker" / "Cloud Expert". Settings page (`BrainPicker.tsx`) shows completely different brain names. Must be identical.
- Read brain choice from `fireside_agent_style` or config endpoint
- Highlight the brain the user already chose during onboarding
- Files: `dashboard/components/BrainPicker.tsx`, `dashboard/components/SettingsForm.tsx`

### F3. Node shows as user's agent name 🟡
The "this PC" node on the nodes page should show the agent name chosen during onboarding (e.g. "Atlas"), not a generic name.
- Read from `fireside_agent_name` localStorage
- File: `dashboard/app/nodes/page.tsx`

### F4. Store page — wire to real backend 🔴
Replace `MOCK_MARKETPLACE` (8 fake plugins) with real `GET /api/v1/store/plugins`.
- Install button → `POST /api/v1/store/purchase`
- Show real purchase history
- Seller dashboard can be v1.1
- Files: `dashboard/app/store/page.tsx`, `dashboard/app/store/sell/page.tsx`

### F5. Mock pages → "Coming Soon" 🟡
Pages that aren't wired yet should show a clean "Coming Soon" card instead of fake data:
- `/learning` — MOCK_PREDICTIONS, MOCK_SELF_MODEL
- `/warroom` — MOCK_HYPOTHESES, MOCK_PREDICTIONS, MOCK_EVENTS
- `/crucible` — MOCK_CRUCIBLE
- `/debate` — MOCK_DEBATES
- `/pipeline` — MOCK_PIPELINES
- Files: each page's `page.tsx`

### F6. Guild Hall redesign 🟡
Current pixel art is low quality. User reference: **Game Dev Story** level pixel art, **Claude office** ambient style.
- Higher-res sprites (48px or 64px instead of current tiny ones)
- Warm, ambient background (fireside cabin / cozy office)
- Agents doing contextual activities (not just floating)
- Smooth idle animations
- Files: `dashboard/components/GuildHall.tsx`, `dashboard/components/GuildHallAgent.tsx`, `dashboard/components/AvatarSprite.tsx`

### F7. Companion name from onboarding 🟡
Companion widget should show the name chosen during onboarding (e.g. "Ember"), not a default.
- Read from `fireside_companion` localStorage (JSON with name, species)
- File: `dashboard/components/CompanionSim.tsx`

---

## 🛡️ Heimdall (Audit)

### H1. Full end-to-end config flow audit
Trace every onboarding field through the system:
- `userName` → where does it appear in dashboard?
- `agentName` → nodes? sidebar? settings? everywhere?
- `companionName` → companion widget? chat?
- `brainSize` → brains page? settings?
Report any disconnects.

### H2. Store security review
- Purchase endpoint auth
- Plugin download validation
- No arbitrary code execution from installed plugins

---

## 📋 Valkyrie (QA)

### V1. Fresh install end-to-end
1. Uninstall Fireside + clear state
2. Run .exe → system shows ~64GB RAM + ~32GB VRAM?
3. Onboarding → name agent "Atlas", pick fox companion "Ember"
4. Dashboard → "Atlas" shows in sidebar, settings, nodes?
5. Tour → Next works, tabs locked until done?
6. Brains → matches onboarding choice?
7. Store → real listings?
8. Chat → sends to backend (if running)?
9. No Norse names visible anywhere?

---

## Gate Criteria
- [ ] Fresh install shows correct RAM + VRAM (nvidia-smi)
- [ ] Guided tour: Next works, tabs locked
- [ ] Agent name flows: sidebar, settings, nodes, config page
- [ ] Companion name flows: widget, chat
- [ ] Brain picker: settings matches onboarding
- [ ] Store: real listings from backend (even if local JSON)
- [ ] No "Offline mode" banner when backend is running
- [ ] No mock data visible on any page user can reach during tour
- [ ] `npm run build` passes
- [ ] `cargo tauri build` produces .exe

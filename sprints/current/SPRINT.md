# Sprint 16 — "Polish & Ship"

> **Goal:** Fix everything caught by Sprint 15 audit + user test.  
> **Timeline:** 1 day  
> **Source:** Heimdall audit S15, Valkyrie review S15, owner's user test

---

## 🔨 Thor (Backend + Tauri)

### T1. Store backend — wire to frontend 🔴
Sprint 15 added endpoints but Valkyrie confirms store page still shows mock data.
- Verify `GET /api/v1/store/plugins` returns 6 default plugins
- Verify `POST /api/v1/store/purchase` records to purchases.json
- Verify `GET /api/v1/store/purchases` returns purchase history
- Test: `curl http://127.0.0.1:8765/api/v1/store/plugins`

### T2. Backend auto-start verification 🔴
Sprint 15 added `setup()` hook in main.rs (confirmed by Heimdall). Needs:
- Rebuild .exe
- Test: launch app → backend starts automatically → no "Offline mode" banner
- Verify restart-on-crash (max 3)
- Verify kill-on-exit

### T3. BrainPicker brains → match onboarding 🟡
Onboarding says "Smart & Fast" / "Deep Thinker". BrainPicker shows different names.
- Read brain constants from shared config
- Store `fireside_brain` to localStorage during onboarding
- File: `InstallerWizard.tsx` (write), `BrainPicker.tsx` (read)

---

## 🎨 Freya (Dashboard Frontend)

### F1. Store page → real API 🔴
Replace mock store data with real backend calls:
- `GET /api/v1/store/plugins` → render plugin cards
- Install button → `POST /api/v1/store/purchase` → show confirmation
- Purchase history from `GET /api/v1/store/purchases`
- Handle loading/error states
- Files: `dashboard/app/store/page.tsx`

### F2. Guild Hall visual upgrade 🟡
User feedback: "ugly as fuck" / "needs Game Dev Story quality pixel art"
- Reference: Game Dev Story pixel art quality, Claude office ambient style
- Higher-res sprites (48px or 64px)
- Warm ambient background (fireside cabin)
- Agents doing contextual activities with smooth idle animations
- Files: `GuildHall.tsx`, `GuildHallAgent.tsx`, `AvatarSprite.tsx`

### F3. "Coming Soon" on unreachable pages 🟢
Sprint 15 added `ComingSoon.tsx` component. Verify it's used on:
- `/learning`, `/warroom`, `/crucible`, `/debate`, `/pipeline`
- Files: each page's `page.tsx`

---

## 🛡️ Heimdall (Audit)

### H1. Store purchase auth
Add `fireside_auth_token` validation to `POST /api/v1/store/purchase` (MEDIUM from S15 audit).

### H2. Verify MorningBriefing fix
Confirm `MorningBriefing.tsx` reads `fireside_user_name`, not "Odin!".

### H3. Verify companion key consistency
Confirm `InstallerWizard.tsx` writes `fireside_companion` JSON.

---

## 📋 Valkyrie (QA)

### V1. Full fresh install end-to-end
Same as Sprint 15 V1 but REBUILD .EXE FIRST:
1. Clear state (`%LOCALAPPDATA%\ai.fireside.app` + `~/.fireside`)
2. Install fresh .exe
3. System check: ~64GB RAM + ~32GB VRAM ← **MUST verify this time**
4. Name agent "Atlas", pick fox "Ember"
5. Tour: Next works, tabs locked
6. Store: real plugin listings from backend
7. Chat: works when backend running
8. Settings brain: matches onboarding choice
9. No "Odin" anywhere
10. No "Offline mode" when backend is auto-started

---

## Gate Criteria
- [ ] Backend auto-starts from Tauri → no "Offline mode"
- [ ] Store shows real plugins from `GET /store/plugins`
- [ ] Purchase flow works (record to JSON)  
- [ ] System specs show correct RAM + VRAM (nvidia-smi)
- [ ] MorningBriefing shows user's name, not "Odin"
- [ ] Brain picker matches onboarding
- [ ] Companion data available in GuildHall (JSON key)
- [ ] `npm run build` passes
- [ ] `cargo tauri build` produces .exe

# Sprint 20 — "Less is More" Valkyrie QA Review

**Date:** 2026-03-16
**Build:** `npm run build` → ✓ 27/27 pages, 0 errors

---

## Task Status

| Task | Status | Notes |
|------|--------|-------|
| F1: Sidebar → 6 tabs | ✅ PASS | **Your AI:** Chat, Personality. **World:** Guild Hall. **System:** Brains, Store, Settings. Down from 10. Clean groups. |
| F2: Settings Advanced sub-tabs | ✅ PASS | General + Advanced tabs with neon active indicator. Advanced: Connected Devices (lazy-loaded NodesPage), Task Builder ("coming soon"), Learning Stats ("coming soon"). |
| F3: Companion → Guild Hall | ✅ PASS | Companion removed from sidebar. User's GuildHall.tsx fix (`type: "companion"`) ensures companion renders as mascot sprite, not as an agent. |
| F4: Dashboard learning widget | ⚠️ NOTE | Not visible on `page.tsx` — dashboard currently shows companion widget, chat input, and welcome card. Learning widget could be a future addition. |
| H1: Removed routes don't 404 | ✅ PASS | `/nodes`, `/pipeline`, `/learning` still have page.tsx files (Coming Soon). `/companion` still has page.tsx. No dead links. |
| H2: Power user access | ✅ PASS | Connected Devices accessible via Settings > Advanced. Task Builder and Learning Stats have placeholder cards ready for future wiring. |

## Sidebar Architecture

The sidebar is now **3 clean groups**:
```
Your AI    → Chat, Personality
World      → Guild Hall
System     → Brains, Store, Settings
```
Plus "Your Team" section with `AgentSidebarList` at the bottom. Tour locking still functions on all 6 items.

## Settings Page

- **General tab:** SettingsForm + VoiceSettings + TelegramSetup
- **Advanced tab:** NodesPage (lazy-loaded via `dynamic()` — smart), Task Builder placeholder, Learning Stats placeholder
- Tab strip uses neon-on-black active state — consistent with app theme

## Build
✅ **27/27 pages, 0 type errors, 0 lint errors.**

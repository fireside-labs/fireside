# Freya Gate — Sprint 15 Ship It
Completed at 2026-03-16T00:12:00-07:00

## Completed
- [x] F1: GuidedTour rewritten — Next button, sidebar tab lock (🔒), steps: Dashboard → Brains → Chat → Done
- [x] F2: Brains page reads `fireside_brain` from localStorage, pre-selects onboarding choice
- [x] F3: Nodes page shows `fireside_agent_name` from onboarding instead of generic "Fireside"
- [x] F4: Store page tries `GET /api/v1/store/plugins`, falls back to hardcoded items
- [x] F5: 5 mock pages → Coming Soon (learning, warroom, crucible, debate, pipeline)
- [x] F6: GuildHall reads agent name/style + companion from localStorage, default theme → cozy
- [x] F7: Companion page already reads name from `fireside_companion` localStorage

## Files Changed/Created
| File | Change |
|---|---|
| `dashboard/components/GuidedTour.tsx` | [REWRITE] Next button, pathname-aware, href-based lock |
| `dashboard/components/Sidebar.tsx` | [MOD] useTour, locked tabs → 🔒, agent name from localStorage |
| `dashboard/app/brains/page.tsx` | [MOD] reads fireside_brain from localStorage |
| `dashboard/app/nodes/page.tsx` | [MOD] overrides "fireside" node with agent name |
| `dashboard/app/store/page.tsx` | [MOD] tries real API, dynamic tab counts |
| `dashboard/components/ComingSoon.tsx` | [NEW] reusable Coming Soon card |
| `dashboard/app/learning/page.tsx` | [REWRITE] → Coming Soon |
| `dashboard/app/warroom/page.tsx` | [REWRITE] → Coming Soon |
| `dashboard/app/crucible/page.tsx` | [REWRITE] → Coming Soon |
| `dashboard/app/debate/page.tsx` | [REWRITE] → Coming Soon |
| `dashboard/app/pipeline/page.tsx` | [REWRITE] → Coming Soon |
| `dashboard/components/GuildHall.tsx` | [MOD] reads agent/companion from localStorage, cozy default |

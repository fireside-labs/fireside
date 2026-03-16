# Freya Gate — Sprint 14 Frontend Complete
Sprint 14 tasks completed at 2026-03-15T22:42:00-07:00

## Completed
- [x] F1: CompanionChat → POST /api/v1/chat (canned fallback)
- [x] F2: BrainInstaller → SSE stream (simulated fallback)
- [x] F3: Fire theme (neon green → fire amber across all CSS)
- [x] F4: Removed Norse FRIENDLY_NAMES
- [x] F5: Add Node → mesh join-token dialog
- [x] F6: Save buttons already wired via api.ts (putSoul, updateConfig)
- [x] F7: SystemStatus polls GET /api/v1/status every 5s
- [x] F8: Mock fallback labeled via OfflineBanner
- [x] F9: OfflineBanner component (polls backend, checks wasLastCallMock)
- [x] F10: GuidedTour + TourOverlay (3-step onboarding with skip)

## Files Changed/Created
| File | Change |
|---|---|
| `dashboard/components/CompanionChat.tsx` | [MOD] → real POST /api/v1/chat |
| `dashboard/components/BrainInstaller.tsx` | [MOD] → SSE stream |
| `dashboard/app/globals.css` | [MOD] neon green → fire amber |
| `dashboard/app/nodes/page.tsx` | [MOD] Norse names removed, Add Node wired |
| `dashboard/components/SystemStatus.tsx` | [MOD] → polls /api/v1/status |
| `dashboard/lib/api.ts` | [MOD] friendly_name, mock tracking |
| `dashboard/components/OfflineBanner.tsx` | [NEW] |
| `dashboard/components/GuidedTour.tsx` | [NEW] |
| `dashboard/app/layout.tsx` | [MOD] + OfflineBanner + TourProvider |

## Build Status
- Mobile TypeScript: ✅ 0 errors

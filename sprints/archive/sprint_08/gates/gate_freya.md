# Freya Gate — Sprint 8 Frontend Complete
Sprint 8 tasks completed at 2026-03-15T15:25:00-07:00

## Completed
- [x] Settings screen (mode switch, connection, voice, notifications, privacy, about)
- [x] Onboarding v2 (self-hosted QR/IP + waitlist email, mode select, permissions)
- [x] Mode rename (Pet→Companion, Tool→Executive — display only)
- [x] Marketplace browse-only (paid items show "Purchase on desktop dashboard")
- [x] TestFlight pre-flight (app renamed Fireside, permissions verified, no console.log spam)
- [x] Theme overhaul (neon-green → fire-orange per Creative Direction)

## Files Changed/Created
| File | Change |
|---|---|
| `mobile/src/theme.ts` | [MOD] Complete palette swap: #00ff88 → #E8712C, added ember/warmGlow tokens |
| `mobile/app/settings.tsx` | [NEW] Settings screen with 7 sections |
| `mobile/app/onboarding.tsx` | [MOD] v2 with dual-path (self-hosted + waitlist), hasOnboarded export |
| `mobile/src/api.ts` | [MOD] Added waitlist() method |
| `mobile/app/(tabs)/_layout.tsx` | [MOD] Mode comments renamed Companion/Executive |
| `mobile/app/(tabs)/marketplace.tsx` | [MOD] Browse-only for paid items, paidNote styles |
| `mobile/app.json` | [MOD] name→Fireside, slug→fireside-ai |

## Build Status
- TypeScript: ✅ 0 errors
- TestFlight: ✅ Ready (`npx eas-cli@latest build --platform ios --profile preview`)

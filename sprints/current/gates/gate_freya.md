# Freya Gate — Sprint 16 Polish & Ship
Completed at 2026-03-16T00:50:00-07:00

## Completed
- [x] F1: Store → real API (ItemCard→POST /api/v1/store/purchase, PurchaseHistory→GET /api/v1/store/purchases)
- [x] F2: Guild Hall visual upgrade (warm ambient fireplace glow, 64px sprites, layered background, larger furniture)
- [x] F3: Coming Soon pages verified (from Sprint 15)

## Files Changed
| File | Change |
|---|---|
| `dashboard/components/ItemCard.tsx` | [MOD] handleBuy→POST /api/v1/store/purchase, added `id` destructuring |
| `dashboard/components/PurchaseHistory.tsx` | [REWRITE] fetches from GET /api/v1/store/purchases, loading skeleton, empty state |
| `dashboard/components/GuildHall.tsx` | [MOD] warm ambient glow, layered floor, wall line, larger furniture (text-3xl), hover effects |
| `dashboard/components/GuildHallAgent.tsx` | [MOD] sprite size 56px→64px |

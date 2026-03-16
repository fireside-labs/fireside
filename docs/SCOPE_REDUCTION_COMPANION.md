# Scope Reduction: Companion System

> **Decision date:** 2026-03-16
> **Source:** Freya + Jordan design review

## What STAYS

- **Visual mascot** — companion sits next to agent in Guild Hall, reacts to status effects (tail wag, curl up, happy bounce)
- **Onboarding choice** — user picks species + names it (emotional hook)
- **Push notification avatar** — "Ember says: your task is done!" on mobile
- **Guild Hall presence** — sprite rendered via `SpriteCharacter.tsx`

## What gets CUT

- ❌ `bag.tsx` — inventory/items system (scope bloat)
- ❌ `care.tsx` — feeding/caring screens (not a Tamagotchi)
- ❌ Leveling/XP system — complexity without revenue
- ❌ Mobile companion management screens
- ❌ Companion stats backend

## Where energy goes INSTEAD

- 🏰 **Guild Hall scene** — THE product differentiator. Interactive, LimeZu-quality, Kairosoft-feel
- 🎨 **Environment packs & skins** — actual monetization (themes, furniture, character outfits)
- 📱 **Mobile stays lean** — chat, tasks, push notifications. That's it.

## Files affected

| File | Action |
|------|--------|
| `mobile/app/(tabs)/bag.tsx` | Remove or replace with "Coming Soon" |
| `mobile/app/(tabs)/care.tsx` | Remove or replace with "Coming Soon" |
| `mobile/app/(tabs)/_layout.tsx` | Remove bag/care tabs |
| `plugins/companion/handler.py` | Keep notification logic, strip leveling |
| `dashboard/components/GuildHall.tsx` | Keep + enhance companion rendering |
| `dashboard/app/companion/page.tsx` | Simplify to mascot view only |

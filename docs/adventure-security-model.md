# Adventure Security Model

> **Module:** `plugins/companion/adventure_guard.py`  
> **Tests:** `tests/test_adventure_security.py` (37 tests)  
> **Sprint:** 14

---

## 1  Adventure Encounters — Server-Authoritative

| Check | Enforcement |
|-------|------------|
| Encounter types | 8-type whitelist (riddle, treasure, merchant, forage, lost_pet, weather, storyteller, challenge) |
| Loot table integrity | Drop chances must sum ≤ 1.0, no negative rates |
| XP rewards | Capped at 100 per encounter |
| Happiness changes | Bounded ±50 per choice |
| Adventure results | **HMAC-SHA256 signed by server** — client cannot forge rewards |
| Result freshness | Signatures expire after 5 minutes |

### Why server-signing matters
Without it, a user could modify localStorage and claim:
```json
{"type": "riddle", "reward": {"xp": 99999, "item": "legendary_bone"}}
```
With signing, the server issues a signature when the adventure starts. The client can only claim the exact rewards the server approved.

## 2  Inventory

| Rule | Limit |
|------|-------|
| Max slots | 20 |
| Max stack size | 99 per item |
| Duplicate items | Blocked (same item can't appear in two slots) |
| Item names | `^[a-z][a-z0-9_]{0,49}$` only |
| Trade validation | Must have item + sufficient count, inventory must have room |
| Action whitelist | `use`, `equip`, `unequip`, `trade`, `discard` |

## 3  "Teach Me" Facts

| Check | Detail |
|-------|--------|
| Max facts | 200 per user |
| Max length | 500 chars |
| Injection scan | 6 patterns (ignore instructions, system:, pretend, override) |
| PII detection | SSN, credit card, email, phone → **warning, not blocked** |

## 4  Morning Briefing

- Field whitelist: only safe stats fields allowed
- Numeric bounds: values clamped to sane ranges
- No internal data (API keys, tokens) can leak into briefing

---

*Adventure security model. Heimdall — Sprint 14 (2026-03-11).*

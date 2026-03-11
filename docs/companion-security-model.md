# Companion Security Model

> **Module:** `plugins/companion/relay.py`  
> **Tests:** `tests/test_companion_security.py` (37 tests)  
> **Sprint:** 13

---

## 1  Relay Server (E2E Encrypted)

```
Phone ──[encrypted]──→ Relay ──[encrypted]──→ Home PC
                    (can't read)
```

| Feature | Implementation |
|---------|---------------|
| Message signing | HMAC-SHA256 with shared secret from QR pairing |
| Token lifetime | 24 hours, auto-rotated daily |
| Rate limit | 100 messages/minute per device |
| Message validation | Type whitelist, timestamp freshness (5 min), 1MB payload max |

## 2  Task Queue

| Check | Enforcement |
|-------|------------|
| Task types | Whitelisted: `clean_photos`, `draft_text`, `math_calc`, etc. (9 types) |
| Injection scan | 9 patterns: `<script>`, `eval()`, `exec()`, `__import__`, `subprocess`, etc. |
| Description limit | 2,000 chars |
| Queue capacity | 50 tasks max |
| Source verification | Must be `companion_chat`, `companion_quick_action`, or `companion_voice` |

## 3  Pet State Integrity

| Attack | Mitigation |
|--------|-----------|
| XP manipulation via localStorage | HMAC-SHA256 signing — server signs, client stores, server verifies |
| Level cheating | XP-level consistency check (XP can't exceed `(level+1) × 20 + 100`) |
| Invalid species | 6-species whitelist: cat, dog, penguin, fox, owl, dragon |
| Stat overflow | All bars (hunger, mood, energy) bounded 0–100 |

## 4  Offline Privacy

| Rule | Status |
|------|--------|
| Conversations local-only | ✅ Enforced — no sync |
| Cloud fallback | ❌ Blocked — pet handles offline alone |
| Task queue encryption | AES-256 at rest |
| Photo upload | Requires existing auth token |
| Translation | NLLB runs on-device (600MB) |

---

*Companion security model. Heimdall — Sprint 13 (2026-03-11).*

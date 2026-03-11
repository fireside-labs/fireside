# Payment Security Model

> **Module:** `plugins/payments/security.py`  
> **Tests:** `tests/test_payment_security.py` (39 tests)  
> **Sprint:** 9

---

## 1  Stripe Integration Security

### Webhook Verification

| Check | Implementation |
|-------|---------------|
| Signature algorithm | HMAC-SHA256 (Stripe standard) |
| Comparison | Timing-safe `hmac.compare_digest` |
| Replay protection | Timestamp tolerance (default 300s) |
| Multi-signature | Accepts multiple v1 signatures (Stripe rollover) |
| Missing fields | Rejected with specific error |

### Credit Card Details
**NEVER stored.** All payment processing delegated to Stripe. Valhalla only stores:
- Payment intent ID
- Amount + fee breakdown
- Buyer/seller identifiers
- Timestamp

---

## 2  Purchase Receipt Chain

```
Receipt N-1                    Receipt N
┌─────────────┐               ┌─────────────┐
│ receipt_hash │──prev_hash──→│ receipt_hash │
│ prev_hash    │               │ prev_hash    │
│ amount       │               │ amount       │
│ buyer/seller │               │ buyer/seller │
└─────────────┘               └─────────────┘
```

- **Immutable:** Append-only log, no edits
- **Hash-chained:** Each receipt's `prev_hash` = previous receipt's `receipt_hash`
- **Tamper detection:** `verify_chain()` recomputes all hashes, detects any modification
- **Platform fee:** 30% cut automatically calculated and logged

---

## 3  Card Testing Prevention

| Rule | Limit |
|------|-------|
| Purchase attempts per IP/hour | 10 |
| Failed payments per IP/hour | 3 |
| Detection action | CRITICAL log, request blocked |

---

## 4  Store Content Scanning

| Content Type | Validation |
|-------------|-----------|
| SVG themes | 10 dangerous patterns blocked (script, onclick, javascript:, foreignObject, iframe, embed, object, external xlinks) |
| Voice packs | Magic byte validation (WAV, OGG, MP3, FLAC), rejects executables (PE/ELF headers), 10MB max |
| Personality presets | Same 26 injection patterns from `personality_guard.py`, slider bounds check |

---

*Payment security model. Heimdall — Sprint 9 (2026-03-10).*

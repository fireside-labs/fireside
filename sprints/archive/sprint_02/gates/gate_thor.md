# Thor Gate — Sprint 2 Backend Complete
Sprint 2 tasks completed.

## Completed
- [x] CORS wildcard replaced with explicit allowlist
- [x] /mobile/pair requires auth header
- [x] Rate limiting on pair endpoint (3/min)
- [x] Token TTL reduced to 15 minutes
- [x] Chat history endpoints (POST + GET)
- [x] /mobile/sync handles no-companion state
- [x] IP format validation

## Files Changed
- `valhalla.yaml` — Removed `"*"` from cors_origins, kept localhost entries
- `bifrost.py` — Added `allow_origin_regex` for Tailscale/LAN IPs (100.x, 192.168.x, 10.x)
- `plugins/companion/handler.py` — Auth, rate limit, TTL, chat history, adoption flow, IP validation
- `tests/test_sprint2_security.py` — 27 tests, all passing

## Test Results
```
27 passed in 0.5s
```

Freya can start.

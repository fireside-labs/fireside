# Thor Gate — Sprint 5 Backend Complete
Sprint 5 tasks completed.

## Completed
- [x] Adventure rewards: server-side encounter storage (`_active_encounters` dict, 5-min expiry, client rewards ignored)
- [x] /mobile/unregister-push endpoint (deletes push_token.json)
- [x] Platform activity in /mobile/sync (uptime, models, memory, plugins, predictions, mesh nodes — graceful fallbacks)
- [x] Proactive guardian check-in (time-aware, species-specific late-night messages for all 6 species)
- [x] Translation API verified for mobile (POST /translate + GET /translate/languages — already existed)

## Files Changed
- `plugins/companion/handler.py` — Server-side encounter storage, unregister-push, platform activity, guardian check-in
- `tests/test_sprint5_platform.py` — NEW: 26 tests, all passing

## Test Results
All 124 tests passing (Sprint 1: 15, Sprint 2: 27, Sprint 3: 27, Sprint 4: 29, Sprint 5: 26).

## Security Fix
🟡 **Heimdall MEDIUM fixed:** Adventure rewards no longer come from client body. Server stores encounter on `/generate`, pops on `/choose`. Client can only submit `choice_index`. Encounter expires after 5 min.

## New Endpoints for Freya
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/companion/mobile/unregister-push` | Remove push token |
| GET | `/api/v1/companion/guardian/check-in` | Late-night warning on chat open |
| POST | `/api/v1/companion/translate` | Translate text (200 languages) |
| GET | `/api/v1/companion/translate/languages` | List supported languages |

Freya can start.

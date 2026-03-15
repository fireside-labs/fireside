# Thor Gate — Sprint 6 Backend Complete
Sprint 6 tasks completed.

## Completed
- [x] Voice endpoints (transcribe + speak) via existing Whisper/Kokoro — local-only, no cloud
- [x] Marketplace browse/search/detail/install endpoints — wraps existing marketplace plugin
- [x] Web page summary endpoint (via browse/parser.py) — powers iOS share sheet
- [x] WebSocket for real-time companion sync (ping/pong, on-demand sync, broadcast)
- [x] Morning briefing placeholder fix (null defaults, validate_briefing_data)

## Files Changed
- `plugins/companion/handler.py` — Voice, marketplace, browse, WebSocket, morning briefing endpoints
- `tests/test_sprint6_platform.py` — NEW: 36 tests, all passing

## Test Results
All 160 tests passing (Sprint 1: 15, Sprint 2: 27, Sprint 3: 27, Sprint 4: 29, Sprint 5: 26, Sprint 6: 36).

## New Endpoints for Freya
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/voice/transcribe` | STT (multipart audio upload, 25MB max) |
| POST | `/api/v1/voice/speak` | TTS (returns audio/wav stream) |
| GET | `/api/v1/marketplace/browse` | Browse items (?category=) |
| GET | `/api/v1/marketplace/search` | Search (?q=) |
| GET | `/api/v1/marketplace/item/{id}` | Item detail |
| POST | `/api/v1/marketplace/install` | Install free item |
| POST | `/api/v1/browse/summarize` | Summarize URL for share sheet |
| WS | `/api/v1/companion/ws` | Real-time state updates |
| GET | `/api/v1/companion/morning-briefing` | Briefing with null fallbacks |

Freya can start.

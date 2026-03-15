# Thor Gate — Sprint 8 Backend Complete
- [x] Hosted waitlist endpoint (POST /api/v1/waitlist)
- [x] Email validation + dedup + rate limit

## Details
- `POST /api/v1/waitlist` — email regex, `.strip().lower()`, dedup in `~/.valhalla/waitlist.json`
- Rate limit: 10 signups/min (in-memory counter, 429 on excess)
- 16 new tests in `tests/test_sprint8_waitlist.py`
- **207 total tests passing** (Sprints 1-8)

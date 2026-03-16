# Thor Gate — Sprint 15 Complete (Ship It)
- [x] T1 — Backend auto-start: `setup()` hook spawns bifrost.py, restart-on-crash (max 3), kills on `RunEvent::Exit`, `get_backend_status` command
- [x] T2 — VRAM verified: nvidia-smi → WMI fallback on Windows, sysctl on Mac, nvidia-smi on Linux
- [x] T3 — Store backend: `GET /store/plugins` (local JSON registry), `POST /store/purchase` (with 404/409), `GET /store/purchases`
- [x] T4 — Config sync: `GET /config/onboarding` returns agent_name, companion_name, brain, onboarded flag from config

## Files Modified
| File | Change |
|------|--------|
| `tauri/src-tauri/src/main.rs` | T1: setup() hook, BackendState, spawn_backend, exit cleanup, get_backend_status |
| `api/v1.py` | T3: 3 store endpoints + local JSON registry. T4: config/onboarding endpoint |
| `tests/test_sprint15_shipit.py` | NEW — 34 tests |

## Test Results
**444 tests passing** (Sprints 1-15)

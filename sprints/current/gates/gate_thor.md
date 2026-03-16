# Thor Gate — Sprint 14 Complete (Last Mile Wiring)
- [x] T1 — Mac unified memory: `sysctl hw.memsize` for macOS, `nvidia-smi` for Linux
- [x] T2 — `POST /api/v1/chat`: SSE proxy to llama.cpp at 127.0.0.1:8080, companion personality from config
- [x] T3 — `POST /api/v1/brains/install`: GGUF download to ~/.fireside/models/ with SSE progress streaming
- [x] T4 — `GET /api/v1/guildhall/agents`: real agents from config with live activity status
- [x] T5 — `POST /api/v1/nodes`: device registration with config persistence + 409 conflict detection
- [x] T6 — Port fix: `API_BASE` in api.ts changed from 8766 → 8765

## Files Modified
| File | Change |
|------|--------|
| `tauri/src-tauri/src/main.rs` | T1: macOS sysctl + Linux nvidia-smi VRAM detection |
| `api/v1.py` | T2-T5: 4 new endpoints (chat, brains/install, guildhall/agents, nodes) |
| `dashboard/lib/api.ts` | T6: port 8766 → 8765 |
| `tests/test_sprint14_lastmile.py` | NEW — 42 tests |

## Test Results
**410 tests passing** (Sprints 1-14)

# Thor Gate — Sprint 21 Complete ("Finish the Install")
- [x] T1 — download_brain Tauri command:
    - [x] Downloads GGUF from HuggingFace CDN
    - [x] Cross-platform: PowerShell (Windows) / curl (macOS/Linux)
    - [x] Already-installed detection (>100MB file)
    - [x] Maps fast→llama-3.1-8b-q6, deep→qwen-2.5-35b-q4
- [x] T2 — test_connection Tauri command:
    - [x] TCP connect to 127.0.0.1:8765 with 10 retries
    - [x] HTTP health check against /api/v1/status/agent
    - [x] Returns "connected:{body}" on success

## Files Modified
| File | Change |
|------|--------|
| `tauri/src-tauri/src/main.rs` | Added `download_brain` + `test_connection`, registered in handler |
| `tests/test_sprint21_finishinstall.py` | NEW — 17 tests |

## Test Results
**549 tests passing** across 21 sprints.

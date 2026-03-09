# Dispatch Bugs Postmortem — 2026-03-09

## Summary

Six dispatch bugs were blocking pipeline execution. All found and fixed in one session.

**Verification:** Thor completed both pipeline build tasks. Telegram confirmed `BUILD COMPLETE` via `llama/qwen3.5-35b` local Q6_K inference.

---

## Bug 1: TaskPoller `accepted` vs `ok` (FIXED — `3380c3e`)

`/dispatch` returns `"accepted"` (async 202), TaskPoller only checked for `"ok"`. Every pipeline task immediately went `blocked`.

**Fix:** Handle `"accepted"` status, poll every 15s for completion.

## Bug 2: `openclaw.ps1` Blocked on Windows (FIXED — `82d35a2`)

`shutil.which("openclaw")` finds `.ps1` first. Execution policy blocks it. Agent subprocess silently fails.

**Fix:** Prefer `openclaw.cmd` on `win32`.

## Bug 3: Gateway Dying (Start-Job GC) (FIXED — manual)

Gateway launched via `Start-Job` dies when job is garbage collected.

**Fix:** Launch via `cmd.exe` detached process. Needs scheduled task for persistence.

## Bug 4: API Key Mismatch `local` vs `ollama` (FIXED)

Gateway sends `Bearer local`, llama-server expected `--api-key ollama`. Agent gets 401.

**Fix:** Changed `llama-server.cmd` to `--api-key local`.

## Bug 5: Thor Identifying as Freya (FIXED)

`config.json` had `"this_node": "freya"` — cloned from Freya, never updated. Dispatch self-reported as Freya for tasks assigned to Thor. Completions silently mismatched.

**Fix:** Changed to `"this_node": "thor"`, `"agent.id": "thor"`.

## Bug 6: Odin Gateway localhost-only (FIXED by Odin)

Gateway bound to `127.0.0.1:18789`. Separate channel from pipelines.

**Fix:** `openclaw config set gateway.bind lan`.

---

## All Commits

| Commit | Fix |
|--------|-----|
| `3477e6b` | `OLLAMA_BASE` / `MLX_BASE` env vars |
| `9461440` | `OLLAMA_EMBED_BASE` env var |
| `3380c3e` | TaskPoller async dispatch handling |
| `82d35a2` | Prefer `openclaw.cmd` on Windows |

## Config Fixes on Thor

| Item | Change |
|------|--------|
| `config.json` | `this_node: "thor"`, `agent.id: "thor"` |
| `openclaw.json` | Added `"bind": "lan"` |
| `llama-server.cmd` | `--api-key local` |
| `models.json` | Ollama port 11434 → 11435 |
| Firewall | Ports 8765, 18789, 8080 |

## Deployment Status

- [x] Thor — all fixes, pipeline verified ✅
- [x] Freya — pulled code fixes
- [x] Heimdall — pulled code fixes
- [x] Odin — gateway.bind = lan

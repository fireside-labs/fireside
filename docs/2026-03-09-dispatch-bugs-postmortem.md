# Dispatch Bugs Postmortem — 2026-03-09

## Summary

Two separate dispatch bugs were blocking all pipeline execution across the mesh. They appeared as a single symptom ("pipeline tasks go `blocked` immediately") but had different root causes on different code paths.

---

## Bug 1: TaskPoller `accepted` vs `ok` Status Mismatch (FIXED)

**Severity:** Critical — broke ALL pipeline execution on ALL nodes  
**Commit:** `3380c3e`  
**Affected file:** `bifrost.py` — `TaskPoller._process_task()`

### Root Cause

The `/dispatch` endpoint (`routes.py:458`) was refactored to run the OpenClaw agent **asynchronously** in a background thread, returning immediately with:

```json
{"status": "accepted", "task_id": "...", "message": "Agent session started in background"}
```

But `TaskPoller._process_task()` (`bifrost.py:1744`) only checked for `"ok"`:

```python
dispatch_status = result_data.get("status", "error")
if dispatch_status == "ok":
    result_text = result_data.get("result", "completed (no output)")
else:
    raise RuntimeError(result_data.get("error", "dispatch failed"))  # ← BUG
```

Since `"accepted" != "ok"`, every dispatch raised `RuntimeError`, which triggered the exception handler at line 1759 that marks the task `blocked`. The background agent would eventually complete and self-report via `/war-room/complete`, but by then the task was already marked `blocked` — and the TaskPoller wouldn't retry it.

### Why Simple Tasks Worked

Simple tasks (ping, reply, etc.) were dispatched via **direct HTTP POST to `/dispatch`** from external callers (Odin, test scripts). Those callers didn't check the status field — they just fired and forgot. The background agent ran, completed, and self-reported via `/war-room/complete`. This path never went through `TaskPoller._process_task()`.

Pipeline subtasks were different: they were created as `open` tasks in the War Room by `pipeline.py:_start_stage()`, then picked up by the `TaskPoller`, which **did** check the status field — and failed.

### Fix

Accept both `"ok"` (sync) and `"accepted"` (async) status values. For async, poll the War Room every 15s until the task moves to `done` or times out after 5.5 minutes.

### The Flow (Before vs After)

```
BEFORE (broken):
  TaskPoller picks up open task
  → POST /dispatch → returns {status: "accepted"}
  → "accepted" != "ok" → RuntimeError
  → task marked "blocked" (instantly, ~0ms)
  → background agent finishes 30s later, calls /war-room/complete
  → but task is already blocked, completion ignored

AFTER (fixed):
  TaskPoller picks up open task
  → POST /dispatch → returns {status: "accepted"}
  → "accepted" handled → polls every 15s for completion
  → background agent finishes → calls /war-room/complete → task = "done"
  → TaskPoller sees done → exits poll loop → task complete
```

---

## Bug 2: Odin Gateway Bound to localhost (OPEN — needs Odin-side fix)

**Severity:** Medium — blocks the OpenClaw node client dispatch channel  
**Affected:** Odin's `openclaw.json` on Mac

### Root Cause

Odin's OpenClaw gateway is listening on `127.0.0.1:18789` instead of `0.0.0.0:18789`. All three node clients (`node.cmd` on Thor, Freya, Heimdall) connect to Odin's Tailscale IP `100.105.27.121:18789` — but since the gateway only binds to localhost, TCP connections from other nodes stay in `SYN_SENT` indefinitely.

Telegram correctly reports all nodes as "paired but disconnected."

### Why Pipelines Still Work

Pipeline dispatch does NOT use this path. The two dispatch channels are:

| Channel | Path | Used By | Status |
|---------|------|---------|--------|
| **Bifrost TaskPoller** | War Room (8765) → local `/dispatch` → local `openclaw agent` → local gateway (18789) | Pipeline subtasks | ✅ Fixed (Bug 1) |
| **OpenClaw Node Client** | `node.cmd` → WebSocket → Odin gateway (18789) → agent dispatch | Direct Odin → Node dispatch | ❌ Blocked (Bug 2) |

The pipeline path is entirely local to each node — TaskPoller reads from the local War Room, dispatches to the local `/dispatch` endpoint, which runs `openclaw agent` against the LOCAL gateway at `127.0.0.1:18789`. No cross-node gateway traffic needed.

The node client path is for Odin to push work directly to a specific node's agent without going through the War Room. This is currently broken for all nodes because Odin's gateway doesn't accept remote connections.

### Fix (Odin needs to run)

```bash
# On Odin's Mac:
openclaw config set gateway.bind lan

# Then restart:
lsof -ti:18789 | xargs kill -9
sleep 2
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# Verify:
lsof -i:18789 | grep LISTEN
# Should show *:18789, not 127.0.0.1:18789
```

---

## Other Fixes Shipped Tonight

| Commit | Fix | Impact |
|--------|-----|--------|
| `3477e6b` | `OLLAMA_BASE` / `MLX_BASE` configurable via env vars | `/ask local` works on nodes where Ollama moved to 11435 |
| `9461440` | `OLLAMA_EMBED_BASE` env var (default 11435) | Embedding calls in `hydra.py` and `bifrost.py` no longer hit llama-server |
| `3380c3e` | TaskPoller `accepted` status handling | Pipeline subtasks actually execute instead of going blocked |

## Config Fixes Applied to Thor

| Item | Change |
|------|--------|
| `openclaw.json` gateway | Added `"bind": "lan"` for Tailscale-accessible gateway |
| Windows Firewall | Inbound rules for ports 8765, 18789, 8080 |
| Env vars | `NVIDIA_API_KEY`, `OLLAMA_BASE=11435`, `OLLAMA_EMBED_BASE=11435` set persistent |
| Q6_K model | Swapped from Q4_K_M → Q6_K (28GB, ~137 tok/s, q8_0 KV cache, flash-attn) |

## Nodes That Need `git pull github main` + Bifrost Restart

- [x] Thor — pulled and restarted
- [ ] Freya — needs pull + restart for Bug 1 fix
- [ ] Heimdall — needs pull + restart for Bug 1 fix
- [ ] Odin — needs pull + restart for Bug 1 fix, PLUS `gateway.bind = lan` for Bug 2

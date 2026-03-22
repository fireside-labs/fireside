# Known Issues & Fixes

> Living document — every bug found per plugin and how it was resolved.

---

## agent_profiles (`plugins/agent_profiles/handler.py`)

### 1. 503 "No brain installed" — chat routing broken
- **Symptom:** Dashboard fell back to raw llama-server `:8080` (no tools)
- **Cause:** `_get_active_brain()` only checked `~/.valhalla/brains_state.json`, which doesn't exist for most users
- **Fix:** Added fallback to `brain_manager.get_status()` to detect running llama-server
- **Commit:** `a310d33`

### 2. Tools never sent to model
- **Symptom:** Ember said "I don't have internet access" — model didn't know tools existed
- **Cause:** `_stream_chat()` was a simple proxy — never included `tools` array in the llama-server request
- **Fix:** Rewrote as full tool-calling agent loop with `tool_defs.TOOL_SCHEMAS`
- **Commit:** `ee98524`

### 3. Dashboard got SSE when expecting JSON
- **Symptom:** Dashboard's `res.json()` failed silently → fell back to raw llama-server
- **Cause:** Dashboard sends `stream: false`, but endpoint always returned `text/event-stream`
- **Fix:** Added `stream` field to `ChatRequest`. When `false`, collects tool results and returns `{response, agent, brain, tools_used}` as JSON
- **Commit:** `ee98524`

### 4. `str + None` crash → 500
- **Symptom:** "Sorry, I encountered an error: can only concatenate str (not NoneType) to str"
- **Cause:** llama-server returns `"content": null` during tool call rounds. `msg.get("content", "")` returns `None` (key exists with null value), not `""` (the default for missing keys)
- **Fix:** Changed to `msg.get("content") or ""`
- **Commit:** `aa9d7e3`

### 5. XML-style tool calls not parsed
- **Symptom:** Model returned raw `<tool_call><function=files_write>...` XML as text instead of executing
- **Cause:** Some GGUF chat templates output tool calls as XML in `content` instead of structured `tool_calls` JSON
- **Fix:** Added regex parser that detects `<tool_call>` tags, extracts function name + parameters, executes via `execute_tool()`, and strips leaked XML from final response
- **Commit:** `fe9d571`

### 6. Model refuses to use tools ("security rules")
- **Symptom:** Ember says "I can't write to your hard drive" or "I don't have internet access"
- **Cause:** System prompt (SOUL.md/IDENTITY.md) never mentioned tools — model invented restrictions
- **Fix:** Added "Your Capabilities" section to `_load_system_prompt()` listing all 16 tool names + explicit instruction to USE them
- **Commit:** `09d3b48`

### 7. Empty response after successful tool execution
- **Symptom:** Tools ran (files_write, terminal_exec) but response text was blank
- **Cause:** Model's final text was all XML tool tags → stripped to empty string
- **Fix:** Added fallback summary: if response is empty but tools ran, generate "Done! I used X, Y to complete your request"
- **Commit:** `e7eed3c`

### 8. No conversation history — model had amnesia every message
- **Symptom:** User asked "move the file you just wrote" → Ember said "which file?"
- **Cause:** Dashboard sent only `{message}` to bifrost — no chat history. Each request was stateless
- **Fix:** Dashboard now sends `history: chatHistory.map(...)`. Backend prepends up to 10 previous messages to llama-server call
- **Note:** Ironically, `store_memory`/`recall_memory` (vector DB long-term memory) existed but the model had zero short-term memory
- **Commit:** conversation history fix

### 9. Context compaction existed but was never reachable
- **Symptom:** Both dashboard (`compactHistory`) and backend (`context-compactor` plugin) had compaction code, but it never triggered
- **Cause:** No history was sent → nothing to compact. Compaction at 60%/75% of context window requires messages to exist first
- **Fix:** Same as #8 — now that history flows through, compaction kicks in automatically when conversations get long

### 10. files_write BLOCKED on relative paths — model hallucinated success
- **Symptom:** Model said "File saved: ./Desktop/my_favorite_food.txt" but file didn't exist
- **Cause:** Model used relative paths (`./Desktop/`, `Desktop/`) which don't start with `C:/Users/Jorda/` → security check returned BLOCKED. Model ignored the BLOCKED response and told user it succeeded
- **Fix:** All file tools (`files_list`, `files_read`, `files_write`) now resolve `./path`, `~/path`, and bare relative paths against `Path.home()` before security check
- **Commit:** `564000f`

---

## dashboard (`dashboard/app/page.tsx`)

### 1. New conversation (+) button clears chat instead of saving
- **Symptom:** Pressing + clears the current conversation — it doesn't save to sidebar
- **Cause:** Button just resets `chatHistory` state — no persistence layer for conversations
- **Status:** 🔴 Open — needs conversation persistence (localStorage or backend storage)

### 2. Static build missing latest changes
- **Symptom:** User on port 3999 (`npx serve out`) doesn't get code updates
- **Cause:** Dashboard changes require `npx next build` to regenerate static files
- **Fix:** Rebuilt dashboard after conversation history changes
- **Note:** Dev server on port 4001 picks up changes automatically

### 3. Tauri exe uses stale Next.js cache — changes don't appear
- **Symptom:** Rebuilt Tauri exe still shows old UI (mascot, unstyled pages)
- **Cause:** `cargo tauri build` runs `npm run build`, but Next.js reuses `.next/` cache and old `out/` files without detecting component changes
- **Fix:** Always nuke cache before Tauri builds:
  ```powershell
  Remove-Item -Recurse -Force dashboard\.next, dashboard\out
  cd tauri\src-tauri; cargo tauri build
  ```
- **Commit:** `f7c214e`

### 4. Inline `@import url()` kills all styles in Tauri webview
- **Symptom:** Pages (pipeline, skills, installer) render completely unstyled in Tauri exe but look fine on localhost
- **Cause:** Tauri CSP blocks cross-origin `@import` inside inline `<style>` tags → entire style block silently fails
- **Fix:** Removed `@import url(fonts.googleapis.com)` from 3 inline CSS blocks. Fonts already loaded via `<link>` in `layout.tsx` `<head>`
- **Commit:** `32059c3`

### 5. Hub shows "No brain installed" despite brain running
- **Symptom:** Brain is active on port 8080 (visible on Brain Lab), but hub shows "⚠ No brain installed · Set up →"
- **Cause:** Hub only checked `localStorage.getItem("fireside_model")`, which is only set during the installer download flow. Pre-installed or externally-started brains were never detected
- **Fix:** Added API-based auto-detection — hub probes `/api/v1/status` on load and auto-populates brain label from the running model
- **Commit:** `61a2acf`

---

## brain_manager (`bot/brain_manager.py`)

### 1. Model re-downloaded on every startup
- **Symptom:** Installer downloaded model again even though it already existed
- **Cause:** No existence check before download
- **Fix:** Added `Path.exists()` check on model path before triggering download

### 2. Wrong binary/model paths for new users
- **Symptom:** llama-server not found, models not found
- **Cause:** Code searched `.openclaw/` which only exists for devs, not new users
- **Fix:** Prioritized `~/.fireside/bin/` for binary, `~/.fireside/models/` for models. `.openclaw` kept as legacy fallback only

---

## brain_installer (`plugins/brain_installer/`)

### 1. Pixelated emojis in installer
- **Symptom:** Dragon, brain, and animal pixel art looked bad during loading
- **Fix:** Replaced with actual companion mascot images from `/public/mascots/`

---

## pipeline (`plugins/pipeline/handler.py`)

### 1. Two separate tool registries
- **Symptom:** Chat had 10 tools (`bot/tools.py`), pipelines had 16 tools (`tool_defs.py`) — inconsistent capabilities
- **Fix:** Unified chat to use `tool_defs.py` (same registry as pipelines). `bot/tools.py` still exists for legacy but isn't used by the chat path
- **Commit:** `ee98524`

---

## bifrost (`bifrost.py`)

### 1. Startup crashes with no recovery
- **Symptom:** If llama-server failed to start, bifrost would hang or crash
- **Fix:** Multi-layered auto-recovery: tries progressively safer GPU flags, then CPU-only fallback

### 2. Dashboard broken during startup
- **Symptom:** Blank page or errors while bifrost was still loading
- **Fix:** Dashboard shows loading screen until bifrost health check passes

---

## General — Model Compatibility

### Tool calling format varies by GGUF template
Different models handle tool calling differently:

| Format | Example | Handled? |
|--------|---------|----------|
| Structured `tool_calls` JSON | `choices[0].message.tool_calls: [...]` | ✅ |
| XML in content | `<tool_call><function=name>...</function></tool_call>` | ✅ |
| `content: null` during tool rounds | Standard OpenAI protocol | ✅ |

> [!TIP]
> If adding support for a new model and tools don't work, check what format it uses for tool calls. The parser in `_stream_chat()` handles both structured JSON and XML formats.

---

## Chat UI (`dashboard/app/page.tsx`)

### 1. + button clears chat instead of saving — OPEN
- **Symptom:** Pressing + for new conversation clears the current one. Previous conversation is lost
- **Cause:** No persistence layer — chat history is only in React state / sessionStorage, not saved per-conversation
- **Fix needed:** Save conversations to localStorage or backend before clearing, load from sidebar

### 2. Tasks/Workflow tab still unstyled in Tauri — OPEN
- **Symptom:** Pipeline page renders fully styled on localhost:4001 but unstyled in Tauri exe
- **Cause:** Inline `<style>{pageCSS}</style>` pattern may have issues in Tauri webview beyond the `@import` fix
- **Fix needed:** Investigate Tauri CSP handling of large inline style blocks, or move to CSS module

---

## Tools — Known Failures (March 21 2026 testing)

### 1. create_docx sometimes fails to resolve path
- **Symptom:** Model runs `Get-ChildItem` to find username instead of using known path
- **Cause:** System prompt doesn't tell the model the user's home directory path
- **Fix needed:** Pass `HOME_DIR=C:\Users\Jorda` in system prompt context

### 2. list_schedules times out
- **Symptom:** Two consecutive timeout errors when listing schedules
- **Cause:** Scheduler plugin may not be running, or endpoint hangs
- **Fix needed:** Check `plugins/scheduler/handler.py` timeout handling

### 3. files_list on Documents folder returns incomplete results
- **Symptom:** Model showed `/Users` instead of listing Documents folder contents
- **Cause:** Model used relative path instead of absolute path
- **Fix needed:** Same as #1 — pass home dir in system prompt


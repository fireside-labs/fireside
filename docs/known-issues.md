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

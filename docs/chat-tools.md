# Chat + Tool-Calling Architecture

> How Ember uses tools (web search, file ops, etc.) inside the chat interface.

---

## Overview

```
┌─────────────┐       ┌──────────────────┐       ┌───────────────┐
│  Dashboard   │──────▶│  Bifrost :8765    │──────▶│ llama-server  │
│  (Next.js)   │  POST │  (FastAPI)       │  POST │   :8080       │
│              │◀──SSE─│                  │◀─JSON─│  (GGUF model) │
└─────────────┘       └──────┬───────────┘       └───────────────┘
                             │
                             │ tool_calls detected?
                             ▼
                      ┌──────────────┐
                      │  bot/tools.py │
                      │  execute_tool │
                      └──────────────┘
```

## Request Flow

### 1. Dashboard → Bifrost

**File:** `dashboard/app/page.tsx` → `handleSend()`

```
POST http://127.0.0.1:8765/api/v1/chat
Body: { "message": "search yahoo for headlines" }
```

If this fails (503, timeout), the dashboard falls back to raw llama-server `:8080` — **no tools** in that path.

### 2. Bifrost routes the request

**File:** `plugins/agent_profiles/handler.py` → `api_chat()`

1. `_get_active_brain()` finds which brain is running:
   - Checks `~/.valhalla/brains_state.json` (Brain Lab selection)
   - Falls back to `bot/brain_manager.get_status()` (auto-started llama-server)
   - Returns `None` → **503 "No brain installed"** (dashboard falls back, no tools)

2. `_load_system_prompt()` builds the system prompt from `SOUL.md` + `IDENTITY.md` + personality sliders

3. `_stream_chat()` runs the **tool-calling agent loop**

### 3. Tool-Calling Agent Loop

**File:** `plugins/agent_profiles/handler.py` → `_stream_chat()`

```python
for round in range(MAX_TOOL_ROUNDS):  # max 5
    # Send messages + tool definitions to llama-server
    payload = {
        "messages": [...],
        "tools": get_tool_definitions(),  # from bot/tools.py
        "stream": False,  # need full response to detect tool_calls
    }
    
    response = POST llama-server /v1/chat/completions
    
    if response has tool_calls:
        for each tool_call:
            result = execute_tool(name, args)  # bot/tools.py
            messages.append(tool result)
        continue  # send results back to model
    else:
        stream text response to user
        return
```

Key points:
- Non-streaming on tool rounds (need full JSON to detect `tool_calls`)
- Streaming on final round (for UX)
- Max 5 rounds prevents infinite loops
- Tool results are appended as `role: "tool"` messages

### 4. llama-server processes with tools

llama-server (with `--jinja` flag) supports OpenAI-compatible function calling:
- Receives `tools` array in the request
- Model decides whether to call a tool or respond directly
- Returns `tool_calls` in `choices[0].message.tool_calls`

---

## Tool Definitions

**File:** `bot/tools.py`

Tools are registered with `@register()` decorator and expose:
- `get_tool_definitions()` → OpenAI-compatible tool schemas
- `execute_tool(name, args)` → runs the tool function

### Available Tools

| Tool | Description | Key File |
|------|-------------|----------|
| `web_search` | DuckDuckGo search (no API key) | `bot/tools.py` |
| `http_request` | HTTP GET/POST | `bot/tools.py` |
| `browse_and_act` | Open website + interactive navigation | `bot/tools.py` + `plugins/browse/` |
| `read_file` | Read file contents | `bot/tools.py` |
| `write_file` | Write to `~/.fireside/outputs/` | `bot/tools.py` |
| `run_command` | Shell command (sandboxed, 30s timeout) | `bot/tools.py` |
| `create_document` | Generate PPTX/DOCX/TXT | `bot/tools.py` |
| `send_email` | SMTP email | `bot/tools.py` |
| `check_spending` | Spending limit check | `bot/tools.py` |
| `scan_message` | Scam/phishing detection | `bot/tools.py` |

### Adding a new tool

```python
# In bot/tools.py
@register(
    name="my_tool",
    description="What this tool does",
    parameters={
        "type": "object",
        "properties": {
            "arg1": {"type": "string", "description": "..."},
        },
        "required": ["arg1"],
    },
)
def my_tool(arg1: str) -> dict:
    return {"result": "..."}
```

No other wiring needed — `get_tool_definitions()` auto-discovers registered tools.

---

## Brain Detection

**File:** `bot/brain_manager.py`

At Bifrost startup, `auto_start()` finds and starts the model:

1. `~/.fireside/onboarding.json` → explicit model path
2. `valhalla.yaml` → `node.model_path`
3. Scan `~/.fireside/models/` for largest `.gguf` file

The llama-server binary is searched in:
1. `~/.fireside/bin/` (production)
2. `~/.openclaw/llama-server/` (legacy fallback)
3. System PATH
4. Common install locations (`~/llama.cpp/`, `C:/llama.cpp/`, etc.)

---

## Failure Modes & Fallbacks

| Symptom | Cause | Fix |
|---------|-------|-----|
| Chat works but no tools | Dashboard fallback to `:8080` | Ensure Bifrost is healthy on `:8765` |
| "No brain installed" (503) | `brains_state.json` missing + brain_manager not running | brain_manager auto-starts on boot |
| Model ignores tools | `--jinja` flag missing from llama-server | brain_manager always adds `--jinja` |
| Tool timeout | llama-server slow with large model + tools | Increase `_stream_chat` timeout |
| "Analyze the Request" thinking | Model not receiving tools, falling back to raw reasoning | Check Bifrost logs for 503/422 |

---

## File Map

```
bot/tools.py                          ← Tool registry + implementations
bot/brain_manager.py                  ← llama-server lifecycle
plugins/agent_profiles/handler.py     ← /api/v1/chat endpoint + agent loop
plugins/browse/handler.py             ← web_search (async version for plugins)
dashboard/app/page.tsx                ← handleSend() → bifrost or fallback
```

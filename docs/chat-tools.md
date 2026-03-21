# Chat + Tools + Pipeline Architecture

> How tools connect to both **Chat** and **Tasks/Pipeline** — unified system via `tool_defs.py`.

---

## Overview

```
                        ┌──────────────────────────────────────┐
                        │           Bifrost :8765               │
                        │           (FastAPI)                   │
┌─────────────┐         │                                      │         ┌───────────────┐
│  Dashboard   │──POST──│  /api/v1/chat     (agent_profiles)   │──POST──▶│ llama-server  │
│  Chat Tab    │◀─JSON──│    └─ tool_defs.py (all 16 tools)    │◀─JSON──│   :8080       │
└─────────────┘         │                                      │         │  (GGUF model) │
                        │                                      │         └───────────────┘
┌─────────────┐         │  /api/v1/pipeline  (pipeline plugin)  │──POST──▶     ↑ same
│  Dashboard   │──POST──│    └─ tool_defs.py (role-scoped)     │◀─JSON──      │
│  Tasks Tab   │◀─JSON──│                                      │              │
└─────────────┘         └──────────────────────────────────────┘
```

**Both use the same tool system** (`tool_defs.py`), same llama-server, same agent loop pattern.

---

## Tool Registry: `tool_defs.py`

Single source of truth for all tool schemas and execution logic.

### All 16 Tools

| Tool | Description |
|------|-------------|
| `files_list` | List directory contents |
| `files_read` | Read file contents |
| `files_write` | Create/save files (home dir only) |
| `files_delete` | Delete files (requires confirmation) |
| `terminal_exec` | Shell commands (sandboxed, 30s timeout) |
| `web_search` | DuckDuckGo via browse plugin |
| `browse_url` | Fetch and read a webpage |
| `create_schedule` | Set reminders/recurring tasks |
| `cancel_schedule` | Stop a scheduled task |
| `list_schedules` | Show active schedules |
| `store_memory` | Save to long-term memory |
| `recall_memory` | Search past memories |
| `create_pipeline` | Spawn multi-stage pipeline |
| `create_pptx` | Generate PowerPoint |
| `create_docx` | Generate Word doc |
| `create_xlsx` | Generate Excel spreadsheet |

### Adding a new tool

1. Add schema to `TOOL_SCHEMAS` list in `tool_defs.py`
2. Add executor case in `execute_tool()` function
3. Add tool name to relevant roles in `_ROLE_TOOL_MAP`

Both chat and pipelines pick it up automatically.

---

## Chat Tab Flow

**Files:** `dashboard/app/page.tsx` → `plugins/agent_profiles/handler.py`

```
Dashboard handleSend()
    │
    POST /api/v1/chat { message: "...", stream: false }
    │
    ▼
Bifrost api_chat()
    │
    _get_active_brain()  ──▶  1. ~/.valhalla/brains_state.json
    │                         2. brain_manager.get_status() (fallback)
    │
    _load_system_prompt()  ──▶  SOUL.md + IDENTITY.md + personality
    │
    stream=false? ──▶ JSON mode: run agent loop, return {response, tools_used}
    stream=true?  ──▶ SSE mode: stream chunks as text/event-stream
    │
    _stream_chat() agent loop (max 5 rounds):
    │
    ┌──▶ Send messages + TOOL_SCHEMAS → llama-server
    │         │
    │    tool_calls in response?
    │    yes ──▶ execute_tool() → append results → loop
    │    no  ──▶ return text response
    └────────
```

The dashboard sends `stream: false` and calls `res.json()`:
```json
{
  "response": "Here are today's top Yahoo headlines...",
  "agent": "ember",
  "brain": "local",
  "tools_used": ["web_search", "browse_url"]
}
```

---

## Tasks / Pipeline Tab Flow

**Files:** `dashboard/app/tasks/page.tsx` → `plugins/pipeline/handler.py`

```
Dashboard Tasks Tab
    │
    POST /api/v1/pipeline/start { task: "...", template: "research" }
    │
    ▼
Pipeline Plugin
    │
    Select template → map stages → assign roles
    │
    For each stage:
    │
    _call_llm_with_tools(prompt, role="researcher")
    │
    ┌──▶ tools = get_tools_for_role("researcher")
    │    Send prompt + scoped tools → llama-server
    │         │
    │    tool_calls? ──▶ execute_tool() → append → loop
    │    no          ──▶ return stage output → next stage
    └────────
```

### Role-Based Tool Scoping

Pipeline stages get **scoped subsets** — they don't get all 16 tools:

| Role | Tools Available |
|------|----------------|
| `planner` | files_list, files_read, web_search, recall_memory |
| `researcher` | files_list, files_read, web_search, browse_url, recall_memory |
| `backend` | files_list, files_read, files_write, terminal_exec, create_docx, create_xlsx |
| `frontend` | files_list, files_read, files_write, terminal_exec |
| `tester` | files_list, files_read, terminal_exec |
| `reviewer` | files_list, files_read |
| `writer` | files_list, files_read, files_write, store_memory, create_docx, create_pptx |
| `executor` | files_list, files_read, files_write, terminal_exec, create_pptx, create_docx, create_xlsx |

**Always blocked in pipelines:** `files_delete`, `create_pipeline`, `create_schedule` (prevents recursion/destructive ops).

---

## Brain Detection

**File:** `bot/brain_manager.py`

At startup, resolves in order:
1. `~/.fireside/onboarding.json` → explicit model path
2. `valhalla.yaml` → `node.model_path`
3. `~/.fireside/models/` → largest `.gguf` file

llama-server binary searched in:
1. `~/.fireside/bin/` (production)
2. `~/.openclaw/llama-server/` (legacy)
3. System PATH

---

## Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| "I don't have internet access" | Dashboard fell back to raw :8080 | Check Bifrost on :8765 |
| 503 "No brain installed" | `brains_state.json` missing | brain_manager fallback added |
| Tools ignored by model | `--jinja` flag missing | brain_manager always adds it |
| Pipeline tools fail | `tool_defs.py` import error | Check Python path |

---

## File Map

```
tool_defs.py                          ← UNIFIED tool registry (16 tools + role scoping)
bot/brain_manager.py                  ← llama-server lifecycle
plugins/agent_profiles/handler.py     ← /api/v1/chat (chat agent loop)
plugins/pipeline/handler.py           ← /api/v1/pipeline (per-stage agent)
plugins/browse/handler.py             ← web_search + browse implementations
dashboard/app/page.tsx                ← Chat tab → /api/v1/chat
dashboard/app/tasks/page.tsx          ← Tasks tab → /api/v1/pipeline
```

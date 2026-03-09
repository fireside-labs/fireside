# Worker Node Setup & Troubleshooting Guide

> Lessons learned from bringing Thor online. Follow this checklist when setting up any new node or debugging dispatch failures.

## Table of Contents

- [Quick Start Checklist](#quick-start-checklist)
- [Node Identity](#1-node-identity)
- [Model Provider](#2-model-provider-llama-server)
- [Gateway Configuration](#3-gateway-configuration)
- [Bifrost & TaskPoller](#4-bifrost--taskpoller)
- [Scheduled Tasks (Windows)](#5-scheduled-tasks-windows)
- [Verification](#6-verification-steps)
- [Known Bugs & Fixes](#known-bugs--fixes)

---

## Quick Start Checklist

```
[ ] config.json — this_node matches your hostname
[ ] config.json — agent.id matches your hostname
[ ] models.json — llama baseUrl points to llama-server (port 8080)
[ ] models.json — ollama baseUrl points to Ollama (port 11435, NOT 11434)
[ ] auth-profiles.json — llama key matches llama-server's --api-key
[ ] llama-server.cmd — --api-key matches what gateway sends ("local")
[ ] openclaw.json — gateway.bind = "lan" for Tailscale visibility
[ ] Firewall rules — ports 8765, 18789, 8080 inbound allowed
[ ] Environment vars — NVIDIA_API_KEY, OLLAMA_BASE, OLLAMA_EMBED_BASE
[ ] Scheduled tasks — Bifrost, Gateway, Llama Server, OpenClaw Node
[ ] git pull latest — bifrost.py accepted/ok fix & openclaw.cmd fix
```

---

## 1. Node Identity

### The Problem

Each node has a `config.json` in the workspace root. If you cloned the repo from another node, **this file still has the other node's identity**. The dispatch handler reads `this_node` to determine who to report as when completing tasks. If Thor reports as Freya, completions silently fail.

### How to Check

```powershell
# What does config.json say?
(Get-Content "$env:USERPROFILE\.openclaw\workspace\bot\config.json" | ConvertFrom-Json).this_node

# What does Bifrost report?
(Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing).Content
# Should show "node": "<your-hostname>"
```

### How to Fix

Edit `config.json`:

```json
{
    "this_node": "thor",        // ← must match your hostname
    "agent": {
        "id": "thor",           // ← must match
        "role": "build_engineer"
    }
}
```

Alternatively, create a `config.<hostname>.json` (e.g., `config.thor.json`) — Bifrost prefers node-specific configs over the shared `config.json`.

**After changing:** Restart Bifrost.

---

## 2. Model Provider (llama-server)

### API Key Matching

The OpenClaw gateway hardcodes `key: "local"` in `auth-profiles.json` and overwrites it on every restart. Your llama-server must accept this key:

```batch
REM In llama-server.cmd:
  --api-key local ^
```

**NOT** `--api-key ollama` — this causes `HTTP 401: Invalid API Key`.

### Port Separation

| Service | Port | Purpose |
|---------|------|---------|
| llama-server | 8080 | LLM inference (Q6_K model) |
| Ollama | 11435 | Embeddings only |
| Bifrost | 8765 | War Room, dispatch, gossip |
| Gateway | 18789 | OpenClaw agent sessions |

If Ollama was previously on 11434 and llama-server took that port, update:

- `models.json` → `ollama.baseUrl: "http://127.0.0.1:11435"`
- Environment: `OLLAMA_BASE=http://127.0.0.1:11435`
- Environment: `OLLAMA_EMBED_BASE=http://127.0.0.1:11435`

### Verify Model Works

```powershell
# Direct test — should return 200
$body = '{"model":"qwen3.5-35b","messages":[{"role":"user","content":"say OK"}],"max_tokens":10}'
Invoke-WebRequest "http://127.0.0.1:8080/v1/chat/completions" -Method POST -Body $body `
  -ContentType "application/json" -Headers @{Authorization="Bearer local"}
```

---

## 3. Gateway Configuration

### Binding

In `~/.openclaw/openclaw.json`, the gateway section must include `"bind": "lan"`:

```json
"gateway": {
    "mode": "local",
    "bind": "lan",
    ...
}
```

Without `bind: lan`, the gateway only listens on `127.0.0.1:18789`. With it, it listens on `0.0.0.0:18789` — required for Tailscale connections.

### Verify

```powershell
netstat -ano | findstr ":18789.*LISTENING"
# Should show 0.0.0.0:18789, NOT 127.0.0.1:18789
```

### Launch Method (Windows)

**Never** launch the gateway via PowerShell `Start-Job` — the process dies when the job is garbage collected. Use:

```powershell
Start-Process -FilePath "cmd.exe" -ArgumentList '/c "C:\Users\Jorda\AppData\Roaming\npm\openclaw.cmd" gateway' -WindowStyle Minimized
```

---

## 4. Bifrost & TaskPoller

### How Pipeline Tasks Flow

```
pipeline.py creates task → POST /war-room/task (status: open)
                                    ↓
TaskPoller._poll() scans for open tasks assigned to this node
                                    ↓
TaskPoller._process_task() → claims → POST /dispatch
                                    ↓
/dispatch runs: subprocess.run(["openclaw.cmd", "agent", ...])
                                    ↓
openclaw agent → local gateway (18789) → llama-server (8080) → response
                                    ↓
_self_report() → POST /war-room/complete → task = done
```

### Windows-Specific: `.cmd` vs `.ps1`

On Windows, `shutil.which("openclaw")` may find `openclaw.ps1` first, which is blocked by ExecutionPolicy. The fix (commit `82d35a2`) prefers `openclaw.cmd` on `win32`. **Pull latest code.**

### TaskPoller Timing

- Initial delay: **30 seconds** after Bifrost starts
- Poll interval: **60 seconds**
- First task pickup: ~90 seconds after Bifrost boot

### Verify Bifrost

```powershell
# Health check
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing

# Check tasks
$r = Invoke-WebRequest http://127.0.0.1:8765/war-room/tasks -UseBasicParsing
($r.Content | ConvertFrom-Json) | Select-Object id, title, status | Format-Table
```

---

## 5. Scheduled Tasks (Windows)

### Required Tasks

| Task Name | Command | Trigger |
|-----------|---------|---------|
| Llama Server | `cmd.exe /c C:\llama-server\llama-server.cmd` | At Logon |
| OpenClaw Gateway | `cmd.exe /c openclaw.cmd gateway` | At Logon |
| Bifrost Bot | `python.exe bifrost.py` | At Logon |
| OpenClaw Node | `node-loop.cmd` | At Logon |

### Create via PowerShell (Run as Admin)

```powershell
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "Jorda"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
  -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Gateway
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
  -Argument '/c "C:\Users\Jorda\AppData\Roaming\npm\openclaw.cmd" gateway'
Register-ScheduledTask -TaskName "OpenClaw Gateway" -Action $action `
  -Trigger $trigger -Settings $settings -User "Jorda" -RunLevel Highest -Force

# Llama Server
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
  -Argument '/c "C:\llama-server\llama-server.cmd"'
Register-ScheduledTask -TaskName "Llama Server" -Action $action `
  -Trigger $trigger -Settings $settings -User "Jorda" -RunLevel Highest -Force
```

### Environment Variables (Persistent)

```powershell
[System.Environment]::SetEnvironmentVariable("NVIDIA_API_KEY", "<your-key>", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_BASE", "http://127.0.0.1:11435", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_EMBED_BASE", "http://127.0.0.1:11435", "User")
```

---

## 6. Verification Steps

Run these in order after setup:

### Step 1: Services Running

```powershell
# llama-server
Invoke-WebRequest http://127.0.0.1:8080/v1/models -UseBasicParsing

# Ollama
Invoke-WebRequest http://127.0.0.1:11435/api/tags -UseBasicParsing

# Gateway
netstat -ano | findstr ":18789.*LISTENING"

# Bifrost
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing
```

### Step 2: Agent Works End-to-End

```powershell
cmd.exe /c "openclaw.cmd" agent -m "Reply with: AGENT OK" --json --session-id test --agent main --timeout 60
# Should return: {"status": "ok", "result": {"text": "AGENT OK"}}
```

### Step 3: Dispatch Works

```powershell
$body = '{"task_id":"verify-001","description":"Reply with: DISPATCH OK","timeout":60}'
Invoke-WebRequest http://127.0.0.1:8765/dispatch -Method POST -Body $body `
  -ContentType "application/json" -UseBasicParsing
# Should return: {"status": "accepted"}
# Wait 60s, then check if the agent completed
```

### Step 4: TaskPoller Works

```powershell
# Create a test task
$body = '{"title":"Self-test","description":"Reply with: POLLER OK","assigned_to":"<your-node>","posted_by":"test"}'
Invoke-WebRequest http://127.0.0.1:8765/war-room/task -Method POST -Body $body `
  -ContentType "application/json" -UseBasicParsing

# Wait 90s for TaskPoller to pick it up, then:
$r = Invoke-WebRequest http://127.0.0.1:8765/war-room/tasks -UseBasicParsing
($r.Content | ConvertFrom-Json) | Where-Object { $_.title -eq "Self-test" } | Select-Object status, result
# Should show: status=done
```

---

## Known Bugs & Fixes

| Bug | Symptom | Root Cause | Fix | Commit |
|-----|---------|------------|-----|--------|
| Tasks go `blocked` instantly | Pipeline tasks never execute | TaskPoller checks `status == "ok"` but dispatch returns `"accepted"` | Handle async status | `3380c3e` |
| Agent subprocess fails silently | Tasks stuck `in_progress` | `shutil.which` finds `.ps1` blocked by ExecutionPolicy | Prefer `.cmd` on Windows | `82d35a2` |
| Gateway disappears | `netstat` shows no 18789 listener | Start-Job GC kills child process | Use `cmd.exe` detached launch | Manual |
| `HTTP 401` from model | Agent returns "Invalid API Key" | `--api-key ollama` vs gateway sends `"local"` | Match api-key to `"local"` | Manual |
| Self-report rejected | Tasks complete but stay `in_progress` | `config.json this_node` = wrong node | Fix identity in config.json | Manual |
| Nodes show "disconnected" | Telegram says paired but offline | Orchestrator gateway on localhost only | `gateway.bind = lan` on orchestrator | Manual |

---

*Last updated: 2026-03-09. Based on Thor node bringup session.*

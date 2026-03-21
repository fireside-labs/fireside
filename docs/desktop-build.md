# Desktop Build Guide

> **Last updated:** 2026-03-20
> **Output:** `tauri/src-tauri/target/release/bundle/nsis/Fireside_1.0.0_x64-setup.exe`

---

## Architecture

The desktop app is **two separate processes**:

| Process | Tech | Port | Launched By |
|---------|------|------|-------------|
| **Frontend** | Tauri v2 (Rust webview) | N/A | User double-clicks `Fireside.exe` |
| **Backend** | Python FastAPI (`bifrost.py`) | 8765 | Tauri spawns `python bifrost.py` automatically |
| **LLM** | llama-server (llama.cpp) | 8080 | Bifrost's `brain_manager.py` auto-starts it |

**Key insight:** The Tauri exe does NOT bundle Python code. It runs `python bifrost.py` as a subprocess from the source directory. All Python code (plugins, middleware, etc.) runs from source. This means:
- Any code changes to `bifrost.py`, `plugins/`, `middleware/`, etc. take effect on next app restart
- Python must be installed on the user's system
- The repo must be present at the expected path

### How Tauri Launches the Backend

In `tauri/src-tauri/src/main.rs`:

1. **`spawn_backend()` (line ~760)** — runs `python bifrost.py` with `current_dir` set to the fireside directory
2. **Restart loop (line ~1320)** — if the backend crashes, Tauri restarts it (max 3 attempts)
3. **Fallback Strategy 2 (line ~1376)** — if Python isn't available, Tauri tries to start `llama-server` directly with the newest `.gguf` model
4. **Exit cleanup (line ~1454)** — kills the backend process + dashboard when the app closes

### How Bifrost Loads Plugins

`bifrost.py` → `plugin_loader.py` → scans `plugins/*/plugin.yaml` → calls `register_routes(app, config)` on each plugin. The pipeline plugin lives at `plugins/pipeline/handler.py`. If you add a new plugin, just create `plugins/your-plugin/plugin.yaml` + `handler.py` and it auto-loads.

### Chat Fallback Chain (IMPORTANT)

The dashboard chat (`page.tsx` `handleSend`) uses a **two-tier fallback**:

```
1. POST ${API_BASE}/api/v1/chat  →  bifrost:8765  →  HAS TOOLS (web search, files, etc.)
2. POST http://127.0.0.1:8080/v1/chat/completions  →  raw llama-server  →  NO TOOLS (dumb LLM)
```

> [!CAUTION]
> **If bifrost crashes on startup, chat STILL WORKS** via the llama-server fallback — but the user
> loses ALL tools, the offline banner appears, brain status shows "No Brain Equipped", and download
> buttons do nothing. This is extremely confusing because the user thinks everything is working
> (they can chat), but tools/pipelines/brain management are all dead.
>
> **Diagnosis:** If the offline banner shows but chat works, bifrost is NOT running. Check port 8765.
> Start bifrost manually: `python bifrost.py` from the repo root and watch for startup errors.

---

## Build Steps

### Prerequisites
- **Rust** — `rustup` installed with stable toolchain
- **Node.js 18+** — for dashboard build
- **Tauri CLI** — `cargo install tauri-cli` (or use `cargo tauri` directly)
- **NSIS** — Windows installer compiler (Tauri downloads this automatically on first build)

### 1. Build the Dashboard (Next.js static export)
```powershell
cd dashboard
npm run build
# Output: dashboard/out/ (static HTML/CSS/JS)
```

### 2. Build the Tauri NSIS Installer
```powershell
$env:NO_STRIP = "true"   # Required on Windows to avoid strip.exe errors
cd tauri
cargo tauri build
```

**Output location:**
```
tauri/src-tauri/target/release/bundle/nsis/Fireside_1.0.0_x64-setup.exe
```

The NSIS installer includes:
- `fireside.exe` (Tauri Rust binary — ~15MB)
- `dashboard/out/` (static frontend)
- WebView2 bootstrapper (for Windows 10 users without Edge)

It does **not** include:
- Python runtime (must be pre-installed)
- Python source code (runs from repo directory)
- GGUF model files (downloaded by brain installer)
- llama-server binary (downloaded by brain installer)

### 3. (Optional) Dev Mode
```powershell
cd tauri
cargo tauri dev
# Opens app in dev mode with hot-reload on the dashboard
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| `strip.exe` error during build | Set `$env:NO_STRIP = "true"` before building |
| Backend crashes on startup | Check `bifrost.py` can run standalone: `python bifrost.py` |
| Plugin not loading | Verify `plugins/your-plugin/plugin.yaml` exists and `handler.py` has `register_routes()` |
| "Backend exited" in Tauri logs | Tauri restarts it 3 times, then gives up. Check Python logs. |
| NSIS not found | First `cargo tauri build` downloads NSIS automatically. If it fails, install NSIS manually. |
| Dashboard shows stale UI | Rebuild dashboard first: `cd dashboard && npm run build` |
| Offline banner but chat works | Bifrost crashed — chat fell back to raw llama-server. See "Known Bug" below. |
| Port 8765 in TIME_WAIT | Kill the process holding it: `taskkill /F /PID <pid>`, then wait 60-120s for Windows to release it. |

---

## Known Bug: Zombie Bifrost (2026-03-20)

> [!WARNING]
> **Symptom:** The exe starts, chat works, but the offline banner shows and tools/brains/pipelines are broken.
>
> **Root cause:** `spawn_backend()` in main.rs runs `python bifrost.py`. Sometimes bifrost
> partially initializes (loads all 30 plugins, starts llama-server on 8080) but then fails to
> bind port 8765 or fails to mount the API routes. It ends up in a **zombie state** — holding port
> 8765 open but returning 404 on every route. The dashboard tries `/api/v1/status`, gets 404
> (`!res.ok`), and shows the offline banner. Chat still works because `page.tsx` falls back
> to `http://127.0.0.1:8080/v1/chat/completions` (raw llama-server, no tools).
>
> **Fix (manual):**
> ```powershell
> # 1. Find what's on port 8765
> netstat -ano | findstr :8765
> # 2. Kill the zombie process
> taskkill /F /PID <pid_from_above>
> # 3. Wait for TIME_WAIT to clear (60-120s on Windows)
> Start-Sleep 120
> # 4. Start bifrost fresh
> python bifrost.py
> ```
>
> **Root fix needed:** `spawn_backend()` should verify bifrost is healthy (HTTP 200 on `/api/v1/status`)
> after spawning, and kill+retry if it's in the zombie state instead of counting it as "running".

---

## Clean State (Fresh Install Testing)
```powershell
Remove-Item "$env:LOCALAPPDATA\ai.fireside.app" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.fireside" -Recurse -Force -ErrorAction SilentlyContinue
```

---

## File Map

| File | Purpose |
|------|---------|
| `tauri/src-tauri/src/main.rs` | Tauri entry point — system detection, backend spawn, IPC commands |
| `tauri/src-tauri/tauri.conf.json` | App config — window size, CSP, NSIS settings, bundle targets |
| `tauri/src-tauri/Cargo.toml` | Rust dependencies |
| `bifrost.py` | Python FastAPI backend entry point |
| `plugin_loader.py` | Scans `plugins/*/plugin.yaml` and loads each plugin |
| `config_loader.py` | Loads `valhalla.yaml` config |
| `dashboard/package.json` | Dashboard build scripts (`npm run build`) |
| `HANDOFF.md` | Quick-reference build commands and project overview |

# Sprint 13 — THOR (Tauri Commands + Config + Icons)

// turbo-all

**Your role:** Backend/Systems engineer. Rust (Tauri commands), Python, PowerShell.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_thor.md` when complete.

> [!IMPORTANT]
> **READ FIRST:** `VISION.md` + `tauri/src-tauri/tauri.conf.json` — existing Tauri v2 config.

---

## Context

There's already a Tauri v2 skeleton in `tauri/src-tauri/`. It wraps the dashboard at `localhost:3000` into a native app window. Your job is to:
1. Update the branding from "Valhalla" → "Fireside"
2. Create Rust commands that the frontend wizard calls to do the actual installation
3. Generate branded icons

---

## Your Tasks

### Task 1 — Update `tauri.conf.json`

```json
{
  "productName": "Fireside",
  "version": "1.0.0",
  "identifier": "ai.fireside.app",
  "app": {
    "title": "Fireside",
    "windows": [{ "title": "🔥 Fireside Setup" }]
  }
}
```

Update all references from "Valhalla" to "Fireside". Update the auto-updater endpoint to `https://releases.getfireside.ai/...` (placeholder is fine for now).

### Task 2 — Tauri Rust Commands

In `tauri/src-tauri/src/main.rs` (or `lib.rs`), create invoke-able commands:

```rust
#[tauri::command]
fn get_system_info() -> SystemInfo {
    // Return RAM_GB, GPU name, OS, architecture
}

#[tauri::command]
fn check_python() -> Option<String> {
    // Run `python --version`, return version string or None
}

#[tauri::command]
fn check_node() -> Option<String> {
    // Run `node --version`, return version string or None
}

#[tauri::command]
async fn install_python() -> Result<(), String> {
    // Windows: winget install Python.Python.3.12
    // macOS: brew install python@3.12
}

#[tauri::command]
async fn install_node() -> Result<(), String> {
    // Windows: winget install OpenJS.NodeJS.LTS
    // macOS: brew install node@20
}

#[tauri::command]
async fn clone_repo(fireside_dir: String) -> Result<(), String> {
    // git clone https://github.com/JordanFableFur/valhalla-mesh.git ~/.fireside
}

#[tauri::command]
async fn install_deps(fireside_dir: String) -> Result<(), String> {
    // pip install -r requirements.txt
    // cd dashboard && npm install
}

#[tauri::command]
fn write_config(config: FiresideConfig) -> Result<(), String> {
    // Write valhalla.yaml, companion_state.json, onboarding.json
    // Same output as install.sh / install.ps1
}

#[tauri::command]
async fn start_fireside(fireside_dir: String) -> Result<(), String> {
    // Start bifrost.py + npm run dev as background processes
}
```

Register all commands in the Tauri builder.

### Task 3 — App Icons

Generate icon files for all required sizes in `tauri/src-tauri/icons/`:
- `32x32.png`
- `128x128.png`
- `128x128@2x.png`
- `icon.icns` (macOS)
- `icon.ico` (Windows)

The icon should be the Fireside campfire (🔥) or a fox silhouette with fire-amber brand colors. Use the `tauri icon` CLI to generate from a single 1024x1024 source if possible.

### Task 4 — Update Cargo.toml

Ensure `tauri/src-tauri/Cargo.toml` has:
- `name = "fireside"`
- All required Tauri v2 dependencies
- The `tauri-build` in build-dependencies

### Task 5 — Drop Your Gate

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

# Sprint 13 — Fireside Setup App (Tauri Installer)

**Goal:** Turn the existing Tauri v2 skeleton into a polished, consumer-ready `Fireside-Setup.exe` (Windows) and `Fireside.dmg` (macOS) that non-technical users download from `getfireside.ai` and double-click.

**Read first:** `VISION.md` + `tauri/src-tauri/tauri.conf.json` (existing Tauri config)

> "Download. Double-click. Meet Ember."

---

## Sprint 13 Scope

### Thor (Backend + Tauri Commands)
- Update `tauri.conf.json`: rename "Valhalla" → "Fireside", update identifier
- Create Tauri commands (Rust → JS bridge) for install steps:
  - `check_python()` → returns version or null
  - `install_python()` → runs winget/brew
  - `check_node()` → returns version or null  
  - `install_node()` → runs winget/brew
  - `clone_repo()` → git clone to ~/.fireside
  - `install_deps()` → pip install + npm install
  - `write_config(name, pet, brain, agent_name, agent_style)` → writes valhalla.yaml + state
  - `start_fireside()` → launches bifrost.py + dashboard
  - `get_system_info()` → RAM, GPU, OS
- Generate app icons (fire + fox branded) for all required sizes

### Freya (Frontend — Installer UI)
- Create an `InstallerWizard.tsx` component (or adapt OnboardingWizard) that:
  - Step 1: Welcome screen with Fireside branding + "Get Started" button
  - Step 2: System check (shows RAM, GPU, auto-detects best brain)
  - Step 3: Companion selection (6 animals with art/emoji)
  - Step 4: AI person creation (name + style)
  - Step 5: Confirmation card
  - Step 6: Install progress (animated bar showing each step)
  - Step 7: Success screen — "Atlas and Ember are ready" + "Open Dashboard"
- Each step calls Tauri commands behind the scenes
- Beautiful, on-brand, fire amber palette per CREATIVE_DIRECTION.md
- Must feel like a premium app installer, not a developer tool

### Heimdall — Audit
- Tauri CSP settings are secure
- No secrets in the bundled app
- Auto-updater endpoint is HTTPS
- NSIS installer doesn't require admin if possible (currentUser mode)

### Valkyrie — UX Review
- Does the wizard feel premium?
- Is the install time acceptable?
- Does the success screen make the user excited to use the product?

---

## Build Outputs

| Platform | Output | Install Method |
|----------|--------|----------------|
| Windows | `Fireside-Setup.exe` | NSIS installer (double-click) |
| macOS | `Fireside.dmg` | Drag to Applications |
| Linux | `Fireside.AppImage` | chmod +x, run |

---

## Definition of Done
- [ ] `cargo tauri build` produces working `.exe` + `.dmg`
- [ ] User can install Fireside by double-clicking the `.exe`
- [ ] Full 7-step wizard runs inside the native window
- [ ] Config files are written correctly
- [ ] Dashboard and backend launch after wizard completes
- [ ] Icons are Fireside-branded
- [ ] All gates dropped

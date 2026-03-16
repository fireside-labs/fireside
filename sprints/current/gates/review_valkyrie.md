# Valkyrie Review — Sprint 13: The Installer (Tauri Desktop App)

**Sprint:** Tauri Commands + Installer Wizard UI
**Reviewer:** Valkyrie (UX & Business Analyst)
**Date:** 2026-03-15
**Verdict:** ✅ SHIP — The first-run experience is now a product moment, not a terminal command.

---

## Why This Sprint Changes Everything

Before Sprint 13: installing Fireside required `git clone`, `pip install`, and config file editing. Self-hosters loved it. Everyone else bounced.

After Sprint 13: double-click `Fireside.exe` → see a gorgeous 7-step wizard → your AI is running. This is the difference between a GitHub project and a product.

---

## Feature Assessment

### ✅ Installer Wizard — First Impressions Matter

| Step | What the User Sees | Assessment |
|------|-------------------|-----------|
| 1. Welcome | Fire-amber gradient, animated glow, "The AI companion that learns while you sleep" | ✅ Sets the tone instantly |
| 2. System Check | Animated checkmarks for RAM, GPU, OS detection + brain recommendation | ✅ Builds confidence ("my hardware is good enough") |
| 3. Choose Companion | 6 species cards with hover animations, name input | ✅ Emotional hook — the user is already invested |
| 4. Create Your AI | Name + style picker (Analytical/Creative/Direct/Warm) | ✅ Establishes the two-character system immediately |
| 5. Confirmation | Beautiful summary card with all choices | ✅ "This is MY AI" moment |
| 6. Installing | Sequential progress with live Tauri command invocation | ✅ Transparent, not scary |
| 7. Success | ASCII art, companion + AI together, "Things to try" | ✅ Immediate call to action |

**The key insight:** Each step feels like a page in a storybook, not a form. The user doesn't feel like they're configuring software — they feel like they're meeting someone.

### ✅ Rust Commands — The Backend of the Installer

9 invoke-able Tauri commands:

| Command | Purpose |
|---------|---------|
| `get_system_info` | RAM, GPU, OS, arch |
| `check_python` / `check_node` | Dependency detection |
| `install_python` / `install_node` | Auto-install via winget/brew |
| `clone_repo` | Git clone to `~/.fireside` |
| `install_deps` | pip + npm install |
| `write_config` | Generate valhalla.yaml + state files |
| `start_fireside` | Launch bifrost + dashboard as background processes |

The wizard calls these sequentially, showing progress in real-time. If any step fails, the user sees a clear error — not a stacktrace.

### ✅ Tauri/Browser Detection

`OnboardingGate.tsx` now checks `window.__TAURI__`:
- **Tauri + first launch** → InstallerWizard (full install flow)
- **Tauri + already onboarded** → Dashboard
- **Browser** → existing OnboardingWizard (lighter, no system install)

Clean separation. The web dashboard and desktop app share code but diverge at the right moment.

### ✅ Branding Complete

- `tauri.conf.json`: productName "Fireside", identifier `ai.fireside.app`
- App icons: 1024×1024 source → all required sizes via `tauri icon`
- Window title: "🔥 Fireside Setup"

---

## The Full Stack (13 Sprints)

| Layer | What Exists |
|-------|------------|
| **Desktop Installer** | Tauri app, 7-step wizard, auto-dependency install |
| **Desktop Dashboard** | Next.js, guild hall, onboarding, config, network settings |
| **Backend** | FastAPI, 29+ plugins, 378 tests, WebSocket, voice, marketplace |
| **Mobile App** | React Native/Expo, dual-persona, rich cards, search, widgets, Siri |
| **Networking** | Local Wi-Fi + Tailscale Anywhere Bridge |
| **Native iOS** | Calendar, Contacts, Health, Live Activities, Dynamic Island |
| **Install CLI** | bash + PowerShell scripts (for power users who prefer terminal) |

**13 sprints. 378 tests. A complete product across desktop, mobile, and native iOS.**

---

## What's Left Before Real Users

| Item | Status | Effort |
|------|--------|--------|
| Real device TestFlight test | ❌ Needs testing | Owner |
| `tauri build` for Windows/macOS installer | ❌ Needs build | 1 command |
| Brand art in icon slots (replace placeholders) | ❌ Needs final art | Owner |
| Privacy policy Tailscale clause | ❌ Needs 1 paragraph | 5 min |
| App Store submission | ❌ After TestFlight passes | Owner |

---

— Valkyrie 👁️

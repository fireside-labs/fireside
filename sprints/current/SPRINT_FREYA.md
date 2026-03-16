# Sprint 13 — FREYA (Installer Wizard UI in Tauri)

// turbo-all

**Your role:** Frontend engineer. React/Next.js (dashboard), TypeScript.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_freya.md` when complete.

> [!IMPORTANT]
> **READ FIRST:** `VISION.md` + `sprints/current/CREATIVE_DIRECTION.md` — brand palette.
> **READ ALSO:** `dashboard/components/OnboardingWizard.tsx` — existing wizard (reuse heavily).

---

## Context

The Tauri app wraps the dashboard. When there's no config (first launch), the user should see a beautiful **Installer Wizard** instead of the dashboard. Thor is building Tauri commands you can invoke from JS. Your job is the UI.

The wizard MUST feel premium. This is literally the first thing every user sees. It sells the product.

---

## Your Tasks

### Task 1 — InstallerWizard Component

Create `dashboard/components/InstallerWizard.tsx` with 7 steps:

**Step 1 — Welcome**
```
🔥
FIRESIDE

The AI companion that learns while you sleep.

[Get Started →]
```
Full-screen, centered, fire-amber gradient background. Animated fire particles or gentle glow. Premium font (Inter or Outfit from Google Fonts).

**Step 2 — System Check**
```
Checking your system...

✔ Windows 11 (Build 22621)
✔ 32GB RAM
✔ NVIDIA RTX 4090

Recommended brain: Smart & Fast (7B)
```
Auto-runs `invoke('get_system_info')`. Show animated checkmarks appearing one by one. Auto-advances after 2 seconds.

**Step 3 — Choose Your Companion**
```
Choose a companion for your journey.

  🐱 Cat       🐶 Dog       🐧 Penguin
  🦊 Fox       🦉 Owl       🐉 Dragon

[Selected: 🦊 Fox]

Name your companion: [Ember]

[Next →]
```
6 clickable cards with hover animations. Selected card glows amber. Name input below.

**Step 4 — Create Your AI**
```
Every companion has someone at the fireside.
This is the mind behind Ember — your AI.

Name: [Atlas]

What's Atlas's style?
  🎯 Analytical    🎨 Creative
  ⚡ Direct         🌿 Warm

[Next →]
```
4 style cards with descriptions and hover effects.

**Step 5 — Confirmation**
```
Ready to install.

  Owner       Jordan
  AI          Atlas (🎯)
  Companion   🦊 Ember
  Brain       Smart & Fast (7B)

[Install Fireside →]
```
Beautiful card with all choices. "Install" button is large, amber, with a subtle pulse animation.

**Step 6 — Installing**
```
Atlas and Ember are getting ready...

  ✔ Python ready
  ✔ Node.js ready
  ██████████░░░░░░░ Downloading Fireside...
  ○ Installing packages
  ○ Saving your preferences
```
Sequential progress. Each step calls the corresponding Tauri command. Animated progress bar. Show the companion emoji doing a little idle animation.

**Step 7 — Success**
```
🔥 Fireside is live.

Atlas is at the fireside.
Ember is by their side.

       🔥
       🦊

Atlas & Ember are ready for you, Jordan.

  Things to try:
  1. Say "Hello Ember!"
  2. Ask "Take me for a walk"
  3. Say "Remember: I like coffee black"

[Open Dashboard →]
```
Celebratory moment. Maybe a brief confetti or fire-spark animation. The "Open Dashboard" button transitions to the actual dashboard.

### Task 2 — Installer Gate

Update `dashboard/components/OnboardingGate.tsx` to:
- Check if running inside Tauri (`window.__TAURI__`)
- If Tauri + no onboarding.json → show InstallerWizard
- If Tauri + already onboarded → show dashboard
- If browser (not Tauri) → show existing OnboardingWizard

### Task 3 — Tauri Command Integration

Call Thor's commands from the wizard using `@tauri-apps/api/core`:

```typescript
import { invoke } from '@tauri-apps/api/core';

const sysInfo = await invoke('get_system_info');
const hasPython = await invoke('check_python');
await invoke('install_python');
await invoke('clone_repo', { firesideDir: '~/.fireside' });
await invoke('write_config', { config: { ... } });
await invoke('start_fireside', { firesideDir: '~/.fireside' });
```

### Task 4 — Responsive Design

The Tauri window is 1280×800. Design for this exact viewport. No mobile responsive needed — this is desktop only.

### Task 5 — Drop Your Gate

---

## Design Requirements
- Fire amber palette (#F59E0B, #D97706, #92400E)
- Dark background (#0F0F0F or #1A1A1A)
- Google Fonts: Inter or Outfit
- Smooth step transitions (slide or fade, 300ms)
- Each step should feel like a page in a storybook, not a form
- The companion should feel ALIVE — small animations, personality hints

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

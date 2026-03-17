---
description: how to test the dashboard without building the Tauri exe
---

# Dev-Test the Dashboard

// turbo-all

## Quick Start

1. Navigate to the dashboard directory:
```bash
cd dashboard
```

2. Install dependencies (first time only):
```bash
npm install
```

3. Start the dev server:
```bash
npm run dev
```

4. Open in browser with dev mode bypass:
```
http://localhost:3000?dev=1
```

The `?dev=1` param auto-seeds localStorage with demo data (companion "Ember" the fox, agent "Atlas", Llama brain) and skips the installer/onboarding wizard.

## Reset State

To re-test onboarding or the installer flow:
- Open browser DevTools → Application → Local Storage → Clear all `fireside_*` keys
- Or open an incognito window without `?dev=1`

## Test the Installer Flow

The installer only appears inside the Tauri desktop app (`window.__TAURI__`). Without Tauri, the browser onboarding wizard is shown instead. To test the actual installer, you need to build the Tauri exe:
```bash
cd tauri && cargo tauri dev
```

## What to Check

- **Dashboard** (`/`) — companion sprite renders, ambient fire glow visible
- **Guild Hall** (`/guildhall`) — agents render with sprites, parallax works
- **Personality** (`/soul`) — Add Skill and Add Rule buttons work
- **Settings** (`/config`) — "Connect Your Phone" card visible, no Telegram
- **Tour** — tabs never locked, NEW badges on unvisited items, pulsing recommended glow

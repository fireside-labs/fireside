# Sprint 1 — FREYA (Frontend / Mobile)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands. The entire sprint pipeline stalls if you skip this.
> See **Task 6** at the bottom for the exact content.

---

## Context

The companion system is fully built as a Next.js dashboard in `dashboard/`. Your job is to build the **React Native (Expo) mobile app** — a companion app that talks to the same backend APIs over the local network.

Reference the existing dashboard components for UX patterns:
- `dashboard/components/CompanionSim.tsx` — Care tab reference
- `dashboard/components/CompanionChat.tsx` — Chat tab reference
- `dashboard/components/InventoryGrid.tsx` — Bag tab reference
- `dashboard/components/TaskQueue.tsx` — Tasks tab reference
- `dashboard/app/companion/page.tsx` — Full page layout reference

The mobile app does NOT need to replicate the full dashboard — just the companion experience.

---

## Your Tasks

### Task 1 — Scaffold Expo Project
Create the mobile app at `mobile/` inside the repo root:

```bash
cd "C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github"
npx create-expo-app@latest mobile --template blank-typescript
cd mobile
npx expo install expo-router react-native-safe-area-context react-native-screens expo-constants expo-linking expo-status-bar
```

### Task 2 — API Client + Config Screen
Create `mobile/src/api.ts` — a typed API client that reads the home PC IP from local config:

```typescript
// mobile/src/api.ts
const BASE_URL = () => {
  // Read from AsyncStorage: 'valhalla_host' (e.g. '192.168.1.100:8765')
  // Falls back to offline mode if unavailable
};

export const companionAPI = {
  sync: () => fetch(`${BASE_URL()}/api/v1/companion/mobile/sync`),
  status: () => fetch(`${BASE_URL()}/api/v1/companion/status`),
  feed: (food: string) => fetch(`${BASE_URL()}/api/v1/companion/feed`, { method: 'POST', body: JSON.stringify({ food }) }),
  walk: () => fetch(`${BASE_URL()}/api/v1/companion/walk`, { method: 'POST' }),
  chat: (message: string) => fetch(`${BASE_URL()}/api/v1/chat`, { method: 'POST', body: JSON.stringify({ message }) }),
  queue: () => fetch(`${BASE_URL()}/api/v1/companion/queue`),
};
```

Build a **Setup Screen** (shown on first launch) where the user enters their home PC IP address. Store it in AsyncStorage. Show a "Test Connection" button that hits `/api/v1/status` and confirms `mobile_ready: true`.

### Task 3 — Main Companion Screen (4 tabs)
Build `mobile/src/app/index.tsx` with a bottom tab navigator:

**Tab 1 — 💬 Chat**
- Text input + send button
- Message bubbles (user / companion)
- Companion name + species shown at top
- If offline: show species-appropriate message — e.g. for cat: *"I need some wifi to think harder about that 😸"*

**Tab 2 — 🐾 Care**  
- Happiness bar (0-100%, color shifts green→yellow→red)
- XP progress bar + current level
- Feed buttons: 🐟 Fish, 🍬 Treat, 🥗 Salad, 🎂 Cake
- Walk button
- Species + name displayed with emoji avatar

**Tab 3 — 🎒 Bag**
- 5-column grid of inventory items
- Shows emoji, count badge for stacks, gold border for rare items
- Tap to see item detail (name, description)
- "Use" button for consumables

**Tab 4 — 📋 Tasks**
- List of queued tasks (pending / sent / completed)
- Status badges
- "Clear completed" button

### Task 4 — Offline Mode
The app must work gracefully when the home PC is unreachable:

1. On launch, try `mobile/sync`. If it fails, load last cached state from AsyncStorage.
2. Show a subtle "offline" indicator (e.g. a dimmed dot next to the companion name) — not a scary error.
3. Feed/Walk/Chat actions in offline mode should show a species-appropriate response and queue the action locally to sync when connection resumes.
4. When connection resumes (detected via background poll every 30s), sync silently, update UI, remove offline indicator.

### Task 5 — Design System
The app should feel **premium and match Valhalla's aesthetic**:
- Dark background (`#0a0a0f` or similar deep dark)
- Accent: neon green/teal (`#00ff88` or close)
- Glassmorphism cards (semi-transparent with blur)
- Inter or similar clean sans-serif font (`expo-font` or Google Fonts via `@expo-google-fonts/inter`)
- Smooth tab transitions
- Happiness bar animates when value changes

### Task 6 — Drop Your Gate
When all tabs are functional and offline mode works:
```bash
echo "# Freya Gate — Sprint 1 Frontend Complete" > sprints/current/gates/gate_freya.md
echo "Completed at $(date)" >> sprints/current/gates/gate_freya.md
echo "" >> sprints/current/gates/gate_freya.md
echo "## Completed" >> sprints/current/gates/gate_freya.md
echo "- [x] Expo project scaffolded at mobile/" >> sprints/current/gates/gate_freya.md
echo "- [x] API client with offline fallback" >> sprints/current/gates/gate_freya.md
echo "- [x] Setup screen (IP config + connection test)" >> sprints/current/gates/gate_freya.md
echo "- [x] Chat tab" >> sprints/current/gates/gate_freya.md
echo "- [x] Care tab (feed/walk/happiness)" >> sprints/current/gates/gate_freya.md
echo "- [x] Bag tab (inventory)" >> sprints/current/gates/gate_freya.md
echo "- [x] Tasks tab (queue)" >> sprints/current/gates/gate_freya.md
echo "- [x] Offline mode with graceful degradation" >> sprints/current/gates/gate_freya.md
```

---

---

## Rework Loop (if Heimdall rejects)

After you drop your gate, Heimdall audits your code. **If he finds critical issues, he will DELETE `gate_freya.md`.** If your gate file disappears:

1. Read `sprints/current/gates/audit_heimdall.md` for the list of issues
2. Fix every ❌ item
3. Re-drop your gate file (same command as Task 6)

This cycle repeats until Heimdall passes you.

---

## Notes
- Use Expo Router (file-based routing) — it's the current Expo standard.
- Target iOS first (that's where the App Store is). Android compatibility is a nice-to-have for Sprint 1.
- The backend IP is configurable — hardcode nothing. Users set it on first launch.
- DO NOT port the full dashboard. Just the companion tab experience.
- Reference the dashboard components for logic patterns, but write native mobile components from scratch (no web components in RN).

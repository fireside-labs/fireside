# Sprint 6 — FREYA (Frontend: Voice + Marketplace + OS Integration)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

> [!IMPORTANT]
> **Read `FEATURE_INVENTORY.md`** — the platform has voice, marketplace, web browsing already built.
> Read Valkyrie's Sprint 5 review: `sprints/archive/sprint_05/gates/review_valkyrie.md`

---

## Context

After 5 sprints, the mobile app is a companion viewer. Sprint 6 makes it a **platform surface** — a way to access the full power of your home AI. Voice is the demo-killer: "Talk to your home AI from your phone." Marketplace is the commerce layer. Share sheet integrates the AI into your daily phone usage.

---

## Your Tasks

### Task 1 — Voice Mode (Walkie-Talkie)
This is the highest-impact feature. "Talk to your home AI from anywhere."

```bash
cd mobile && npx expo install expo-av
```

Build a voice screen in both Pet and Tool mode. UX: **hold-to-talk walkie-talkie:**

1. **Hold button** → start recording audio (use `expo-av` Audio.Recording)
2. **Release button** → stop recording, send to `POST /api/v1/voice/transcribe`
3. **Show transcribed text** in chat bubble
4. **Send to companion chat** → get response
5. **Play response** via `POST /api/v1/voice/speak` → play audio through speaker
6. **Waveform animation** while companion is "speaking"

UX details:
- The button should be a large, prominent mic icon (60px+)
- While recording: pulsing red ring animation, "Listening..." text
- While processing: "Thinking..." with companion avatar animation
- While speaking: waveform or speaker animation with companion avatar
- Haptic feedback on press (medium impact) and release (light impact)

In Pet mode: voice button on Chat tab (alongside text input)
In Tool mode: voice button on Chat tab (more prominent, maybe primary input)

**Privacy note:** Audio goes to your home PC only. Never to a cloud. Show a small 🔒 icon to reinforce this.

### Task 2 — Marketplace Browsing
Add marketplace browsing. In Pet mode: accessible from Bag tab or a new icon. In Tool mode: accessible from Tools tab.

1. **Browse screen** — grid/list of available items (agent personalities, themes, voice packs)
2. **Search bar** — search marketplace via `GET /api/v1/marketplace/search?q=`
3. **Item detail** — tap item → detail screen with description, screenshots, price, ratings
4. **Install button** — for free items, install directly. For paid, show price + "Buy" button
5. **Category filters** — Agents, Themes, Voices, Plugins

Each item card should show:
- Icon/thumbnail
- Name + creator
- Star rating + install count
- Price (or "Free")
- Install/Installed badge

### Task 3 — iOS Share Sheet Extension
This lets users share a URL from Safari (or any app) and get a summary from their companion.

```bash
cd mobile && npx expo install expo-sharing expo-intent-launcher
```

Note: Full native share extensions in Expo require a config plugin. Create a share-receiving screen:

1. Register the app to receive shared URLs (via `app.json` intent filters)
2. When a URL is shared to the app → call `POST /api/v1/browse/summarize`
3. Show the summary in a compact card: title, summary, key points
4. Options: "Save to notes", "Share summary", "Ask companion about this"

If native share sheet extension is too complex for Expo, alternative: add a "Paste URL" button in the Tools tab that accepts a URL and returns a summary. Simpler, still useful.

### Task 4 — Home Screen Widget
Show companion mood on the home screen without opening the app.

```bash
cd mobile && npx expo install react-native-widget-extension
```

Note: Expo widget support is experimental. If the widget library isn't stable enough, create a simulated widget screen or skip this task and document why.

Widget should show:
- Companion avatar (mood expression)
- Happiness bar
- Last activity ("Fed 2h ago", "Adventure available!")
- Tap → opens app to Care tab

### Task 5 — WebSocket Real-Time Sync
Replace the pull-to-refresh polling with WebSocket for live updates:

1. On app launch, connect to `WS /api/v1/companion/ws`
2. Listen for events: `companion_state_update`, `task_completed`, `chat_message`
3. Update local state immediately when events arrive
4. Show a subtle live indicator (green dot) when WebSocket is connected
5. Fall back to polling if WebSocket fails (keep existing pull-to-refresh as backup)
6. Reconnect automatically on disconnect (exponential backoff)

### Task 6 — Drop Your Gate
Create `sprints/current/gates/gate_freya.md` using write_to_file:

```markdown
# Freya Gate — Sprint 6 Frontend Complete
Sprint 6 tasks completed.

## Completed
- [x] Voice mode (walkie-talkie, hold-to-talk)
- [x] Marketplace browsing (browse, search, detail, install)
- [x] Share sheet / URL summary (or paste-URL alternative)
- [x] Home screen widget (or documented why skipped)
- [x] WebSocket real-time sync
```

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
- Read `sprints/current/gates/audit_heimdall.md` if gate is deleted

---

## Notes
- **Voice is the #1 priority.** This is what makes demos jaw-dropping. "Watch, I'll talk to my home AI from my phone."
- Audio data must NEVER leave the local network. Show the 🔒 privacy indicator.
- If widget or native share sheet is too complex for Expo, document the limitation and build the simpler alternative. Don't block the sprint on platform limitations.
- WebSocket is infrastructure — it makes everything feel instant. Worth the investment.
- Build ON TOP of Sprint 5 code.

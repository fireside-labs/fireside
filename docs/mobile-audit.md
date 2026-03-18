# 📱 Mobile App — Feature Audit & Desktop→Mobile Flow

## Current State

The mobile app is an **Expo/React Native** app with **expo-router** file-based routing. It's already quite comprehensive — ~25 components across 7 tab screens.

### Architecture
- **Framework**: Expo SDK with expo-router (file-based)
- **Pairing**: QR code scan or manual IP entry → stores host in AsyncStorage
- **Connectivity**: Local Wi-Fi + Tailscale "Anywhere Bridge" for remote access
- **Offline**: Queues actions locally, replays when reconnected
- **Backend**: Hits `http://{host}:9099/api/v1/...` (40+ endpoints)
- **WebSocket**: `useWebSocket.ts` for live events from desktop

### Dual Modes
| Mode | Tab Bar | Target User |
|------|---------|-------------|
| **Companion** 🐾 | Home · Chat · Brain · Skills · Soul | Personal/fun — feed, walk, daily gifts |
| **Executive** 💼 | Home · Chat · Tools · Tasks · Brain · Soul | Productivity — tasks, research, pipelines |

### Tab Screens

| Tab | File | Lines | What It Does |
|-----|------|-------|-------------|
| 🏠 **Home** | `care.tsx` | 888 | Campfire scene, companion mood/XP/hunger, morning briefing, daily gift, achievement toasts |
| 💬 **Chat** | `chat.tsx` | 446 | Full chat with guardian moderation, voice mode (Whisper STT + Kokoro TTS), action cards, offline responses, agent relay |
| 🔧 **Tools** | `tools.tsx` | 640 | URL summarizer, translation (NLLB-200), teach facts, voice transcribe, cross-context search |
| 🧠 **Brain** | `brain.tsx` | 435 | Active model info, GPU stats, model switching, memory health, mesh node count |
| ⚡ **Skills** | `skills.tsx` | 370 | RPG skill cards (toggle on/off), XP costs, level progression |
| 📋 **Tasks** | `tasks.tsx` | 540 | Queue tasks from phone, view pending/completed, companion assigns work to desktop |
| 🎭 **Soul** | `personality.tsx` | 380 | Edit personality traits, voice style, greeting, bio — the companion's "soul file" |

### Key Components

| Component | What |
|-----------|------|
| `QRPair.tsx` | Camera QR scanner + manual IP fallback |
| `VoiceMode.tsx` | Hold-to-talk → Whisper transcribe → AI reply → Kokoro TTS playback |
| `GuardianModal.tsx` | Intercepts potentially harmful messages, suggests rewrites |
| `ProactiveGuardian.tsx` | Background check-ins (late night warnings, etc.) |
| `ActionCard.tsx` | Rich cards for pipeline status, browse results, translations, calendar |
| `CampfireScene.tsx` | Animated campfire with companion, embers, mood-reactive glow |
| `DailyGift.tsx` | Daily login reward with items |
| `AchievementBadge.tsx` | RPG achievement unlock toasts |
| `MorningBriefing.tsx` | Morning summary of overnight activity |
| `WeeklySummary.tsx` | Weekly stats digest |
| `SearchAll.tsx` | Cross-context search across memories, chats, tasks |

---

## The Desktop → Mobile Flow

```
┌──────────────────────────────────────────────────────┐
│  DESKTOP (Dashboard)                                  │
│                                                       │
│  1. User creates companion (name + species)           │
│  2. Dashboard → Settings → "Pair Phone"               │
│  3. Shows QR code with {host, token}                  │
│                                                       │
│  ┌─────────┐                                          │
│  │ QR Code │◄──── Contains: host IP + pairing token   │
│  └─────────┘                                          │
└──────────────────┬───────────────────────────────────┘
                   │ User scans QR
                   ▼
┌──────────────────────────────────────────────────────┐
│  MOBILE (Expo App)                                    │
│                                                       │
│  4. Phone scans QR → stores host + token              │
│  5. testConnection() → /api/v1/status ✓               │
│  6. Bridge setup? → Tailscale IP stored               │
│  7. Mode select: Companion or Executive               │
│  8. Permissions: mic, notifications, camera            │
│  9. sync() → pulls companion state, personality,      │
│     pending tasks, inventory, platform stats           │
│                                                       │
│  NOW CONNECTED — same companion on both devices       │
│  Chat on phone → relayed to AI on desktop → responds  │
└──────────────────────────────────────────────────────┘
```

---

## What's Already Working ✅

- [x] QR pairing + manual IP
- [x] Tailscale anywhere bridge
- [x] Full chat with guardian moderation
- [x] Voice mode (STT + TTS)
- [x] Companion care (feed, walk, daily gifts)
- [x] Task queue (create from phone, execute on desktop)
- [x] Brain management (model switching, GPU stats)
- [x] Skill management (RPG toggle cards)
- [x] Personality/soul editing
- [x] Push notification registration
- [x] Offline mode with action queuing
- [x] Translation (200 languages via NLLB-200)
- [x] URL summarization
- [x] Cross-context search
- [x] Achievement system
- [x] Morning briefing + weekly summary
- [x] Campfire scene with animated companion

## What Could Be Enhanced 🔧

### 1. Pipeline Status on Mobile
The `ActionCard` already handles `pipeline_status` and `pipeline_complete` action types, but there's **no dedicated pipeline view** on mobile. Users can see pipeline updates in chat but can't browse or monitor active pipelines like on desktop.

### 2. Agent Feed (Live Transcript)
The mobile has WebSocket support (`useWebSocket.ts`) but doesn't display the agent feed we just built on desktop. Users can't see agent-to-agent communication from their phone.

### 3. Companion Creation on Mobile
Currently, the companion is created on the desktop (`/api/v1/companion/adopt`). The mobile onboarding **assumes a companion already exists**. If a user downloads the app first, there's no way to create/adopt the companion from mobile.

### 4. Desktop Notifications on Mobile
When the desktop pipeline hits a milestone (PASS, escalation, debate), the phone doesn't get push notifications yet. The `registerPush` endpoint exists but the backend doesn't seem to fire push events for pipeline stages.

### 5. Intervene from Mobile
The "Intervene — Jump In" feature we built on desktop (inject instructions into a running pipeline) isn't accessible from mobile.

### 6. Onboarding Flow Gap
The current flow is: Welcome → Connect → Bridge → Mode → Permissions → Done. There's no "Create your companion" step. If they haven't created one on desktop yet, the app lands on an empty state.

---

## Recommended Flow Enhancement

### Ideal User Journey

```
1. DESKTOP: User discovers Fireside, runs installer
2. DESKTOP: Dashboard opens → "Create your companion"
   - Pick species, name, personality
   - Companion appears on dashboard with campfire
   
3. MOBILE: User downloads app from App Store
4. MOBILE: Onboarding starts:
   Welcome → "Connect to your PC" → QR scan → ✅ Connected
   → Companion greeting: "Hey! I'm [name]! 🔥"
   → Mode: Companion or Executive
   → Permissions → Done
   
5. NOW BOTH CONNECTED:
   - Message companion from phone → AI responds via desktop
   - See pipeline status in chat as action cards
   - Get push notifications for pipeline milestones
   - Intervene in pipelines from phone
   - Manage skills/personality from either platform
```

### Priority Improvements

| Priority | Enhancement | Effort | Impact |
|----------|------------|--------|--------|
| 🔴 P0 | Add companion creation to mobile onboarding | Medium | Unblocks users who start on mobile |
| 🟡 P1 | Pipeline mini-view on Tasks tab | Medium | See active pipelines + status from phone |
| 🟡 P1 | Push notifications for pipeline events | Low | Know when pipeline completes without checking |
| 🟢 P2 | Agent feed on mobile (WebSocket → chat) | High | Full transparency, but dense for mobile |
| 🟢 P2 | Intervene from mobile | Low | Send instructions to running pipeline |
| 🟢 P3 | Companion state sync animation | Medium | Visual "connection" moment during pairing |

# Fireside / Valhalla — Complete Feature Inventory

> [!IMPORTANT]
> **ALL AGENTS:** Read this file to understand the FULL platform.
> Updated after Sprint 5 — see what's shipped vs what's still missing.

---

## What the Mobile App Has (Sprints 1-5)

| Feature | Sprint |
|---|---|
| Chat, Care (feed/walk), Bag, Tasks, Offline mode | Sprint 1 |
| Onboarding, avatars, haptics, pull-to-refresh, chat persistence, adoption | Sprint 2 |
| Push notifications (4 triggers), animated avatars, sound effects, icon/splash, privacy policy | Sprint 3 |
| Adventures (8 types), daily gifts, message guardian, EAS build config, feature flags | Sprint 4 |
| **Mode toggle (Pet ↔ Tool)**, translation (200 langs), morning briefing, TeachMe, platform bridge card, proactive guardian | Sprint 5 |

---

## What's Still NOT in Mobile

> [!WARNING]
> These are PLATFORM-LEVEL gaps, not just feature ports.

| Feature | Backend | Dashboard | Mobile | Sprint 6? |
|---|---|---|---|---|
| **Voice** (Whisper STT + Kokoro TTS) | `voice/` plugin | `VoiceSettings.tsx` | ❌ | ✅ Sprint 6 |
| **Marketplace** (browse, install, sell) | `marketplace/` plugin | `SellerDashboard.tsx` | ❌ | ✅ Sprint 6 |
| **Web browsing** (summarize pages) | `browse/parser.py` | via handler | ❌ | ✅ Sprint 6 |
| **Real-time sync** (WebSocket) | Not yet | Not yet | ❌ (polling) | ✅ Sprint 6 |
| **OS integration** (share sheet, widget) | N/A | N/A | ❌ | ✅ Sprint 6 |
| **Payments** (Stripe / IAP) | `payments/` plugin | `PurchaseHistory.tsx` | ❌ | Sprint 7+ |
| **Agent profiles** (RPG cards, XP) | `agent-profiles/` | `AgentProfile.tsx` | ❌ | Sprint 7+ |
| **Pipeline monitoring** | `pipeline/` | `PipelineCard.tsx` | ❌ | Sprint 7+ |
| **Guild Hall** (animated social) | N/A | `GuildHall.tsx` | ❌ | Sprint 8+ |

---

## Full Backend Plugin List (29 plugins)

| Plugin | Purpose |
|---|---|
| `hypotheses` | Bayesian belief system |
| `predictions` | Free energy prediction before every /ask |
| `self-model` | Default mode network — self-assessment injected into prompts |
| `working-memory` | Top 10 high-importance memories in every prompt |
| `belief-shadows` | Theory of mind — model what each peer believes |
| `crucible` | Adversarial stress-testing of procedures |
| `philosopher-stone` | Knowledge transmutation engine |
| `pipeline` | Multi-stage task processing |
| `socratic` | Guided discovery / Socratic dialogue |
| `event-bus` | Pub/sub cortical broadcast |
| `model-switch` | Runtime model swapping |
| `model-router` | Intelligent routing between models |
| `watchdog` | Peer health monitoring |
| `hydra` | Node failure absorption |
| `personality` | Behavioral evolution (weekly P&L) |
| `agent-profiles` | RPG profiles, XP, levels, achievements |
| `brain-installer` | Model download orchestration |
| `companion` | Tamagotchi engine, guardian, relay, queue, nllb |
| `consumer-api` | Consumer-facing API layer |
| `telegram` | Chat + notifications + 5 commands |
| `voice` | Whisper STT + Kokoro TTS |
| `alerts` | Proactive alert engine |
| `marketplace` | Plugin/agent browsing and install |
| `payments` | Stripe integration |
| `browse` | Web navigation (tree-based parser) |
| `task-persistence` | Task state across restarts |
| `adaptive-thinking` | Dynamic reasoning mode |
| `context-compactor` | Context window optimization |

---

## Dashboard (60 components, 16 pages)

| Route | What |
|---|---|
| `/` | Main chat interface |
| `/companion` | Companion hub (Chat/Care/Bag/Tasks) |
| `/agents` | Agent profiles and management |
| `/brains` | Brain picker and installer |
| `/config` | Settings (SettingsForm, VoiceSettings, TelegramSetup) |
| `/crucible` | Adversarial test results |
| `/debate` | Agent debate transcripts |
| `/guildhall` | Animated 2D guild hall (5 themes) |
| `/landing` | Landing/marketing page |
| `/learning` | Learning/wisdom viewer |
| `/marketplace` | Plugin marketplace |
| `/nodes` | Mesh node management |
| `/pipeline` | Task pipeline view |
| `/plugins` | Installed plugins |
| `/soul` | Soul editor |
| `/store` | Store (themes, avatars, voice packs) |
| `/warroom` | War room (hypotheses, events, predictions) |

# Fireside / Valhalla — Complete Feature Inventory

> [!IMPORTANT]
> **ALL AGENTS:** Read this file to understand the FULL platform.
> The mobile app (Sprints 1-3) only surfaces a fraction of these features.
> Many backend APIs and dashboard components exist but are NOT yet in the mobile app.

---

## What the Mobile App Currently Has (Sprints 1-3)

| Feature | Mobile Status |
|---|---|
| Chat with companion | ✅ Shipped Sprint 1 |
| Care (feed/walk/happiness/XP) | ✅ Shipped Sprint 1 |
| Inventory grid (Bag tab) | ✅ Shipped Sprint 1 |
| Task queue (phone → home PC) | ✅ Shipped Sprint 1 |
| Offline mode + action queueing | ✅ Shipped Sprint 1 |
| Onboarding carousel | ✅ Shipped Sprint 2 |
| Companion avatar images | ✅ Shipped Sprint 2 |
| Pull-to-refresh | ✅ Shipped Sprint 2 |
| Haptic feedback | ✅ Shipped Sprint 2 |
| Chat history persistence | ✅ Shipped Sprint 2 |
| Mobile companion adoption | ✅ Shipped Sprint 2 |
| Animated avatar expressions | ✅ Shipped Sprint 3 |
| Push notifications (4 triggers) | ✅ Shipped Sprint 3 |
| Sound effects | ✅ Shipped Sprint 3 |
| App icon + splash | ✅ Shipped Sprint 3 |
| Privacy policy | ✅ Shipped Sprint 3 |

---

## What the Desktop Has But Mobile DOESN'T (Yet)

> [!WARNING]
> These features have working backend APIs AND dashboard components. They just haven't been ported to the mobile app.

| Feature | Backend | Dashboard Component | Mobile |
|---|---|---|---|
| **Adventures** (8 types: riddle, treasure, merchant, forage, lost_pet, weather, storyteller, challenge) | `adventure_guard.py` | `AdventureCard.tsx` (308 lines) | ❌ NOT IN MOBILE |
| **Daily Gifts** (species-specific poems, items, facts, advice, compliments) | `sim.py` | `DailyGift.tsx` | ❌ NOT IN MOBILE |
| **Teach Me** (user teaches companion facts, personality-flavored confirmations) | `handler.py` | `TeachMe.tsx` | ❌ NOT IN MOBILE |
| **Morning Briefing** (daily summary from companion) | `handler.py` | `MorningBriefing.tsx` | ❌ NOT IN MOBILE |
| **Message Guardian** (sentiment, regret detection, drunk text filter, PII filter, softer rewrites) | `guardian.py` (284 lines) | integrated in chat | ❌ NOT IN MOBILE |
| **Translation** (200 languages, offline, NLLB-200) | `nllb.py` (274 lines) | via handler | ❌ NOT IN MOBILE |
| **Marketplace** (browse, install, sell plugins/agents) | `marketplace/` plugin | `SellerDashboard.tsx` | ❌ NOT IN MOBILE |
| **Voice** (Whisper STT + Kokoro TTS) | `voice/` plugin | `VoiceSettings.tsx` | ❌ NOT IN MOBILE |

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

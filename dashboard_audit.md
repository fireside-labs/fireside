# Dashboard Wiring Audit

> Every page, what's mock, what's real, and what to fix first.

---

## The Problem

`api.ts` has **20 MOCK_ constants** totaling ~500 lines of fake data. Every API function falls back to mock data when the backend is unreachable — which is always for a fresh install, since `bifrost.py` doesn't implement half these endpoints yet.

---

## Page-by-Page Status

### ✅ Wired (works with real data)
| Page | What's Real |
|------|-------------|
| `/` (Chat) | Chat input → `POST /api/v1/chat` on port 8765, companion widget from localStorage |
| `/companion` | Pet state from localStorage, care/chat/bag/tasks tabs all functional |
| `/soul` | Reads/writes soul files via API (falls back to mock) |
| `/config` | Reads/writes `valhalla.yaml` via API (falls back to mock) |

### ⚠️ Partially Wired (API exists, falls back to mock)
| Page | What Works | What's Mock |
|------|-----------|-------------|
| `/nodes` | Calls `getNodes()` → hits `/api/v1/nodes` | Falls back to 5 hardcoded nodes: odin, thor, freya, heimdall, hermes |
| `/plugins` | Calls `getPlugins()` → hits `/api/v1/plugins` | Falls back to 2 mock plugins |
| `/brains` | Brain picker exists | No real model download/status API |

### 🔴 Fully Mock (hardcoded data, no backend)
| Page | Mock Source | What You See |
|------|------------|-------------|
| `/guildhall` | Hardcoded agents in `GuildHall.tsx` | 5 agents, fixed activities, theme picker works |
| `/warroom` | `MOCK_HYPOTHESES`, `MOCK_PREDICTIONS`, `MOCK_EVENTS` | All fake data from api.ts |
| `/pipeline` | `MOCK_PIPELINES` (3 pipelines) | Fake "Add JWT auth" pipeline |
| `/pipeline/[id]` | Same mock | Fake iteration history |
| `/crucible` | `MOCK_CRUCIBLE` (12 procedures) | All fake test results |
| `/debate` | `MOCK_DEBATES` | Fake Socratic debate |
| `/learning` | `MOCK_PREDICTIONS`, `MOCK_SELF_MODEL` | Fake prediction scores |
| `/models` | `MOCK_MODEL_ROUTER` | Fake token counts |
| `/marketplace` | `MOCK_AGENTS` | Fake marketplace listings |
| `/marketplace/[id]` | Same mock | Fake agent details |
| `/store` | `MOCK_MARKETPLACE` (8 plugins) | Fake store listings |
| `/store/sell` | Seller dashboard | No backend |
| `/landing` | Static | N/A — just marketing |

### 🟡 Components with Inline Mocks
| Component | Mock Data |
|-----------|-----------|
| `WeeklyCard.tsx` | `MOCK_INSIGHTS` — "Learned 12 new things" |
| `InventoryGrid.tsx` | `MOCK_INVENTORY` — fake items |
| `TaskQueue.tsx` | `MOCK_TASKS` — fake queued tasks |
| `AdventureCard.tsx` | `MOCK_ADVENTURES` — per-species adventures |
| `PurchaseHistory.tsx` | `MOCK_PURCHASES` — empty array |

---

## Hardcoded Values (non-mock)

| Location | Hardcoded | Should Be |
|----------|-----------|-----------|
| `Sidebar.tsx` | ~~"odin"~~ ✅ Fixed → dynamic from localStorage | ✅ Done |
| `nodes/page.tsx` | `FRIENDLY_NAMES: { odin: "Your MacBook", thor: "Office PC" }` | Dynamic from config/node registration |
| `api.ts` | `API_BASE = localhost:8766` | Should match install port (8765) or be configurable |
| `page.tsx` | ~~`localhost:8337`~~ ✅ Fixed → 8765 | ✅ Done |

---

## Your Specific Questions

### "Where can I see my nodes?"
**→ `/nodes` page** (sidebar: "Connected Devices"). It calls `getNodes()` but falls back to mock data showing odin/thor/freya/heimdall/hermes. The "Add another device" button exists but does nothing.

### "Making new nodes, assigning stats?"
**→ Not built.** No endpoint for `POST /api/v1/nodes` (register a new node). The install wizard creates a node config in `valhalla.yaml` but there's no API to register/discover nodes dynamically.

### "Where can I see nodes working in a space station or vikings theme?"
**→ `/guildhall` page** (sidebar: "Guild Hall"). Theme picker works (Valhalla, Office, Space, Cozy, Dungeon). Agents are hardcoded in `GuildHall.tsx` with fixed activities — not wired to real agent status.

---

## Priority Fix Plan

### P0 — Demo Blockers (do first)
1. **Fix `api.ts` port** — `API_BASE` is `8766`, install starts backend on `8765`
2. **Guild Hall → wire to real node status** — when a node is actually online, show it as "researching" not a hardcoded activity
3. **Remove `FRIENDLY_NAMES` from nodes page** — use actual node names from config, not "Your MacBook"

### P1 — First Impression (homepage + companion)
4. **Wire WeeklyCard to real data** or remove it (it's not on homepage anymore but still imported)
5. **Wire TaskQueue to real backend tasks** if pipeline is running
6. **Wire InventoryGrid to localStorage** instead of mock

### P2 — Power Features (when backend catches up)
7. **Node registration API** — `POST /api/v1/nodes` to add new devices
8. **Guild Hall real status** — WebSocket for live activity updates
9. **Pipeline wiring** — connect to real task execution
10. **Marketplace wiring** — connect to real plugin/agent store

---

*The mock fallback pattern in `api.ts` is actually good architecture — it means the dashboard always renders even when the backend is down. The fix isn't removing mocks, it's making the backend implement the endpoints so the mocks stop being needed.*

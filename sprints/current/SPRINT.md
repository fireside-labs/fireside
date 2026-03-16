# Sprint 20 — "Less is More"

> **Goal:** Cut sidebar from 10 tabs to 6. Reduce overwhelm. Power user features move to Settings sub-tabs, not deleted. Companion folds into Guild Hall.
> **Timeline:** 1 day
> **Source:** User testing — "I'm overwhelmed. Getting rid of useless features matters more than adding new ones."

---

## Sidebar: Before → After

| Before (10 tabs) | After (6 tabs) | What happens to cut items |
|---|---|---|
| 💬 Chat | ✅ **KEEP** | Core product |
| 🧠 Personality | ✅ **KEEP** | Configure AI |
| 📱 Connected Devices | ❌ CUT | → Settings > Advanced > Devices |
| 🐾 Companion | ❌ CUT | → Mascot lives in Guild Hall |
| 📋 Task Builder | ❌ CUT | → Settings > Advanced > Tasks |
| 📊 How It's Learning | ❌ CUT | → Dashboard widget + Settings > Advanced > Learning |
| 🏰 Guild Hall | ✅ **KEEP** | Money shot |
| ⚙ Settings | ✅ **KEEP** | Now includes Advanced sub-tabs |
| 🧠 Brains | ✅ **KEEP** | Model management |
| 🏪 Store | ✅ **KEEP** | Revenue |

---

## 🎨 Freya (UI)

### F1: Reduce Sidebar to 6 items
- Update `Sidebar.tsx` NAV_SECTIONS to only show:
  - **Your AI:** Chat, Personality
  - **World:** Guild Hall
  - **System:** Brains, Store, Settings
- Remove Companion, Connected Devices, Task Builder, Learning from sidebar

### F2: Settings gets "Advanced" sub-tabs
- Settings page gets tab strip: General | Brains | Advanced
- Advanced sub-tab contains:
  - Connected Devices (was `/nodes`)
  - Task Builder (was `/pipeline`)
  - Learning Stats (was `/learning`)
- Power users find everything. Grandma never sees it.

### F3: Fold companion into Guild Hall
- Remove `/companion` page from sidebar
- Companion is always visible in Guild Hall (mascot)
- Companion name shown in Guild Hall tooltip
- Companion selection only happens during onboarding

### F4: Dashboard "How It's Learning" widget
- Small card on main dashboard showing:
  - "47 things learned" + last learned topic
  - Links to Settings > Advanced > Learning for details
- Replaces the dedicated `/learning` page for casual users

---

## 🔨 Thor (Backend)

### T1: No backend changes needed
- All existing API endpoints stay — just frontend routing changes
- Settings page fetches from same endpoints as the removed pages

---

## 🛡️ Heimdall (Audit)

### H1: Verify removed routes don't 404
- `/nodes`, `/pipeline`, `/learning`, `/companion` should redirect to Settings > Advanced
- No dead links in the app

### H2: Verify power user access
- Every feature that was cut from sidebar is still accessible via Settings > Advanced

---

## ✅ Valkyrie (QA)

### V1: Fresh user experience
- Install → onboard → see 6 clean tabs
- Not overwhelmed — clear path: Chat, Guild Hall, Brains
- Settings > Advanced contains everything for power users
- Companion visible in Guild Hall, not a separate page

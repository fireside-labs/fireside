# Sprint 10 — FREYA (Frontend: Two Characters in Dashboard + Mobile)

// turbo-all

**Your role:** Frontend engineer. React/Next.js (dashboard), React Native/Expo (mobile).
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** Create `sprints/current/gates/gate_freya.md` when complete.

> [!IMPORTANT]
> **READ FIRST:** `VISION.md` — the product vision. This sprint brings both characters to life.
> **READ ALSO:** `sprints/current/CREATIVE_DIRECTION.md` — brand palette.

---

## Context

The product now has TWO characters:
1. **AI Agent** (person) — lives at home, visible in the guild hall on the dashboard
2. **Companion** (animal) — goes with the user on mobile

This sprint makes both characters visible and connected across desktop and mobile.

---

## Your Tasks

### Task 1 — Dashboard: Guild Hall Reads Real Data

Replace the mocked `AGENTS` array in `dashboard/components/GuildHall.tsx` with real data from `GET /api/v1/guildhall/agents`.

1. Fetch agents on mount using `useSWR` or `useEffect`
2. Map each agent to the existing `GuildHallAgent` component
3. For the AI agent: generate an avatar config from their `style`:
   - Analytical → structured look (glasses, neat hair)
   - Creative → artistic look (colorful, flowing)
   - Direct → military/clean look
   - Warm → soft, approachable
4. For the companion: show the species emoji/sprite near the fireplace
5. Position the AI agent at the activity zone based on their `activity`
6. Show the companion curled up near the fire (idle) or alert (if chatting/tasks active)
7. Fallback to existing mocked data if API is unavailable

### Task 2 — Dashboard: Onboarding Wizard Two-Character Flow

Update `dashboard/components/OnboardingWizard.tsx` to match the new install flow:

1. Step 1: Your name (existing)
2. Step 2: Choose companion species + name (existing, reorder if needed)
3. Step 3: Choose brain size (existing)
4. **Step 4 (NEW): Create your AI**
   - "Every companion has someone at the fireside."
   - Name input (default: "Atlas")
   - Style picker: Analytical / Creative / Direct / Warm (4 cards with emoji + description)
5. Step 5: Confirmation with both characters shown
6. Save both to onboarding config

### Task 3 — Mobile: Companion References AI by Name

Update the mobile companion chat to reference the AI agent by name:

1. Fetch `GET /api/v1/agent/profile` on app launch, store in context
2. When the companion relays a task home or gets a response from the big model, prepend flavor text:
   - "Let me check with Atlas..." (when sending to PC)
   - "Atlas says..." (when showing response from PC brain)
   - "I can handle this one myself" (when handling locally/cached)
3. In offline mode: "Atlas is resting right now, but I'll remember this for when we're home."
4. Show both names in the agent profile card:
   ```
   ┌──────────────────┐
   │  🦊 Ember         │ ← Your companion
   │  Level 4 · Fox    │
   │                    │
   │  🏠 Atlas          │ ← Your AI at home
   │  Analytical · 🟢   │
   └──────────────────┘
   ```

### Task 4 — Mobile: Settings Screen Update

Add an "AI Agent" section to the settings screen:

- **AI Name:** Atlas
- **Style:** Analytical
- **Status:** 🟢 Online / 🔴 Offline
- **Uptime:** 4h 22m (from agent profile API)

### Task 5 — Drop Your Gate

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

---

## Notes
- The guild hall is the "wow" moment on desktop. Make sure the API connection works smoothly.
- The "Let me check with Atlas..." flavor text is the emotional bridge between phone and PC.
- Don't break existing functionality — this is additive, not a rewrite.
- Follow CREATIVE_DIRECTION.md for all visual decisions.

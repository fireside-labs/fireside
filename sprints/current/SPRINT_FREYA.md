# Sprint 8 — FREYA (Frontend: Orchestration UI + Settings + Onboarding v2)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).

> [!IMPORTANT]
> **Read `FEATURE_INVENTORY.md`** — the platform has 29 plugins and a full mesh of agents.
> The mobile app's job is to make that mesh accessible, not to replicate what it does.

---

## Context

The companion is an orchestrator, not an email client. Sprint 8 makes the full mesh accessible from your phone. The user says "research competitor pricing" and the companion routes it to the browse agent. They say "what did we talk about last week?" and the companion searches across all memories, conversations, and predictions.

This sprint also adds the settings screen, a proper onboarding flow with hosted mode, and renames "Tool Mode" to "Executive Mode."

---

## Your Tasks

### Task 1 — Smart Command Bar
Replace or augment the chat input with an intelligent command bar:

When the user types a message that looks like a task/command (not just conversation), show a routing indicator:

1. As user types, call `POST /api/v1/companion/route` (debounced, 500ms)
2. If the router identifies a specific plugin, show a subtle chip above the input:
   - 🌐 "Browse agent" for research requests
   - 🧠 "Memory" for recall requests
   - 📋 "Pipeline" for multi-step tasks
   - 🐾 "Companion" for care/chat
3. User can tap the chip to confirm routing, or just send normally (auto-routes)
4. When a task is routed, show a task card in the chat feed:
   - "🌐 Research queued: 'competitor pricing analysis'"
   - Progress indicator if available
   - Result appears as a rich card when complete

The key UX principle: **the user just talks naturally, the companion figures out HOW to do it.**

### Task 2 — Agent Activity Feed
Build `mobile/src/AgentActivity.tsx` — shows what the mesh is doing right now.

Show on the "What's Happening at Home" card (from Sprint 5) or as a new section:

1. Call `GET /api/v1/mesh/status` on mount + via WebSocket updates
2. Show each active agent with:
   - Name + status (online/offline/busy)
   - Current task (if any) with progress bar
   - Last activity timestamp
3. Show queued tasks with estimated completion
4. Show loaded models (clickable → "What's this?" tooltip)

This replaces the simple platform stats card with a **live mesh dashboard** on your phone.

### Task 3 — Cross-Context Search
Build `mobile/src/SearchAll.tsx` — "What do you know about X?"

Accessible from a search icon in the chat header or Tools tab:

1. Search input with placeholder: "Search across all your AI's memory..."
2. Call `POST /api/v1/companion/query` with the search term
3. Show results grouped by source:
   - 🧠 Memories
   - 💬 Conversations
   - 📚 Taught facts
   - 🔮 Predictions
4. Each result shows: source icon, content snippet, relevance score, date
5. Tap a result → expand to full context

This is the "holy shit" feature for executives — "What do you know about Sarah's project?" and the AI searches its ENTIRE brain.

### Task 4 — Settings Screen
Build `mobile/app/settings.tsx` — accessible from a gear icon:

1. **Mode switch** — "Companion Mode" ↔ "Executive Mode"
2. **Connection** — Status indicator, host IP, re-pair button, connection mode (self-hosted/hosted)
3. **Companion** — Name display, species, level (read-only)
4. **Voice** — Enable/disable voice mode
5. **Notifications** — Category toggles (companion care, tasks, guardian, mesh activity)
6. **Privacy** — Where data lives: "All on your PC" (self-hosted) or "Your private cloud instance" (hosted)
7. **About** — Version, build number, "Powered by Fireside Mesh"

Mode switch should also be accessible from the home screen (header toggle or long-press avatar).

### Task 5 — Onboarding v2
Rebuild the onboarding flow with two paths:

**Screen 1 — Welcome**
"Your private AI — powered by you."

**Screen 2 — How do you connect?**
- 🏠 **"I have Fireside on my PC"** → QR code scan (from Sprint 7) or manual IP
- ☁️ **"Set up for me"** → email signup → "Launching your private AI..." → waits for container (placeholder for now — show waitlist if not ready)

**Screen 3 — Choose your experience**
- 🐾 **"Companion"** — "A friendly AI that grows with you. Adventures, gifts, and personality."
- 💼 **"Executive"** — "Your private AI chief of staff. Tasks, research, and cross-context intelligence."

**Screen 4 — Name your AI**
"What should your AI go by?" (pre-filled with species-appropriate suggestions)

**Screen 5 — Permissions**
Mic, notifications, camera (one screen, clear explanations)

**Screen 6 — Done**
Mode-appropriate welcome:
- Companion: "Say hi to [name]! 🐾"
- Executive: "Ask [name] anything. Try: 'What's happening at home?'"

### Task 6 — Rename Mode Labels
Update all UI references:
- "Pet Mode" → "Companion Mode" (or just "Companion")
- "Tool Mode" → "Executive Mode" (or just "Executive")
- Internal `ModeContext` value stays `"pet"` / `"tool"` — only UI labels change

### Task 7 — Drop Your Gate
Create `sprints/current/gates/gate_freya.md` using write_to_file.

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

---

## Notes
- The smart command bar is the #1 feature. It's what makes the phone feel like a remote control for a mesh of AI agents.
- Cross-context search is the "holy shit" feature for executives.
- Hosted onboarding can show a waitlist for now — actual container provisioning is Sprint 9+.
- Build ON TOP of Sprint 7 code.

# Sprint 8 — FREYA (Frontend: Settings + Onboarding v2 + Ship)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).

> [!IMPORTANT]
> **READ FIRST:** `sprints/current/CREATIVE_DIRECTION.md` — this is your brand bible.
> It contains app icon assignment, splash screen, color palette, and mode-specific tone guidance.
> The 3 brand images you received are assigned there. Follow it exactly.

---

## Context

This is the ship sprint. The app has everything it needs feature-wise. You're adding the last missing UX pieces and getting it ready for TestFlight.

---

## Your Tasks

### Task 1 — Settings Screen
Build `mobile/app/settings.tsx` — accessible from a gear icon in the tab bar or header:

1. **Mode switch** — "Companion Mode" ↔ "Executive Mode" toggle
2. **Connection** — Status indicator (green/red dot), host IP, "Re-pair" button
3. **Companion** — Name, species, level (read-only display)
4. **Voice** — Enable/disable voice mode toggle
5. **Notifications** — Toggle categories (companion care, tasks, guardian)
6. **Privacy** — "All data stays on your PC" with lock icon
7. **About** — App version, build number, "Powered by Fireside"

Keep it clean. No nested menus. One scrollable screen.

### Task 2 — Onboarding v2
Rebuild the onboarding flow with TWO paths:

**Screen 1 — Welcome**
"Your private AI companion"

**Screen 2 — Connect**
- 🏠 **"I have Fireside on my PC"** → QR code scan (already built in Sprint 7) + manual IP fallback
- ☁️ **"Set it up for me"** → email input → calls `POST /api/v1/waitlist` → shows "You're on the waitlist! We'll let you know when your private AI is ready." → stores `connectionMode: "waitlist"` in AsyncStorage

**Screen 3 — Choose your mode** (only for self-hosted path — waitlist users skip this)
- 🐾 **"Companion"** — "A friendly AI that grows with you"
- 💼 **"Executive"** — "Your private AI assistant for tasks and research"

**Screen 4 — Permissions**
Mic, notifications, camera — one screen, clear "why we need this" text

**Screen 5 — Done**
Mode-appropriate welcome message

For waitlist users: show a friendly "Your spot is saved" screen with the app in a limited demo mode or just end gracefully.

### Task 3 — Mode Rename
Update ALL UI-facing labels:
- "Pet Mode" → **"Companion"**
- "Tool Mode" → **"Executive"**
- Internal `ModeContext` values stay `"pet"` / `"tool"` — only display labels change
- Update the mode toggle component text
- Update any tab labels that reference modes

### Task 4 — Marketplace Browse-Only
On the marketplace tab, hide or disable the "Buy" / "Install" buttons for PAID items. Free items can still be installed. Show a note on paid items: "Purchase on desktop dashboard."

This avoids the Apple IAP requirement for launch. Users browse on mobile, buy on desktop.

### Task 5 — TestFlight Pre-Flight Check
Verify everything is ready:

1. `app.json`:
   - `name`: "Fireside" (or final app name)
   - `slug`, `version` (1.0.0), `bundleIdentifier`
   - `icon` (1024x1024) — use existing or placeholder
   - `splash` image
   - All permission strings (camera, mic, notifications) with user-friendly descriptions
2. `eas.json`: preview and production profiles exist
3. No hardcoded localhost URLs — all use the dynamic host from pairing
4. No `console.log` spam in production build
5. Document the build command: `npx eas-cli@latest build --platform ios --profile preview`

### Task 6 — Drop Your Gate
Create `sprints/current/gates/gate_freya.md` using write_to_file.

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

---

## Notes
- This is a POLISH sprint, not a feature sprint. Resist the urge to add features.
- The goal is: owner runs `eas build` after this sprint and tests on a real iPhone.
- Hosted waitlist is a demand test, not a product. Keep it simple.
- Build ON TOP of Sprint 7 code.

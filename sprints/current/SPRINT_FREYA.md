# Sprint 9 — FREYA (Frontend: Rich Cards + Search + App Store Fixes)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).

> [!IMPORTANT]
> **READ:** `sprints/current/CREATIVE_DIRECTION.md` — continues from Sprint 8.
> This is the LAST sprint before a real iPhone gets the app. Everything must be polished.

---

## Context

This sprint fixes Heimdall's 3 pre-App Store items, adds rich action cards to chat, and adds cross-context search. After this: TestFlight.

---

## Your Tasks

### Task 1 — Rich Action Cards in Chat
When a chat response includes an `action` field, render a visual card instead of (or alongside) plain text:

**Browse Result Card:**
- Title + URL (truncated, tappable to open in browser)
- Summary paragraph
- Key points as bullet chips
- Timestamp
- Fire-orange left border accent

**Pipeline Status Card:**
- Task name + current stage
- Progress bar (fire-orange fill)
- Estimated completion
- Pulsing animation while in progress

**Pipeline Complete Card:**
- Task name + completion badge ✅
- Results summary
- Confetti micro-animation (subtle, like achievements)

**Memory Recall Card:**
- Source badge (🧠 Memory / 📚 Taught / 💬 Chat)
- Content snippet
- Date
- Dimmer styling than regular messages — it's supplemental

**Translation Result Card:**
- Language pair (flag emojis if possible)
- Original text → translated text
- Copy button

All cards should use the fire-orange palette from `CREATIVE_DIRECTION.md`. Cards go in the chat feed as companion messages.

### Task 2 — Cross-Context Search
Build `mobile/src/SearchAll.tsx`:

1. Search icon in the chat header (magnifying glass)
2. Tapping opens a search overlay/screen
3. Search input: "Search across your AI's memory..."
4. Call `POST /api/v1/companion/query` (debounced 500ms)
5. Results grouped by source with icons:
   - 🧠 Working Memory
   - 📚 Taught Facts
   - 💬 Conversations
   - 🔮 Hypotheses
6. Each result: source icon, content preview (2 lines), relevance badge, date
7. Tap result → expand to full content
8. Empty state: "Your AI's memory is empty. Start chatting, teaching, and exploring!"

Accessible from both Companion and Executive mode chat screens.

### Task 3 — Update Privacy Policy
Update `mobile/app/privacy.tsx` to cover ALL features added in Sprints 4-8:

| Feature | Privacy Statement |
|---|---|
| Voice mode | "Microphone audio is sent to your home PC for speech recognition (Whisper). Audio is never stored or sent to any cloud service." |
| Camera (QR) | "Camera is used only for scanning QR pairing codes. No photos are taken or stored." |
| Marketplace | "Marketplace browsing sends requests to your home PC's plugin registry. No browsing data is shared externally." |
| Translation | "Text translation is performed by NLLB-200 on your home PC. Translated text never leaves your network." |
| TeachMe | "Facts you teach your companion are stored on your home PC in its memory files." |
| Achievements | "Achievement progress is stored on your home PC." |
| Weekly summary | "Weekly activity stats are generated from data on your home PC." |
| Waitlist | "If you join the hosted waitlist, your email address is stored. No other data is collected until your instance is provisioned." |

Replace contact email: `privacy@valhalla.local` → `hello@fablefur.com`

### Task 4 — Fix EAS Preview Profile
In `mobile/eas.json`, update the `preview` profile:

```json
// Before:
"preview": {
  "distribution": "internal",
  "ios": { "simulator": true }
}

// After:
"preview": {
  "distribution": "internal"
}
```

Remove `simulator: true` so the build targets real devices for TestFlight.

### Task 5 — Brand Art Finalization
The owner provided 3 brand images. Ensure:

1. **App icon** (`mobile/assets/icon.png`) — flame + companion silhouette on dark background. Must be 1024x1024. If the provided image isn't exact, crop/resize to fit.
2. **Splash screen** (`mobile/assets/splash.png`) — all 6 species around campfire under stars. Scale to fit splash dimensions.
3. **Adaptive icon** (Android) — update `android-icon-foreground.png` with the flame icon

If the brand images aren't accessible in the mobile assets directory, create placeholder-quality versions using the fire-orange palette and document what the owner needs to manually replace.

### Task 6 — Drop Your Gate

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

---

## Notes
- This is the LAST implementation sprint. After this: TestFlight build → real iPhone testing.
- Prioritize the 3 Heimdall fixes (privacy policy, email, EAS). Those are BLOCKERS for App Store.
- Rich cards and search are the UX polish that makes the app feel premium on first use.
- Follow `CREATIVE_DIRECTION.md` for all visual decisions.

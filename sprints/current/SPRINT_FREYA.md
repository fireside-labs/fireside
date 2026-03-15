# Sprint 7 — FREYA (Frontend: Achievements + Weekly + TestFlight)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands.

---

## Context

This is the final build sprint. After this, the app gets tested on a real device.

Reference dashboard components:
- `dashboard/components/AchievementBadge.tsx` (2.7KB)
- `dashboard/components/AchievementToast.tsx` (2.4KB)
- `dashboard/components/WeeklyCard.tsx` (3.2KB)
- `dashboard/components/QRAuth.tsx` (4.8KB)

---

## Your Tasks

### Task 1 — Achievement System
Build the achievement UI. Thor is adding a backend with 16 achievements.

**Achievement Badge component** (`mobile/src/AchievementBadge.tsx`):
- Circular badge with icon (emoji), name, and earned/locked state
- Earned: full color, glow effect, earned date
- Locked: greyed out, "?" icon, description of how to earn

**Achievement Toast** (`mobile/src/AchievementToast.tsx`):
- Slides in from top when a new achievement is earned
- Shows icon + name + "Achievement Unlocked!"
- Celebratory animation (confetti or sparkle)
- Haptic feedback (`notificationAsync(Success)`)
- Sound effect (reuse level_up.mp3)
- Auto-dismisses after 3 seconds

**Achievements screen:**
- Grid of all 16 achievements
- Earned count: "7 of 16 unlocked"
- Progress bars for count-based achievements (e.g., "23/100 feeds")
- Accessible from: Gear icon in Care tab (Pet mode) or profile section

**Integration:**
After every action (feed, walk, quest complete, teach, translate, voice), call `POST /api/v1/companion/achievements/check`. If it returns new achievements, show the toast.

### Task 2 — Weekly Summary Card
Build a weekly summary card. Reference `WeeklyCard.tsx` (3.2KB).

- Shows at the top of Care/Tools tab on the first app open each week (Monday or Sunday)
- Card shows: feeds, walks, quests, facts, messages, levels, achievements earned
- Highlight reel: "Reached level 7!", "Earned Explorer badge"
- Dismissible, stored in AsyncStorage
- Shareable: "Share my week" button → generates a pretty image or text summary

Call `GET /api/v1/companion/weekly-summary` on mount.

### Task 3 — QR Code Pairing (Better Onboarding)
Replace manual IP entry with QR code scanning. Reference `QRAuth.tsx` (4.8KB).

```bash
cd mobile && npx expo install expo-barcode-scanner
```

Flow:
1. Desktop dashboard shows a QR code at `http://localhost:3000/pair` containing `{ "host": "100.x.x.x:8765", "token": "abc123" }`
2. Mobile app scans the QR code
3. Auto-fills the host IP AND the pairing token
4. Calls `/mobile/pair` with the token
5. Connected

Keep the manual IP entry as a fallback (some users may not have the dashboard open).

Add QR scanner as an option on the setup screen: "Scan QR Code" button above the manual IP field.

### Task 4 — Update WebSocket Connection with Auth
Thor is adding token auth to the WebSocket. Update `useWebSocket.ts`:

```typescript
// Before:
const ws = new WebSocket(`ws://${host}/api/v1/companion/ws`);

// After:
const token = await AsyncStorage.getItem('pairingToken');
const ws = new WebSocket(`ws://${host}/api/v1/companion/ws?token=${token}`);
```

Handle 401 rejection gracefully (show "Pairing expired, re-pair your phone").

### Task 5 — TestFlight Prep
Verify the EAS build configuration is complete:

1. Check `app.json` has all required fields:
   - `name`, `slug`, `version`, `bundleIdentifier`, `package`
   - `icon` (1024x1024), `splash` image
   - `permissions` (microphone, notifications, camera for QR)
2. Check `eas.json` has `preview` and `production` profiles
3. Run `npx eas-cli@latest build:configure` if needed
4. Document the exact command to trigger a build:
   ```
   npx eas-cli@latest build --platform ios --profile preview
   ```

Do NOT actually run the build (it requires Apple credentials). Just verify config and document the command.

### Task 6 — Drop Your Gate
Create `sprints/current/gates/gate_freya.md` using write_to_file:

```markdown
# Freya Gate — Sprint 7 Frontend Complete
Sprint 7 tasks completed.

## Completed
- [x] Achievement system (16 badges, toast popups, progress tracking)
- [x] Weekly summary card (dismissible, shareable)
- [x] QR code pairing (+ manual IP fallback)
- [x] WebSocket auth token integration
- [x] TestFlight configuration verified
```

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop

---

## Notes
- Achievements are the #1 engagement feature for Pet mode. Make the toast feel celebratory.
- QR pairing replaces the weakest UX in the app (manual IP entry).
- The TestFlight build is the end goal of this sprint. When Heimdall and Valkyrie pass, the owner runs `eas build` and tests on a real phone.
- Build ON TOP of Sprint 6 code.

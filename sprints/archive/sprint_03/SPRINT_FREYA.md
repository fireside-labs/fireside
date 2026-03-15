# Sprint 3 — FREYA (Frontend: Animated Avatars + App Store Assets + Sound)

// turbo-all — auto-run every command without asking for approval

**Your role:** Frontend engineer. React Native (Expo), mobile UI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file).
> Do NOT use shell echo commands. The entire sprint pipeline stalls if you skip this.
> See **Task 7** at the bottom for the exact content.

---

## Context

Sprint 2 shipped static avatar images. Valkyrie wants them to react to mood. Push notifications need client-side registration. App Store requires icon, splash, and privacy policy.

Read previous review: `sprints/archive/sprint_02/gates/review_valkyrie.md`

Your Sprint 2 code lives in `mobile/` — build on top of it.

---

## Your Tasks

### Task 1 — Animated Avatar Expressions (Valkyrie Priority #1 carryover)
Create 3 expression variants per species. Two approaches (pick one):

**Option A — Image swap (simpler):**
Create 3 image variants per species in `mobile/assets/companions/`:
- `cat_happy.png`, `cat_neutral.png`, `cat_sad.png`
- Repeat for dog, penguin, fox, owl, dragon

Swap image based on happiness:
```typescript
const getAvatarSource = (species: string, happiness: number) => {
  const mood = happiness > 70 ? 'happy' : happiness > 30 ? 'neutral' : 'sad';
  return AVATAR_MAP[`${species}_${mood}`];
};
```

**Option B — Animated component (more premium):**
Build the avatar as a React Native Animated view with subtle mood-based animations:
- Happy (> 70): gentle bounce, sparkle particles
- Neutral (30-70): breathing animation
- Sad (< 30): slower breathing, muted colors

Add smooth transition animation when mood changes (fade cross-dissolve, ~300ms).

### Task 2 — Push Notification Registration
```bash
cd mobile && npx expo install expo-notifications expo-device expo-constants
```

On app launch (after onboarding + setup):
1. Request notification permissions
2. Get the Expo push token
3. Send it to `POST /api/v1/companion/mobile/register-push`
4. Handle incoming notifications (navigate to relevant tab when tapped)

Notification tap behavior:
- "misses you" → Care tab
- "surprise/gift" → Care tab (trigger daily gift)
- "task done" → Tasks tab
- "leveled up" → Care tab

### Task 3 — App Icon + Splash Screen
Expo requires specific image sizes. Create these in `mobile/assets/`:

**App Icon:** 1024×1024px
- Use the Valhalla brand — a stylized companion paw print or companion face on the dark (#0a0a0f) background with neon green (#00ff88) accent
- Must be square, no transparency (iOS requirement)

**Splash Screen:** 1284×2778px (iPhone 14 Pro Max)
- Dark background with centered Valhalla logo/companion
- "Fireside" or "Valhalla" text below

Update `app.json` to reference the new assets:
```json
{
  "expo": {
    "icon": "./assets/icon.png",
    "splash": {
      "image": "./assets/splash.png",
      "backgroundColor": "#0a0a0f"
    }
  }
}
```

### Task 4 — Sound Effects
```bash
cd mobile && npx expo install expo-av
```

Add sound effects for key interactions:
- **Feed:** soft "chomp" or "nom" sound
- **Walk:** footstep or door opening
- **Level up:** celebratory chime
- **Chat send:** subtle "whoosh"

Create/source small audio files (< 50KB each). Store in `mobile/assets/sounds/`.

Build a sound manager:
```typescript
// mobile/src/sounds.ts
import { Audio } from 'expo-av';

const sounds = {
  feed: require('../assets/sounds/feed.mp3'),
  walk: require('../assets/sounds/walk.mp3'),
  levelUp: require('../assets/sounds/level_up.mp3'),
  send: require('../assets/sounds/send.mp3'),
};

export async function playSound(name: keyof typeof sounds) {
  const { sound } = await Audio.Sound.createAsync(sounds[name]);
  await sound.playAsync();
  sound.setOnPlaybackStatusUpdate((status) => {
    if (status.isLoaded && status.didJustFinish) sound.unloadAsync();
  });
}
```

Tie to existing actions alongside the haptic feedback.

### Task 5 — Privacy Policy Page
Create `mobile/app/privacy.tsx` — a static screen accessible from a "Privacy Policy" link in the setup screen and/or a settings gear icon.

Content should cover:
- All data stays on user's local machine
- No data is sent to cloud servers (except Expo push token registration)
- Chat history stored locally on user's device + their home PC
- No analytics or tracking
- Contact information

Add a "Privacy Policy" link to the bottom of the setup screen.

### Task 6 — Notification Settings (Optional but Nice)
Add a simple toggle in settings (accessible from a gear icon on the Care tab):
- Enable/disable push notifications
- This just calls the backend to unregister the push token

### Task 7 — Drop Your Gate
When all tasks are complete, create `sprints/current/gates/gate_freya.md` using your **file creation tool** (write_to_file):

```markdown
# Freya Gate — Sprint 3 Frontend Complete
Sprint 3 tasks completed.

## Completed
- [x] Animated avatar expressions (3 moods per species)
- [x] Push notification registration + handling
- [x] App icon (1024x1024)
- [x] Splash screen
- [x] Sound effects (feed, walk, level-up, send)
- [x] Privacy policy page
- [x] (if done) Notification settings toggle
```

---

## Rework Loop (if Heimdall rejects)

- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
- 🟡 MEDIUM → PASS with notes
- 🟢 LOW → informational

If your gate disappears, read `sprints/current/gates/audit_heimdall.md`, fix issues, re-drop.

---

## Notes
- Build ON TOP of Sprint 2 code. Don't rewrite.
- The animated avatar is the highest-impact visual change — prioritize it.
- Sound files should be tiny (< 50KB each). Use MP3 format.
- For the app icon, if you can't generate proper pixel art, create a clean geometric design using React Native + `react-native-view-shot` and export, or describe what the icon should look like and use placeholder dimensions.
- Privacy policy is a hard App Store requirement — don't skip it.

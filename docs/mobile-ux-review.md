# Mobile UX Review

> **Status:** PWA not yet built. This is a criteria spec for when Freya builds it.

---

## Architecture Decision: ✅ PWA is Correct

The spec says: "Mobile is a PWA connecting to the user's home PC, not running inference on the phone."

This is the right call:
- No App Store review process (Apple takes weeks + 30% cut)
- Instant updates (deploy new code, users get it next visit)
- Works on both iPhone and Android
- Phone is a thin client — all AI runs on user's PC
- "Add to Home Screen" makes it feel native

---

## What's Needed (Not Yet Built)

| Component | File | Status |
|---|---|---|
| PWA manifest | `public/manifest.json` | ❌ Not built |
| Service worker | `public/sw.js` | ❌ Not built |
| PWA icons | `public/icons/` | ❌ Not built |
| Mobile chat | Responsive chat page | ⚠️ Partially (Sprint 3 responsive, needs voice button) |
| QR auth | `components/QRAuth.tsx` | ❌ Not built |
| Voice button | `components/VoiceButton.tsx` | ❌ Not built |

---

## Page-by-Page Mobile Audit (375px width)

| Page | Mobile Ready? | Issue |
|---|---|---|
| Chat (home) | ⚠️ Mostly | Needs keyboard-aware layout, voice button |
| Settings | ✅ | Forms work at narrow width |
| Personality | ✅ | Form-based, responsive |
| Connected Devices | ✅ | Cards stack vertically |
| Task Builder | ⚠️ | Task cards may truncate at 375px |
| Learning | ✅ | Stats + cards stack well |
| Guild Hall | ⚠️ | 16:9 scene on 375px = very small. Needs landscape prompt or scroll |
| Agent Profile | ⚠️ | Slider labels may overlap at narrow width |
| Store/Marketplace | ✅ | Card grid should collapse to single column |

---

## QR Code Auth Flow

**Desktop shows:**
```
┌──────────────────────────────────────┐
│                                      │
│     📱 Connect Your Phone            │
│                                      │
│     ┌──────────────────┐             │
│     │  ████████████    │             │
│     │  █          █    │             │
│     │  █  QR CODE  █    │            │
│     │  █          █    │             │
│     │  ████████████    │             │
│     └──────────────────┘             │
│                                      │
│     Scan with your phone's camera.   │
│     Token expires in 5:00            │
│                                      │
└──────────────────────────────────────┘
```

**Phone scans → opens URL with embedded token → authenticated → mobile dashboard.**

### Requirements
- Token in QR code valid for 5 minutes only
- After scan: "🟢 Phone connected!" on both desktop and phone
- Token stored securely on phone (localStorage is fine for PWA)
- Monthly token refresh (automatic, no re-scan)
- "Disconnect all phones" button in Settings for security

---

## Mobile Chat UX

```
┌─────────────────────────┐
│  🟢 Connected to        │
│     Home PC              │
├─────────────────────────┤
│                         │
│  You: Summarize my      │
│  meeting notes           │
│                         │
│  AI: Here's what I      │
│  found in today's       │
│  notes:                 │
│  • Decided to launch…   │
│  • Jordan owns…         │
│                         │
│                         │
├─────────────────────────┤
│  ┌───────────────┐ 🎤 ▶ │
│  │ Type message   │      │
│  └───────────────┘      │
└─────────────────────────┘
```

- Connection indicator at top (green = connected, red = offline with retry)
- Voice button (🎤) visible only when voice is enabled on home PC
- Hold-to-talk: press and hold 🎤, release to send
- Keyboard pushes chat up (not overlaps it)
- Send button disables during inference (prevents double-send)

---

## Guild Hall on Mobile

**Problem:** 16:9 scene on a 9:16 phone = tiny.

**Options:**
1. **Landscape prompt:** "Rotate your phone to see the Guild Hall" — annoying
2. **Vertical layout:** Stack agents vertically with activity labels — loses the "scene" feel
3. **Horizontal scroll:** Full scene, horizontally scrollable — best option
4. **Simplified list:** On mobile, show agent list with activity icons instead of full scene

**Recommendation:** Option 4 (simplified list) on phone, full scene on tablet/desktop. The guild hall's value is visual delight — if it's too small to see, show a clean list instead.

```
┌─────────────────────────┐
│  🏰 Your Team            │
├─────────────────────────┤
│  ⚔️ Thor       🔨 Building  ████░░ │
│  🎨 Freya      📝 Writing        │
│  🛡️ Heimdall   🔍 Reviewing      │
│  👑 Valkyrie   📚 Researching    │
└─────────────────────────┘
```

---

## PWA Manifest Spec

```json
{
  "name": "Valhalla",
  "short_name": "Valhalla",
  "description": "Your personal AI that learns overnight",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0a0a12",
  "theme_color": "#00ff88",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

---

## Recommendations

| Priority | Fix |
|---|---|
| Must (for mobile) | Build `manifest.json` + service worker |
| Must (for mobile) | QR code auth with 5-minute expiry |
| Must (for mobile) | Mobile-friendly agent list (replace guild hall at 375px) |
| Should | Voice button on mobile chat |
| Should | Connection indicator (🟢/🔴) |
| Later | Offline fallback page |
| Later | Push notifications via service worker |

---

## Launch Decision

### 🚫 Don't launch mobile PWA in Sprint 9.

The web dashboard works on mobile browsers already (Sprint 3 responsive). The PWA adds:
- Offline support (not critical — AI needs the home PC anyway)
- "Add to Home Screen" (nice, not essential)
- QR auth (important but can be added post-launch)

**Ship the web dashboard.** Users can access `http://their-pc:3000` from phone. PWA is a post-launch polish item.

# Guardian Keyboard — Custom System Keyboard

A full QWERTY keyboard with two superpowers baked in:

1. **🛡️ Guardian** — analyzes text as you type and shows a companion-voiced
   warning bar when it detects risky patterns (2AM messages, angry sentiment,
   ex-partner mentions, ALL CAPS, profanity bursts)
2. **🌐 Translate** — globe button on the toolbar translates your text inline,
   routing to the Mac Mini NLLB-200 over LAN first, with Google Translate
   as cloud fallback

```
User types angry message at 2am
  → Guardian bar slides in: "🐧 Sir Wadsworth says: Sir. I must advise..."
  → [Softer ✨] rewrites the message  |  [Ignore] dismisses
  → 🌐 tap translates text inline
```

## Platform Setup

### iOS (requires EAS Build)

The custom keyboard extension appears in Settings → Keyboards → Add.

**To enable:** In `app.json`:
```json
"plugins": [
  "./modules/guardian-keyboard/expo-plugin",
  ...
]
```

Build: `eas build --platform ios` or `npx expo run:ios`.
Then: Settings → General → Keyboard → Keyboards → Add → "Guardian Keyboard".

**Note:** Allow Full Access is needed for the translate feature (network).

### Android (requires EAS Build)

The IME service is registered in AndroidManifest automatically.

Build: `eas build --platform android` or `npx expo run:android`.
Then: Settings → Languages & Input → Manage Keyboards → enable "Guardian Keyboard".

## Files

| File | Purpose |
|------|---------|
| `ios/KeyboardViewController.swift` | iOS keyboard — QWERTY + Guardian + Translate |
| `ios/Info.plist` | Extension config — keyboard-service with open access |
| `android/FiresideKeyboardService.java` | Android IME — QWERTY + Guardian + Translate |
| `android/method.xml` | IME metadata — declares input method subtype |
| `expo-plugin.js` | Expo config plugin — wires extension into both platforms |

## Guardian Heuristics (from guardian.py)

| Check | Severity | Trigger |
|-------|----------|---------|
| Late night | Medium | Typing between midnight–5am |
| ALL CAPS | Medium | >70% uppercase with >10 chars |
| Ex-partner | High | "my ex", "ex girlfriend", etc. |
| Reply-all | High | "@everyone", "@all", "reply all" |
| Profanity | Medium | ≥2 profanity words or >10% density |
| Exclamation | Low | ≥3 exclamation marks |
| Angry wall | High | >500 chars with angry sentiment |

## Shared Settings (App Group / SharedPreferences)

The keyboard reads companion settings from the main Fireside app:
- `companion_species` — determines emoji and warning voice
- `companion_name` — shown in the warning bar header
- `pc_host` — Mac Mini IP for LAN NLLB-200 translation

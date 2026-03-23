# Translate with Ember — Inline Share Extension

Provides "Translate with Ember" in the system share/action menu.
**Translates inline without leaving the current app** — shows a compact
overlay inside WhatsApp, iMessage, etc.

```
User selects text → Share/Action menu → "Translate with Ember"
  → Dark overlay appears inside WhatsApp
  → Auto-translates (Home PC or Google Translate)
  → User taps Copy → overlay dismisses
  → Still in WhatsApp with translation on clipboard
```

## Translation Priority

1. **Home PC** (NLLB-200) → private, 200 languages, no cloud
2. **Google Translate** (cloud) → fallback when away from PC, 130+ languages

The overlay shows which engine was used: 🏠 Home PC (green) or ☁️ Google Translate (yellow).

## Platform Setup

### Android (automatic)
The intent filter in `app.json` routes `ACTION_SEND text/plain` to
`TranslateOverlayActivity`, which renders a translucent popup over the caller.

**No additional build steps needed** — works after `eas build` or `npx expo run:android`.

### iOS (requires EAS Build)
The Action Extension shows a bottom sheet overlay with built-in translation UI.

**To enable:** Add to `app.json` plugins:
```json
"plugins": [
  "./modules/translate-extension/expo-plugin",
  ...
]
```

Then build with `eas build --platform ios` or `npx expo run:ios`.

**Note:** iOS extensions don't work in Expo Go. You need a development build.

## Files

| File | Purpose |
|------|---------|
| `ios/ActionViewController.swift` | iOS extension — full inline translate UI (bottom sheet) |
| `ios/Info.plist` | Extension config — activates on text selection |
| `android/TranslateOverlayActivity.java` | Android overlay — translucent popup translate UI |
| `expo-plugin.js` | Expo config plugin — wires extension into Xcode project |

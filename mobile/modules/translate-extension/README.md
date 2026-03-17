# Translate with Ember — iOS/Android Extension

Provides "Translate with Ember" in the system share/action menu.
When a user selects text in any app and taps the action:

1. Text is captured
2. Deep linked to `valhalla://translate?text=...`
3. Main app opens the translate screen
4. NLLB-200 on PC translates (200 languages, offline)
5. User taps Copy to bring translation back

## Platform Setup

### Android (automatic)
The intent filter in `app.json` registers the app for `ACTION_SEND` with `text/plain`.
When the user shares text, the app opens the translate screen.

**No additional build steps needed** — works after `eas build` or `npx expo run:android`.

### iOS (requires EAS Build)
The Action Extension (`com.apple.ui-services`) needs to be added as a separate
target in the Xcode project. This is handled by the Expo config plugin.

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
| `ios/ActionViewController.swift` | Extension controller — extracts text, deep links to app |
| `ios/Info.plist` | Extension config — activates on text selection only |
| `expo-plugin.js` | Expo config plugin — wires extension into Xcode project |

## How Translation Works

```
User selects text → Action menu → "Translate with Ember"
  → ActionViewController.swift extracts text
  → Opens valhalla://translate?text=...
  → translate.tsx receives text
  → POST /api/v1/companion/translate {text, target_lang}
  → NLLB-200 on PC translates
  → User copies result back to original app
```

The NLLB model runs entirely on the user's home PC. No text leaves their network.

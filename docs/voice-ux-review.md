# Voice UX Review

> **Key constraint:** Voice runs on the user's hardware. Whisper STT needs ~1.5GB free VRAM. Kokoro TTS runs on CPU (free). If the user doesn't have VRAM headroom, voice won't work — and the system needs to handle that gracefully.

---

## Capability Detection: ✅ Well-Handled

Thor's `voice/handler.py` does this right:

```
Free VRAM after brain → ≥ 2GB → "available"
Free VRAM after brain → < 2GB → "not_recommended" + tip
```

The tip is critical: "Use a smaller brain to free VRAM for voice" — this tells the user exactly what to do instead of just saying "not supported."

**Recommendation:** Show this as a visual in Settings:

```
┌─ Voice ──────────────────────────────────────────┐
│                                                    │
│  🎤 Voice Chat                          [ OFF ]   │
│                                                    │
│  Your hardware: ⚠️ Limited                        │
│  Your brain uses most of your AI memory.           │
│  Switch to "Smart & Fast" to free up space.        │
│                                                    │
│  ┌──────────────────────────────────┐              │
│  │ AI Memory:  ████████░░ 12/16 GB │              │
│  │ Brain:      ██████░░░░  8 GB    │              │
│  │ Voice:      ██░░░░░░░░  1.5 GB  │              │
│  │ Free:       ██░░░░░░░░  4.5 GB  │  ✅ Enough! │
│  └──────────────────────────────────┘              │
└────────────────────────────────────────────────────┘
```

---

## Enable/Disable Flow: ✅ Good

- `POST /api/v1/voice/enable` → installs faster-whisper + kokoro if needed, loads model
- `POST /api/v1/voice/disable` → unloads model, frees VRAM

**What's good:** It's a single toggle. No multi-step setup. No configuration needed.

**One concern:** The enable endpoint installs pip packages (`faster-whisper`, `kokoro`, `soundfile`). On first enable, this could take 30-60 seconds. The UI should show a progress indicator, not just freeze.

---

## Voice Picker: ✅ Good Foundation

5 built-in voices:

| ID | Label | Style |
|---|---|---|
| `af_default` | Default (Female) | Neutral |
| `am_default` | Default (Male) | Neutral |
| `af_warm` | Warm (Female) | Warm |
| `am_deep` | Deep (Male) | Authoritative |
| `af_bright` | Bright (Female) | Energetic |

**What works:** Clear labels, gender included, style described.

**What's needed in UI:**
1. 5-second audio preview for each voice (play button next to each option)
2. "Test voice" button — AI says "Hello! I'm your Valhalla AI. How can I help you today?" in selected voice
3. Speed slider (0.5x to 2.0x) — Thor's API supports this via `set_speed`

---

## Microphone Button (Mobile): Spec Review

The spec says: "🎤 Microphone button next to send button, hold-to-talk or toggle mode."

**Recommendations for Freya:**
1. **Hold-to-talk** should be the default on mobile — it's familiar (voice messages in WhatsApp, Telegram)
2. **Toggle mode** as a setting for accessibility (users who can't hold a button)
3. **Visual feedback:** pulsing red circle while recording, waveform animation
4. **Audio level meter:** show the user that their voice is being picked up
5. **Cancel:** slide finger away from button to cancel (same as Telegram)

---

## Latency Expectations

| Step | Target | Actual |
|---|---|---|
| Audio capture → transcription | < 500ms | Whisper medium, local GPU — should hit this |
| Transcription → AI response (text) | < 2s | Depends on brain speed |
| AI response → voice synthesis | < 1s | Kokoro CPU, short responses |
| **Total roundtrip** | **< 3.5s** | Acceptable for conversation |

**Risk:** On machines without GPU (CPU-only Whisper), transcription could be 2-5 seconds. **Mitigation:** Show a "Listening..." → "Thinking..." → "Speaking..." indicator so the user knows what's happening.

---

## Privacy: ✅ Excellent

| Concern | How It's Handled |
|---|---|
| Voice data leaves device? | ❌ Never. STT runs locally (faster-whisper). TTS runs locally (Kokoro). |
| Voice recordings stored? | ❌ Stream only by default. Opt-in to save. |
| Cloud fallback? | Alert user if voice is routed through cloud. |

This is a major selling point vs Siri/Alexa/Google. "Your voice never leaves your computer." Put that on the landing page.

---

## Recommendations Summary

| Priority | Issue | Fix |
|---|---|---|
| Must | Show progress indicator during first voice enable (pip install) | Loading spinner + "Installing voice models..." |
| Must | Show VRAM usage bar in voice settings | Visual memory breakdown |
| Should | Add 5-second voice previews | Audio samples for each voice |
| Should | Hold-to-talk as mobile default | Familiar UX pattern |
| Should | Listening/Thinking/Speaking indicator | User knows what stage they're in |
| Nice | Speed slider in voice picker | Thor's API already supports it |

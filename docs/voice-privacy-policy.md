# Voice Privacy Policy

> **Module:** `plugins/payments/security.py` → `VoicePrivacyGuard`  
> **Sprint:** 9

---

## Core Principle: Audio Never Leaves Your Network

| Rule | Enforcement |
|------|------------|
| STT runs locally | Only `faster-whisper`, `whisper` accepted. Cloud providers flagged. |
| TTS runs locally | Only `kokoro`, `piper` accepted. Cloud providers flagged. |
| No disk storage | Audio streams processed in memory only. No recordings saved by default. |
| WebSocket localhost | Voice WebSocket bound to `127.0.0.1` only. Network exposure = error. |

## Opt-In Voice Logging (disabled by default)

If a user enables voice logging:
- Audio **must** be encrypted at rest (`audio_encrypted: true`)
- Unencrypted storage = configuration error (blocked)
- User can delete all voice logs at any time

## Cloud Fallback Alerts

If voice is ever routed through a cloud provider (Google, Azure, AWS, OpenAI, ElevenLabs, Deepgram):
- Dashboard shows persistent warning banner
- Alert sent via notification system
- User explicitly acknowledges before proceeding

## What We Don't Do

- ❌ No cloud transcription
- ❌ No audio telemetry
- ❌ No voice fingerprinting
- ❌ No recording without consent
- ❌ No sharing audio with third parties

---

*Voice privacy policy. Heimdall — Sprint 9 (2026-03-10).*

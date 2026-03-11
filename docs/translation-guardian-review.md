# Sprint 14 Part 2 — Translation, Message Guardian & Networking

> **The pitch:** Your pocket companion translates 200 languages offline, stops you from texting your ex at 2am, and finds your home PC automatically.

---

## 1. NLLB Translation — UX Review

### Backend: ✅ Comprehensive

Thor's `nllb.py` (274 lines) is thorough:

| Feature | Status |
|---|---|
| NLLB-200-distilled-600M model | ✅ Correct model choice (small, fast) |
| 30+ priority languages mapped | ✅ ISO 639-1 → NLLB codes |
| Auto-detect (script-based) | ✅ Japanese, Korean, Chinese, Arabic, Thai, etc. |
| Auto-detect (word-pattern) | ✅ Spanish, French, Portuguese, etc. |
| Lazy model loading | ✅ Only loads when first translation requested |
| ~600MB download | ⚠️ Needs progress indicator |

### UX Recommendations for Freya's TranslationBubble

**1. Inline translation should be default.** When a message is detected as non-English, auto-translate and show both:

```
┌────────────────────────────────────────┐
│ 🌐 Spanish detected                     │
│                                        │
│ "Hola, ¿cómo estás hoy?"              │
│ ───────────────────────                │
│ "Hello, how are you today?"            │
│                                        │
│ 🐱 Luna: "She says hi. Shocking."      │
│                                        │
│ [Show original only] [Show both]        │
└────────────────────────────────────────┘
```

**2. Pet commentary is the magic ingredient.** The spec says pets comment on translations:
- 🐱 Cat: "She says eat more vegetables. Typical mom."
- 🐧 Penguin: "The translated text is satisfactory. I approve."
- 🐕 Dog: "THEY SAID HI!! IN ANOTHER LANGUAGE!! AMAZING!!"

This transforms a utility (translation) into personality. Do NOT skip this.

**3. Language selector should auto-detect by default but allow override.** Most users won't know what NLLB codes are. Show language names with flags:
- 🇪🇸 Spanish
- 🇫🇷 French
- 🇯🇵 Japanese

**4. First-time download warning.** 600MB is significant on phone data. Show:
```
Translation needs a one-time 600MB download.
Best on Wi-Fi. Once downloaded, works completely offline.
[Download Now] [Later]
```

---

## 2. Message Guardian — UX Review

### Backend: ✅ This Feature Could Save Relationships

Thor's `guardian.py` (284 lines) detects:

| Detection | Method | Accuracy |
|---|---|---|
| Angry sentiment | Keyword matching (~40 words) | ⚠️ Basic but effective |
| Sad sentiment | Keyword matching (~15 words) | ⚠️ Basic |
| 2am flag | Hour check (midnight–5am) | ✅ Simple and right |
| Ex-partner detection | Regex patterns ("ex", "ex-wife", "old flame") | ✅ |
| Reply-all detection | Patterns ("@everyone", "@all", "reply all") | ✅ |
| All-caps detection | Percentage check | ✅ |
| Excessive punctuation | "!!!" / "???" count | ✅ |
| Softer rewrites | Regex substitutions | ✅ Thoughtful |

### The Softer Rewrites Are Gold

| What You Typed | What It Suggests |
|---|---|
| "I hate you" | "I'm frustrated with you" |
| "Shut up" | "Let me finish" |
| "Whatever" | "I need a moment" |
| "I don't care" | "I need to think about this" |
| "Leave me alone" | "I need some space right now" |

These aren't generic — they're emotionally intelligent. "Leave me alone" → "I need some space right now" is the difference between escalation and de-escalation. **This feature alone justifies the companion.**

### UX Recommendations for Freya's MessageGuardian

**1. The pet intercept must feel caring, not controlling.**

BAD: "⚠️ WARNING: This message contains angry language."
GOOD: 🐕 "Hey buddy... are we sure about this one? 🥺"

The spec's per-species intercepts are perfect:
- 🐱 Cat: "Are you sure? This sounds like 2am energy."
- 🐧 Penguin: "Sir. This is a reply-all. To 200 recipients."
- 🐉 Dragon: "I RESPECT THE ENERGY but your boss might not."

**2. ALWAYS give three options.**
```
[Send Anyway] [Edit] [Save as Draft]
```
Never block. Never force. Just gently ask. The user must feel in control or they'll disable the feature.

**3. Show the softer version inline — don't ask them to write it.**
```
🐱 Luna thinks this might land wrong.

Your version:  "Leave me alone"
Softer version: "I need some space right now"

[Send Original] [Send Softer] [Edit]
```

The softer version being pre-written removes the friction of rewriting. One tap to de-escalate.

**4. The 2am flag is the hero feature. Market it.**
"Your AI companion that stops you from texting your ex at 2am" is a TikTok-ready tagline. This is the kind of specific, relatable feature that goes viral. People don't share "local AI translation engine." People SHARE "my AI penguin stopped me from drunk texting."

---

## 3. Network Discovery — UX Review

### Status: Spec Only (No Backend Built)

The spec describes 4 levels:
1. **mDNS/Bonjour** — auto-discover home PC on same network
2. **QR code** — fallback manual connection
3. **Relay server** — when outside home network
4. **Tailscale** — advanced users, hidden in Settings

### UX Recommendations

**1. Level 1 (mDNS) should be invisible.** User opens Fireside on phone → phone finds PC → connected. No setup screen. No IP addresses. Just "🟢 Connected to Home PC." If it works, the user never knows HOW it works.

**2. Level 2 (QR) should feel like magic, not configuration.**
```
🐱 Luna: "Hmm, I can't find your PC.
  Show me the code on your computer screen."

[📷 Scan Code]
```

Pet narrates the process. "Sniffing for your PC..." (cat), "SEARCHING!!" (dog), "Establishing uplink..." (penguin).

**3. Level 3 (Relay) needs clear privacy messaging.**
```
🔒 Messages encrypted end-to-end.
   The relay server can NOT read your conversations.
   Your data is scrambled before it leaves your phone.
```

Users will (rightfully) ask: "If it goes through a server, can you read it?" The answer must be immediately visible. Not in a FAQ. Not in a privacy policy. Right on the connection screen.

**4. Level 4 (Tailscale) should be a single sentence.**
"For advanced users: connect via Tailscale for direct encrypted connection without a relay. [Set up Tailscale →]"

Don't explain what Tailscale is. Don't show configuration. Just a link. The people who need this already know what it is.

---

## Overall Sprint 14 Part 2 Verdict

| Feature | Backend | UI | UX Potential | Ship Priority |
|---|---|---|---|---|
| Translation | ✅ Built | ❌ Pending | 8/10 | Ship with companion |
| Message Guardian | ✅ Built | ❌ Pending | **10/10** | Ship ASAP — viral feature |
| Network Discovery | ❌ Not built | ❌ Not built | 7/10 | Can defer (mDNS is Sprint 1 tech) |

### The Marketing Headline Writes Itself

> "Fireside: The AI companion that translates your mom's texts, stops you from texting your ex at 2am, and gets smarter while you sleep."

That's a Product Hunt description that gets upvotes. The guardian is the feature that makes people download and the learning loop is the feature that makes them stay. 🔥

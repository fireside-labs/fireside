# Fresh Install Test Protocol — Sprint 11

> **Goal:** Nuke everything. Install from scratch. Screen record the ENTIRE flow. Time every step.
> This recording becomes the first "building in public" content for Fireside's launch.

---

## Pre-Test Setup

```bash
# 1. Back up everything first
cp -r ~/.valhalla ~/valhalla-backup-$(date +%Y%m%d)
cp -r ~/.openclaw ~/openclaw-backup-$(date +%Y%m%d)

# 2. Nuke all Fireside/Valhalla state
rm -rf ~/.valhalla
rm -rf ~/.openclaw
rm -rf ~/Documents/ProjectOpenClaw/valhalla-mesh-v2/node_modules
rm -rf ~/Documents/ProjectOpenClaw/valhalla-mesh-v2/dashboard/.next

# 3. Kill any running processes
pkill -f bifrost || true
pkill -f llama-server || true
pkill -f mlx_lm || true

# 4. Verify clean state
ls ~/.valhalla 2>/dev/null && echo "NOT CLEAN" || echo "✅ Clean"
```

---

## Screen Recording Setup

- **Tool:** QuickTime screen recording (built into macOS)
- **Resolution:** Full screen, 1920×1080 minimum
- **Audio:** Record system audio off, voiceover on (narrate what you're doing)
- **Timer:** Keep a stopwatch visible or overlay timestamps in post

---

## Test Script

### Phase 1: Install (Target: < 3 minutes)

| Time | Action | What to Say (voiceover) |
|---|---|---|
| 0:00 | Open Terminal | "Fresh Mac. Nothing installed. Let's see how long it takes." |
| 0:05 | Run `curl -fsSL getfireside.ai/install \| bash` | "One command. That's all it takes." |
| 0:10 | Watch installer detect OS | "It detects I'm on a Mac with Apple Silicon..." |
| ~0:30 | Dependencies installing | "It's installing Python and Node if I don't have them..." |
| ~1:30 | Dashboard building | "Building the dashboard..." |
| ~2:30 | Browser opens | "And it's open! Let's see how long that took." |
| ~3:00 | Record: **TIME TO DASHBOARD** | ⏱️ [note actual time] |

### Phase 2: Onboarding (Target: < 90 seconds)

| Time | Action | What to Say |
|---|---|---|
| 3:00 | Wizard starts | "First time — it asks my name." |
| 3:10 | Enter name | "My name is [name]." |
| 3:20 | Pick brain | "I'll pick 'Smart & Fast' — it says it works on most computers." |
| 3:30 | Brain download starts | "Downloading the AI model... this is the one-time download." |
| ~5:00 | Brain installed | "Done. It downloaded [X] GB in [Y] minutes." |
| 5:10 | Pick personality | "I'll pick 'Friendly & Warm.'" |
| 5:20 | "Ready!" screen | "And we're in." |
| ~5:30 | Record: **TIME TO FIRST CONVERSATION** | ⏱️ [note actual time] |

### Phase 3: First Conversation (Target: response < 3 seconds)

| Time | Action | What to Say |
|---|---|---|
| 5:30 | Type "Hi, what can you do?" | "Let's see if it actually works..." |
| ~5:33 | AI responds | "There it is! A real response, running on my laptop." |
| 5:45 | Type "What's the weather?" | "Testing a simple question..." |
| 6:00 | Type "Write me a poem about coding" | "And something creative..." |
| 6:15 | Record: **RESPONSE QUALITY** | ⏱️ [note response times] |

### Phase 4: Explore (2 minutes)

| Time | Action | What to Say |
|---|---|---|
| 6:15 | Open Guild Hall | "This is the Guild Hall — watch the agents work." |
| 6:30 | Switch theme to Space | "Different themes... this is the space station." |
| 6:45 | Click Thor's profile | "Each agent has stats, levels, achievements." |
| 7:00 | Open Settings | "Settings are simple — no command line needed." |
| 7:15 | Show personality sliders | "I can make it more creative or more precise." |
| 7:30 | Open Telegram setup | "I can connect it to my phone via Telegram." |
| 8:00 | End recording | "That's Fireside. Installed in [X] minutes. Zero cloud. Runs on my laptop." |

---

## Metrics to Capture

| Metric | Target | Actual |
|---|---|---|
| Time: terminal → dashboard open | < 3 min | ⬜ |
| Time: dashboard → first chat | < 3 min (includes brain download) | ⬜ |
| Time: total end-to-end | < 6 min | ⬜ |
| Brain download size | ~4 GB (7B model) | ⬜ |
| Brain download speed | Depends on internet | ⬜ |
| First response time | < 3 seconds | ⬜ |
| Errors encountered | 0 | ⬜ |
| Confusion points | 0 | ⬜ |

---

## Error Scenarios to Watch For

| Error | Severity | Fix |
|---|---|---|
| Python not found | 🟡 | Installer should auto-install |
| Node not found | 🟡 | Installer should auto-install |
| Port 3000 in use | 🟠 | Installer should pick next available |
| Port 8337 in use | 🟠 | Bifrost should fail gracefully |
| Xcode CLT prompt (macOS) | 🟠 | Installer should handle `xcode-select --install` |
| Gatekeeper blocks llama-server | 🔴 | Need to codesign or `xattr -cr` |
| Brain download fails (network) | 🟠 | Retry button + partial resume |
| Chat returns mock response | 🔴 | **THE blocker** — must be wired first |

---

## Video Editing Notes (Post-Recording)

- Speed up the brain download (2x or 4x) with timer overlay
- Add text overlays at key moments: "⏱️ 2:34 — Dashboard open"
- Title card: "Installing Fireside on a fresh Mac — no terminal knowledge required"
- End card: "getfireside.ai — Your AI companion, always by your side."
- Target video length: 2-3 minutes (8 min raw, cut the waiting)

---

## Content Strategy

This video becomes:
1. **Product Hunt demo video** (top of listing)
2. **Twitter/X launch thread** (gif clips from key moments)
3. **README.md embedded** (shows instead of telling)
4. **YouTube** ("Install a local AI in 3 minutes")

First "building in public" content. Ship it raw. Authenticity > polish.

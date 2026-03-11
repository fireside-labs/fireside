# Telegram UX — Chat & Notifications

> **Design target:** Telegram is the mobile interface to Valhalla. Everything you can do in the dashboard, you can do (in simplified form) from your phone via Telegram.

---

## Setup Flow (Dashboard Side)

### What the user sees in Settings:

```
┌──────────────────────────────────────────────────────┐
│  💬 Telegram                                         │
│                                                      │
│  Step 1: Create a Telegram bot                       │
│  Open Telegram, search for @BotFather, send          │
│  /newbot, and follow the prompts.                    │
│  [Open @BotFather →]                                 │
│                                                      │
│  Step 2: Paste your bot token                        │
│  ┌──────────────────────────────────────────┐        │
│  │  110201543:AAHdqTcvCH1vGWJx...           │        │
│  └──────────────────────────────────────────┘        │
│  [Verify & Connect]                                  │
│                                                      │
│  Status: 🟢 Connected as @MyValhallaBot             │
│                                                      │
│  Step 3: Choose what to notify you about             │
│  Task completed              [  ON  ]                │
│  Task needs your help        [  ON  ]                │
│  Debate deadlock             [ OFF  ]                │
│  Knowledge check found issue [  ON  ]                │
│                                                      │
│  [Send test message]                                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Key design decisions:**
- 3 steps, all in one page, no wizard needed
- "Verify" button gives immediate feedback: ✅ or ❌ with error message
- Notification toggles use the consumer-friendly names, not event bus topics
- Test message confirms the whole chain works

---

## Chat Experience

### First Message

When a user messages the bot for the first time:

```
You:     Hi

Odin:    Hey! 👋 I'm Odin, your Valhalla AI. I'm running 
         on your MacBook with the Smart & Fast brain.
         
         I can help with anything — just type naturally. 
         Or try one of these:
         
         📋 /task — Give me a job to work on
         🧠 /status — How your mesh is doing
         ⚡ /brains — What brains are installed
```

### Normal Conversation

```
You:     Can you summarize the meeting notes from today?

Odin:    📄 I found 2 files with "meeting" in the name from today:
         
         1. meeting-notes-2026-03-10.md (1,247 words)
         2. standup-2026-03-10.md (312 words)
         
         Here's the summary of both:
         
         **Meeting Notes (1:00 PM)**
         • Decided to launch marketplace in Q2
         • Jordan owns the pricing page
         • Next review: Friday 3 PM
         
         **Standup**
         • Sprint 7 in progress — Telegram integration is today's focus
         • No blockers
         
         Want me to go deeper on either one?
```

### Message Formatting Rules

- **Short messages** (< 500 chars) → send as plain text
- **Long messages** (> 500 chars) → send with Telegram markdown formatting (bold, bullet points)
- **Code** → wrap in \`\`\` code blocks
- **Files** → send as document attachments if < 50MB, otherwise link
- **Images** → send inline (Telegram handles this natively)
- **Never** send more than 4096 characters in one message (Telegram limit). Split into multiple messages with "..." indicator.

---

## Commands

| Command | What It Does | Example Output |
|---|---|---|
| `/status` | Mesh health summary | "🟢 Online · 2 devices · Brain: Smart & Fast · 45 tok/s" |
| `/task <description>` | Create a pipeline task | "📋 Task started: 'Write a blog post about AI trends'" |
| `/brains` | List installed brains | "🧠 Smart & Fast (active) · Deep Thinker (installed) · Cloud Expert (ready)" |
| `/switch <brain>` | Change active brain | "⚡ Switched to Deep Thinker. Speed: 12 tok/s" |
| `/help` | Show all commands | Lists all commands with descriptions |

### /status — Detailed Output

```
🟢 Valhalla Status

📱 Devices: 2 online
   💻 Your MacBook — Main AI · Smart & Fast
   🖥️ Office PC — Helper · Deep Thinker

🧠 Brain: Smart & Fast (8B) · 45 tok/s
📋 Tasks: 1 running, 3 completed today
📊 Knowledge: 247 things known · 94% reliable
🌙 Last learned: 6 hours ago
```

### /task — Creating Tasks from Telegram

```
You:     /task Write a privacy policy for our website

Odin:    📋 Task created: "Write a privacy policy for our website"
         
         Quality level: Balanced (7 steps max)
         I'll notify you when it's done or if I need help.
         
         [View in Dashboard →]
```

When the task completes:
```
Odin:    ✅ Task completed: "Write a privacy policy"
         
         Finished in 18 minutes · 5 steps
         📝 Created: docs/privacy-policy.md (2,143 words)
         
         Lesson learned: "Privacy policies need a 
         'data retention' section — added one."
         
         Want me to send the file?
```

When the task needs help:
```
Odin:    ⚠️ Task needs your help: "Update the tax spreadsheet"
         
         I found two different tax rate tables and I'm not 
         sure which one to use:
         
         1. IRS 2025 schedule (from irs.gov)
         2. State-specific table (from state.gov)
         
         Which should I use?
         
         Reply with 1 or 2, or type a different instruction.
```

---

## Push Notifications

### Notification Formats by Event Type

**Task Completed** (`pipeline.shipped`)
```
✅ Task completed: "{title}"
Finished in {duration} · {steps} steps
{lesson_summary if exists}
```

**Task Needs Help** (`pipeline.escalated`)
```
⚠️ Your AI needs help with: "{title}"
{escalation_reason}
Reply here or tap: [Open Dashboard →]
```

**Debate Deadlock** (`debate.deadlock`)
```
🗣️ Debate stuck: "{topic}"
The reviewers can't agree after {rounds} rounds.
Your input would help break the tie.
[View Debate →]
```

**Knowledge Issue Found** (`crucible.broken`)
```
🧪 Knowledge check found {count} weak spot(s)
Your AI will study these overnight, but you can 
review them now:
[View Results →]
```

### Notification Design Rules

1. **First line is the headline.** Must be understandable at glance (notification preview on phone).
2. **Never send jargon.** "Task completed" not "Pipeline shipped." "Knowledge check" not "Crucible cycle."
3. **Always include a link** to the dashboard for the full view.
4. **Respect quiet hours.** Don't send notifications between 10 PM and 8 AM (configurable in Settings).
5. **Batch low-priority notifications.** If 5 knowledge issues found in one cycle, send one message, not 5.

---

## Group Chat Behavior

If the bot is added to a Telegram group:

- **Only responds when @mentioned** or when a message starts with `/`
- **Never sends unsolicited messages** to the group
- **Notifications go to the admin's private chat,** not the group
- Users in the group can use commands (`/status`, `/brains`) but only the admin (whoever set up the bot token) can use `/task` and `/switch`

---

## Security

| Concern | How It's Handled |
|---|---|
| Who can message the bot? | `allowed_users` list in settings. Empty = anyone with the bot link. |
| Can someone steal my data via the bot? | Bot never sends API keys, configs, or credential data. |
| Can someone create tasks via the bot? | Only `allowed_users`. Rate limited to 10 commands/minute. |
| Bot token storage | Encrypted in `~/.valhalla/credentials`, never in `valhalla.yaml`. |
| Message privacy | Messages go through Telegram's servers (encrypted in transit). For full privacy, use the dashboard directly. |

---

## Error Messages

| Situation | What the user sees |
|---|---|
| Brain is offline | "🔴 Your AI brain is offline. Try: /status to check, or open the dashboard to restart it." |
| No brains installed | "🧠 No brain installed yet. Open the dashboard to install one: http://localhost:3000/brains" |
| Task creation fails | "❌ Couldn't create that task. Try again or create it in the dashboard." |
| Rate limited | "⏳ Slow down — max 10 commands per minute." |
| Not authorized | "🔒 You're not authorized to use this bot. Ask the admin to add your Telegram ID to the allowed list." |

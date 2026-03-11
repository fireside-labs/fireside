# Grandma Test Results

> **Test protocol:** Walk through every page as a 60-year-old who has never seen a terminal. For each page: Can they figure out what to do within 10 seconds? Would they ask "what does [X] mean?"

---

## Overall Score: 8.5 / 10

Freya implemented the accessibility spec faithfully. The dashboard went from a 10-item developer tool to a 7-item consumer app. Key wins: chat-first homepage, form-based settings, friendly terminology. Remaining issues are polish, not structural.

---

## Page-by-Page Results

### 💬 Chat (Homepage)
**Result: ✅ PASS**

| Criteria | Pass? | Notes |
|---|---|---|
| Can start a conversation in <30s | ✅ | Chat input is the first thing they see. "Hi Jordan 👋" is warm. |
| Understands suggested prompts | ✅ | "Summarize my emails" is actionable. Plain English. |
| Understands "What your AI did today" | ✅ | ✅ 12 questions, 📁 3 files, 🧠 2 new things — clear. |
| Would ask "what does [X] mean?" | ✅ No | Zero jargon on this page. |

**Issues found:**
- ⚠️ The "Hi 👋" greeting shows blank name when `localStorage` is empty (no onboarding yet). Should default to "there" → "Hi there 👋"
- ⚠️ Chat response is a mock ("This is a mock response"). Need a real fallback or loading indicator when no model is connected.

---

### 🧠 Personality
**Result: ✅ PASS**

| Criteria | Pass? | Notes |
|---|---|---|
| Can change the AI's name | ✅ | Text input, clearly labeled "Name" |
| Can change the tone | ✅ | Radio buttons: Casual, Friendly, Professional, Direct, Playful — each with one-line description |
| Can add skills | ✅ | Checkboxes with "Add a custom skill" option |
| Can add boundaries | ✅ | Plain-English sentence input with "Add rule" |
| Understands what this page does | ✅ | "Change how your AI talks and what it's good at" — perfect subtitle |

**Issues found:**
- ⚠️ "Edit raw personality files" under Advanced links to the old soul editor. The text "SOUL.md / IDENTITY.md / USER.md" leaks jargon if expanded. Suggestion: just say "Edit raw files" without the filenames.

---

### 📱 Connected Devices
**Result: ✅ PASS**

| Criteria | Pass? | Notes |
|---|---|---|
| Understands what devices are shown | ✅ | "Your MacBook," "Office PC" — friendly names |
| Understands device status | ✅ | Green dot + "Online" |
| Can figure out how to add a device | ✅ | Dashed CTA card with "Add another device" |
| No jargon visible | ✅ | IPs hidden under "Show advanced details" |

**Issues found:**
- ⚠️ The FRIENDLY_NAMES map is hardcoded (`odin: "Your MacBook"`, `thor: "Office PC"`). In production, these need to come from config or auto-detection. New user with a different hostname would see `"jordans-imac's Device"` which is OK but not as clean.
- ⚠️ "Brain" label next to the model name still shows the raw model string (e.g., `llama/Qwen3.5-35B-A3B-8bit`). Should show the friendly alias from Settings ("Smart & Fast") instead.

---

### ⚙ Settings
**Result: ✅ PASS**

| Criteria | Pass? | Notes |
|---|---|---|
| Can change AI name | ✅ | Text input |
| Can change role | ✅ | Dropdown: Main Assistant / Helper / Memory Assistant / Security Guard |
| Can change brain | ✅ | BrainPicker component with radio cards |
| Can toggle add-ons | ✅ | Toggle switches with descriptions: "Smart Switching," "Auto-Restart," "Long-Term Memory" |
| No YAML visible | ✅ | Raw config hidden behind "Edit raw config file" toggle |

**Issues found:**
- ⚠️ BrainPicker component was not fully reviewed (outline only). Need to verify it shows FREE/PAID badges and hardware compatibility warnings.
- ⚠️ "valhalla.yaml" text is visible in the Advanced toggle label. Non-technical users won't know what that means. Suggestion: "Edit raw configuration file"

---

### 📋 Task Builder
**Result: ✅ PASS**

| Criteria | Pass? | Notes |
|---|---|---|
| Can create a new task | ✅ | "+ Create New Task" button opens TaskWizard |
| Understands task progress | ✅ | "Step 3 of 7" with progress bar and "Checking quality..." |
| Understands "Needs Your Help" | ✅ | "Your AI got stuck and needs guidance" — perfect |
| Understands completed tasks | ✅ | ✅ with "Lesson learned" in green |
| Has empty state | ✅ | "No tasks yet. Create your first task..." with CTA button |

**Issues found:**
- ⚠️ The `STAGE_LABELS` map has "Getting a second opinion..." for the review stage. This is excellent — keep it.
- ⚠️ TaskWizard component exists but wasn't fully reviewed. The spec calls for a quality slider + notification preference, which needs verification.

---

### 📊 How It's Learning
**Result: ✅ PASS**

| Criteria | Pass? | Notes |
|---|---|---|
| Understands "Things it knows: 247" | ✅ | Clear stat cards with emoji |
| Understands "Reliable: 94%" | ✅ | Green color = good |
| Understands "Getting smarter: +12%" | ✅ | Simple yes/no with percentage |
| Understands discoveries | ✅ | Plain-English: "Your emails are usually shorter on Fridays" |
| Understands overnight learning | ✅ | Three-line story with emoji |
| Advanced views hidden | ✅ | Collapsed under "Advanced — detailed views" |

**Issues found:**
- ⚠️ Confidence bars use color coding (green >90%, amber >70%, gray otherwise) but no legend. A tiny label like "How sure:" before the bar would help.
- ⚠️ "View hypotheses" in the advanced links uses the old term. Should be "View discoveries" for consistency.
- ⚠️ "View knowledge tests" is OK but "Knowledge Check results" would match the terminology map.

---

### 🏪 Store
**Result: NOT TESTED** — Marketplace page wasn't modified in Sprint 6 (waiting for Thor's marketplace API). Existing page still uses some old terminology. Will test when the full marketplace is built.

---

### 🌟 Onboarding Wizard
**Result: ✅ PASS (from source review)**

| Criteria | Pass? | Notes |
|---|---|---|
| 5 screens total | ✅ | Welcome → Name → Brain → Personality → Ready |
| No terminal/YAML | ✅ | Zero technical content |
| Personality as radio cards | ✅ | 😊 Friendly / 💼 Formal / ⚡ Direct with descriptions |
| Stores name for greeting | ✅ | `localStorage.setItem("valhalla_user_name", name)` |
| "Start chatting" as final CTA | ✅ | Calls `onComplete()` which should route to Chat |

**Issues found:**
- ⚠️ Hardware auto-detection (step 3) shows mock data. In production, needs to call `GET /api/v1/system/hardware` (Thor's Sprint 6 task).
- ⚠️ The wizard doesn't show a "You can change this anytime in Personality" reassurance text on the personality screen. Adding this reduces commitment anxiety.

---

## Summary of Fixes Needed

### Priority 1 (before launch)
| # | Page | Issue | Fix |
|---|---|---|---|
| 1 | Chat | Blank name when no onboarding | Default to "there" → "Hi there 👋" |
| 2 | Devices | Raw model string next to "Brain" | Show friendly alias from BrainPicker |
| 3 | Learning | "View hypotheses" link | Rename to "View discoveries" |

### Priority 2 (first update)
| # | Page | Issue | Fix |
|---|---|---|---|
| 4 | Personality | Advanced text shows "SOUL.md" | Remove filenames, just say "Edit raw files" |
| 5 | Settings | "valhalla.yaml" visible in Advanced | Say "raw configuration file" |
| 6 | Learning | Confidence bar has no micro-label | Add "How sure:" before bar |
| 7 | Onboarding | No "change anytime" reassurance | Add text on personality screen |
| 8 | Chat | Mock response text | Replace with loading indicator or "connect a brain" CTA |

### No fixes needed
All other labels, buttons, empty states, and interactions passed the Grandma Test.

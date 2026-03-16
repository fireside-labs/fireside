# Sprint 21 — "Finish the Install"

> **Goal:** The installer is the strong part. EXTEND IT to cover brain download + first connection. User should NEVER see a dashboard until their AI is ready to talk.
> **Timeline:** 1 day  
> **Source:** User test round 5 screenshots (2026-03-16 3:22 PM) — "this dashboard is low tier... the connection should be part of the install process"

---

## 🚨 BUGS FROM SCREENSHOTS

### B1: Ember companion image is broken
- Shows checkerboard (missing PNG) on dashboard
- Companion card renders but the image path is wrong
- Need to verify `/sprites/companion_fox.png` (or whatever species) exists and path resolves in Tauri

### B2: Chat input active with no brain connected
- User can type messages into a chat that goes nowhere
- "Offline mode — showing cached data" banner at top
- Chat input should be DISABLED until brain is installed + backend running
- Show: "Download a brain first to start chatting" placeholder instead

### B3: Tour says "Go to Brains" but Brains tab is locked
- Tour step 2 tells user to go to Brains
- But Brains has 🔒 icon — confusing
- Tour must UNLOCK the next step's tab, not just tell them to go there

---

## 🔑 CORE FIX: Extend the Installer

The installer currently does:  
1. Welcome → 2. System Check → 3. Choose Companion → 4. Name AI → 5. Install → 6. Done

**It should add:**  
**Step 5.5: Download Brain**
- "Downloading your AI brain — Llama 3.1 8B (4.6 GB)..."
- Real progress bar showing download %
- Can "Download Later" to skip (power users)
- If downloaded: brain loads on launch → dashboard shows WORKING chat
- If skipped: dashboard shows "Download brain to start chatting" with a big button

**Step 5.75: First Connection Test**
- Start backend, verify brain loads
- "Testing connection to your AI..."
- ✔ "Atlas is ready to chat!"
- THEN show dashboard — user arrives to a WORKING product

---

## 🎨 Freya (UI)

### F1: Add brain download step to InstallerWizard
- New step between install and success
- Shows model name + size + download progress bar
- "Download Later" button for skip
- Uses same cinematic styled as rest of installer

### F2: Add connection test step  
- After brain download: "Starting your AI..."
- Animated spinner in installer style
- ✔ "Atlas is ready!" → proceed to dashboard

### F3: Disable chat when no brain
- Chat page: if no brain downloaded → show "Download your brain to start talking"
- Big centered button → navigates to Brains page
- No chat input, no "Try asking" suggestions
- Only show chat UI once brain is confirmed

### F4: Fix Ember companion image
- Verify PNG paths resolve in Tauri WebView
- Dashboard companion card → use correct sprite path
- Fallback to emoji if sprite not found (never show checkerboard)

### F5: Tour must unlock tabs before directing there
- When tour says "Go to Brains" → Brains tab must be unlocked
- UNLOCKED_AT_STEP in GuidedTour.tsx must include the target href
- Tour step should auto-navigate or highlight the unlocked tab

### F6: Dashboard quality parity with installer
- Same glass cards, same amber glow, same typography
- Dashboard cards should feel like installer panels
- Consistent border-radius, padding, shadows, font weights

---

## 🔨 Thor (Backend)

### T1: Brain download command in Tauri
- `invoke("download_brain", { model: "llama-3.1-8b-q6", dest: "~/.fireside/models/" })`
- Returns progress events for the frontend progress bar
- Falls back to showing Brains page if download fails

### T2: Connection test command
- `invoke("test_connection")` — starts backend, sends test prompt, verifies response
- Returns success/failure for the installer UI

---

## 🛡️ Heimdall (Audit)

### H1: Fresh install end-to-end with brain download
- Clear state → install → brain downloads → connection test → dashboard
- Chat works immediately on dashboard
- No broken images, no offline banner

---

## ✅ Valkyrie (QA)

### V1: The "grandma test"
- Fresh install with zero prior knowledge
- Does the user EVER feel lost?
- Can they chat immediately after install?
- Is every image loading?
- Is every tour step achievable?

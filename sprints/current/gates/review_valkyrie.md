# Full Install-to-Dashboard UX Audit

**Date:** 2026-03-16
**Method:** Code walkthrough tracing every step a first-time user sees
**Build:** ✅ 27/27 pages, 0 errors

---

## Flow Map

```
OnboardingGate (Tauri detection, 10×200ms polling)
  → InstallerWizard (9 steps)
    0. Welcome → 1. System Check → 2. Companion → 3. Name AI
    → 4. Confirm → 5. Install → 6. Brain Download → 7. Connection Test → 8. Success
  → localStorage writes (11 keys)
  → onComplete() → OnboardingGate renders children
  → TourProvider polls for fireside_onboarded every 500ms
  → Dashboard (page.tsx) mounts
  → Tour bar appears at bottom
```

---

## 🔴 CRITICAL Issues

### 1. `fireside_companion` is missing fields → dashboard shows broken card
**Severity: HIGH** — Visible on first load

The installer writes:
```js
localStorage.setItem("fireside_companion", JSON.stringify({
  name: "Ember",
  species: "fox",
}));
```

But `page.tsx` reads:
```ts
interface CompanionState {
    species: string;
    name: string;
    owner: string;  // ← NEVER SET by installer
}
```

The `owner` field is never written. It doesn't break rendering, but it's a data contract mismatch.

**Fix:** Remove `owner` from `CompanionState` in page.tsx, or add it to the installer write (`owner: config.userName`).

---

### 2. Brain download "Download Later" skips to step 8, skipping connection test
**Severity: HIGH** — User flow gap

```tsx
// Step 6 — "Download Later" button
<button onClick={() => goTo(8)}>
  Download Later (power users)
</button>
```

This jumps to Success (step 8), skipping the connection test (step 7). So if a user skips download:
- No connection test is run
- They arrive at success screen saying "Fireside is live"
- Dashboard has no brain → shows "Download a brain"

This is **technically correct** but **emotionally dishonest** — the success screen celebrates, but the product isn't actually working. 

**Fix:** Skip to step 8 is fine, but change the success screen messaging when brain wasn't downloaded:
```
"Almost ready — download a brain from the Brains page to start chatting"
```

---

### 3. `fireside_model` is ALWAYS set in step 8 — even when download was skipped
**Severity: MEDIUM** — Silent data bug

```tsx
// Step 8 success button onClick:
localStorage.setItem("fireside_model", config.actualModel || "llama-3.1-8b-q6");
```

This runs regardless of whether the brain was actually downloaded. So `hasBrain` on the dashboard will be `true` even when no model exists. The user will see a chat input, type a message, and get an error.

**Fix:** Only set `fireside_model` in `startBrainDownload()` (which already does this on line 235). Remove it from the step 8 button handler.

---

## 🟡 MEDIUM Issues

### 4. Step 1 system check — VRAM not shown to user
**Severity: MEDIUM** — User can't verify recommendation

System check shows: OS ✅, RAM ✅, GPU ✅. But VRAM (the number that actually determines brain selection) is **never displayed**. The user sees "NVIDIA RTX 4090" but not "24GB VRAM."

**Fix:** Add a 4th check row: `{ label: "AI Memory (VRAM)", status: "ok", value: "24GB" }`

---

### 5. `showAdvanced` uses `(config as any)` — type unsafe
**Severity: LOW** — Code quality

The advanced model picker toggle uses `(config as any).showAdvanced` because `showAdvanced` isn't in `InstallerConfig`. This works but is a code smell.

**Fix:** Add `showAdvanced?: boolean` to `InstallerConfig`.

---

### 6. Tour step 3 (Chat) points to `/` — same as step 1 (Dashboard)
**Severity: MEDIUM** — Confusing tour

```tsx
const TOUR_STEPS = [
    { href: "/", label: "Dashboard", ... },
    { href: "/brains", label: "Brains", ... },
    { href: "/", label: "Chat", ... },  // ← SAME URL as step 1
];
```

Step 1 and Step 3 both go to `/`. The user navigates to Brains, comes back, and the tour says "Chat" but they're on the same page they started on. 

**Fix:** Since Chat IS the dashboard now, step 3 should just say "You're all set! Start chatting." and auto-complete, or be removed entirely (2-step tour: Dashboard → Brains → Done).

---

## 🟢 ACTUALLY GOOD

### Dashboard v2 is a massive improvement
The rewrite of `page.tsx` is excellent:
- **Ambient atmosphere** ported from installer (particles, warm glow, vignette)
- **Hero state** with companion center stage at 5x scale, floating pill suggestions, glowing input
- **Chat state** with animated message bubbles (`msgSlideIn`), typing indicator (3-dot bounce), companion avatar, auto-scroll
- **Two-state design** (hero → chat) creates progressive disclosure
- **Same typography** as installer (Inter 900, amber palette, `#F0DCC8`)
- **Same border-radius, shadows, and blur values** as installer

### Installer is production-quality
- 9-step flow with cinematic transitions
- Fire particles, vignette, amber glow
- Non-critical failure handling ("skipped — already set up")
- Brain download with progress bar + skip option
- Connection test with 3-state feedback

---

## Summary: 3 fixes needed before this is shippable

| # | Fix | Effort |
|---|-----|--------|
| 1 | Don't set `fireside_model` in step 8 if brain wasn't downloaded | 1 line delete |
| 2 | Show VRAM in system check | ~5 lines |
| 3 | Fix tour step 3 (Chat = Dashboard, same URL) | ~3 lines |

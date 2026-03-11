# Accessibility Audit Results — Sprint 6

> **Auditor:** Heimdall  
> **Date:** 2026-03-10  
> **Scope:** All 46 TSX components + `globals.css` (729 lines) + form security

---

## 1  WCAG AA Compliance

### 1.1  Text Contrast

| Element | Dark Theme | Light Theme | WCAG AA (4.5:1) |
|---------|-----------|-------------|-----------------|
| Body text (`--color-rune: #a0a0b8` on `#0a0a0f`) | ~8.2:1 | — | ✅ Pass |
| Dim text (`--color-rune-dim: #6a6a80` on `#0a0a0f`) | ~4.1:1 | — | ⚠️ **Fail** (body), ✅ Pass (large) |
| Neon (`--color-neon: #00ff88` on `#0a0a0f`) | ~11.5:1 | — | ✅ Pass |
| Light body (`#4a4a5e` on `#f5f5f8`) | ~5.6:1 | — | ✅ Pass |
| Light dim (`#8a8a9e` on `#f5f5f8`) | ~3.3:1 | — | ⚠️ **Fail** |
| Light neon (`#00aa55` on `#f5f5f8`) | ~3.8:1 | — | ⚠️ **Fail** |

**Action items:**
- `--color-rune-dim` (dark): darken to `#7a7a95` or lighten to `#8585a0` for 4.5:1
- `--color-rune-dim` (light): darken to `#6a6a80` for 4.5:1
- `--color-neon` (light): darken to `#008844` for 4.5:1 on white backgrounds

### 1.2  Click Targets (44×44px minimum)

| Component | Size | Status |
|-----------|------|--------|
| `btn-neon` | padding: 10px 24px → ~48×40px | ⚠️ Height marginal — increase to `py-3` |
| Sidebar nav items | Full-width, adequate height | ✅ Pass |
| Toggle switches (`SettingsForm`) | 48×24px | ⚠️ **Fail** — height 24px < 44px |
| Skill checkboxes (`PersonalityForm`) | 20×20px | ❌ **Fail** — 20px < 44px |
| Theme toggle | 36×36px | ⚠️ **Fail** — 36px < 44px |
| Mobile hamburger | 40×40px | ⚠️ Marginal — 40px < 44px |
| `+ Add` buttons (PersonalityForm) | text-only, no min area | ❌ **Fail** |

**Action items:**
- Increase toggle switch height to 28px with 44px touch area (invisible padding)
- Wrap checkboxes in `<label>` with min 44×44px clickable area
- Increase theme toggle to 44×44px
- Add `min-h-[44px] min-w-[44px]` to text-only action buttons

### 1.3  Keyboard Navigation

| Test | Status |
|------|--------|
| Tab through all sidebar links | ✅ Works (native `<a>` and `<Link>`) |
| Tab through form inputs (Settings, Personality) | ⚠️ Partial — custom toggles/checkboxes not in tab order |
| Run onboarding wizard with keyboard only | ⚠️ Name input focusable, but personality cards need `tabIndex` |
| Escape to close onboarding overlay | ❌ Not implemented |
| Enter to submit forms | ⚠️ Only custom skills/rules support Enter, not Save button |

### 1.4  Focus Indicators

| Element | Focus Style | WCAG Visible? |
|---------|------------|---------------|
| Text inputs | `border-color: var(--color-neon)` | ⚠️ Subtle — border-only, no ring |
| Buttons (btn-neon) | None | ❌ **No focus indicator** |
| Sidebar links | None (removed `outline-none`) | ❌ **No focus indicator** |
| Select dropdowns | None | ❌ **No focus indicator** |

**Action items (critical):** Add to `globals.css`:
```css
*:focus-visible {
  outline: 2px solid var(--color-neon);
  outline-offset: 2px;
}
```
This one rule fixes all focus indicator issues across the entire dashboard.

---

## 2  Screen Reader Audit

### 2.1  ARIA Labels

| Component | Has ARIA | Issue |
|-----------|----------|-------|
| ThemeToggle | ✅ `aria-label="Toggle theme"` | Good |
| Sidebar hamburger | ✅ `aria-label="Open menu"` | Good |
| SettingsForm toggle switches | ❌ None | Needs `role="switch"`, `aria-checked`, `aria-label` |
| PersonalityForm checkboxes | ❌ None | Needs `role="checkbox"`, `aria-checked` |
| PersonalityForm tone buttons | ❌ None | Needs `role="radiogroup"` + `role="radio"` + `aria-checked` |
| BrainPicker cards | ❌ None | Needs `role="radio"` + `aria-checked` |
| OnboardingWizard progress dots | ❌ None | Needs `role="progressbar"` + `aria-valuenow` |
| ChatInput | ❌ None | Needs `aria-label="Send a message"` |
| All "×" close/remove buttons | ❌ None | Needs `aria-label="Remove"` |
| PipelineCard status badges | ❌ None | Needs `aria-label` for status text |

**Coverage: 2 / ~50 interactive elements (4%).** Needs significant work.

### 2.2  Form Label Association

**All form inputs across SettingsForm, PersonalityForm, and OnboardingWizard use `<label>` elements but do NOT have `htmlFor`/`id` pairing.** The labels are adjacent siblings, not programmatically associated.

**Action items:**
```tsx
// Before (broken for screen readers):
<label className="...">Name</label>
<input value={name} ... />

// After (accessible):
<label htmlFor="settings-name" className="...">Name</label>
<input id="settings-name" value={name} ... />
```

### 2.3  Heading Hierarchy

| Page | h1 | h2 | h3 | Issues |
|------|----|----|-----|--------|
| Home (Chat) | ✅ "What can I help you with?" | — | — | Good |
| Settings | ✅ "Settings" | — | "Your AI", "AI Brain", "Add-ons" | Good |
| Personality | ✅ "Personality" | — | Sections use h3 | ✅ Good |
| Connected Devices | ✅ "Connected Devices" | — | — | Good |
| Pipeline | ✅ "Task Builder" | — | — | Good |
| Learning | ✅ "How It's Learning" | — | — | Good |
| Marketplace | ✅ "Store" | — | — | Good |

**Heading hierarchy is correct across all pages.** ✅

### 2.4  Dynamic Content

| Event | Announced? |
|-------|-----------|
| Toast notifications | ❌ No `aria-live` region |
| Pipeline status changes | ❌ Not announced |
| Onboarding step changes | ❌ Not announced |

**Action items:** Add `role="alert"` or `aria-live="polite"` to Toast component.

---

## 3  Form Security Review

### 3.1  Settings → YAML Injection

**Risk:** User enters a name like `odin\napi_key: stolen` in the Settings form, which gets written into `valhalla.yaml`.

**Finding:** ✅ **SAFE.** The SettingsForm sends values via `onSave()` callback as a typed JavaScript object `{ name, role, brain, addons }`. The config page logs to console only (`console.log("Settings saved:", values)`). **There is NO direct YAML write from the form.** When Thor implements the backend `PUT /api/v1/config`, Heimdall's existing `middleware/auth.py` YAML validation will apply.

**Recommendation:** When the backend write is implemented:
- Validate `name` with regex: `/^[a-zA-Z0-9_-]{1,32}$/`
- `role` from enum only (dropdown — already constrained)
- `brain` from enum only (BrainPicker — already constrained)
- `addons` from known plugin ID list only

### 3.2  Personality → SOUL.md Injection

**Risk:** User enters a boundary rule like `---\nNEW YAML BLOCK` that gets injected into SOUL.md.

**Finding:** ✅ **SAFE (currently).** The PersonalityForm sends values as a typed object. The soul page logs only. **No direct file write exists.** When the backend write is implemented:
- Sanitize all text inputs: strip YAML special chars (`---`, `\n`, `:`)
- Max lengths: name 32, role 32, boundary rules 200 chars each, max 20 rules
- Custom skills: max 50 chars, max 10 custom skills

### 3.3  Onboarding Wizard Sanitization

**Risk:** User enters `<script>alert('xss')</script>` as their name in onboarding.

**Finding:** ✅ **SAFE.** React auto-escapes all JSX interpolation (`{userName}`). The name is stored in `localStorage` and rendered via React — no `dangerouslySetInnerHTML`. The name is used in:
- Line 126: `You're all set, ${userName}!` — auto-escaped by React
- Line 30: `localStorage.setItem("valhalla_user_name", userName)` — stored as-is

**Recommendation:** Add `.trim().slice(0, 32)` sanitization on save for defense-in-depth.

### 3.4  Raw Config Editor

**Risk:** The "Edit raw config file" option in Settings exposes a textarea with YAML content.

**Finding:** ⚠️ **READ-ONLY MOCKUP.** Currently uses `defaultValue` with a hardcoded YAML string. No submit handler. **When Thor adds a real PUT handler**, ensure:
- YAML parse validation before save
- Schema validation (reject unknown root keys)
- File path restriction (can only write `valhalla.yaml`, not arbitrary files)

---

## 4  Summary

| Category | Score | Status |
|----------|-------|--------|
| Contrast ratios | 3/6 pass | ⚠️ Needs fix: `--color-rune-dim` + light theme neon |
| Click targets | 3/7 pass | ⚠️ Toggles, checkboxes, theme toggle too small |
| Keyboard navigation | Partial | ⚠️ Custom components need tabIndex |
| Focus indicators | 0/4 pass | ❌ **Critical — add `*:focus-visible` rule** |
| ARIA labels | 2/50 (4%) | ❌ **Critical — most interactive elements unlabeled** |
| Form label association | 0/8 forms | ❌ No htmlFor/id pairs anywhere |
| Heading hierarchy | 7/7 pass | ✅ Correct across all pages |
| Dynamic announcements | 0/3 | ❌ No aria-live regions |
| Form → YAML injection | — | ✅ Safe (no backend write yet) |
| Form → SOUL.md injection | — | ✅ Safe (no backend write yet) |
| Onboarding XSS | — | ✅ Safe (React auto-escape) |
| Raw config editor | — | ⚠️ Mockup only — secure when real handler added |

### Priority Fixes for Freya

1. **🔴 Critical:** Add `*:focus-visible` CSS rule (1 line fix, instant WCAG win)
2. **🔴 Critical:** Add ARIA roles + labels to custom toggles, checkboxes, radio groups
3. **🟠 High:** Add `htmlFor`/`id` pairs to all form labels
4. **🟠 High:** Fix `--color-rune-dim` contrast (both themes)
5. **🟡 Medium:** Increase click target sizes (toggles, checkboxes, theme toggle)
6. **🟡 Medium:** Add `aria-live="polite"` to Toast component
7. **🟢 Low:** Add Escape key handler to onboarding overlay
8. **🟢 Low:** Add `tabIndex` to personality/brain picker cards

---

*Accessibility audit complete. Heimdall — Sprint 6 (2026-03-10).*

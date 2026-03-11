# Store UX Review

> **Status:** Store expansion (themes/avatars/voices tabs) not yet built. This reviews the existing marketplace + the spec for expansion.

---

## Current Marketplace: ✅ Works for Agents

The Sprint 5 marketplace handles agent browsing, detail pages, publishing, and reviews. That's shippable as-is for agent-only marketplace.

---

## Expanded Store Spec Review

Sprint 9 spec adds 5 tabs: **Agents | Themes | Avatars | Voices | Personalities**

### Buying Flow Analysis

**Target:** < 3 clicks from browse to purchased.

```
Browse → Click item → Buy → Done
  1         2          3      ✅
```

| Step | What Happens | UX Risk |
|---|---|---|
| 1. Browse | Tabs filter by type, cards show preview + price | Cards must be visually distinct per type |
| 2. Click item | Detail page: full preview, price, reviews, creator | Previews must be good enough to sell (see below) |
| 3. Buy | Stripe checkout (hosted page) → redirect back | Redirect adds friction — consider in-app checkout |

**Recommendation:** For items under $5, use Stripe's Payment Links or embedded checkout to avoid a full page redirect. The fewer times the user leaves the app, the higher the conversion.

---

## Preview Quality (Sell-or-Skip Moment)

| Item Type | Preview Needed | How Good? |
|---|---|---|
| Agent | Personality description + sample conversation | ✅ "Try Before Buy" from Sprint 5 |
| Theme | Screenshot of Guild Hall in that theme | ⚠️ Need static renders |
| Avatar | Visual preview of the sprite at profile size | ✅ SVGs render inline |
| Voice | 5-second audio sample | ⚠️ Need audio player component |
| Personality | Description + sample responses at each slider setting | ⚠️ Need text examples |

**Themes and voices are hardest to sell without previews.** A theme card with just a title and description won't convert. Each theme needs a screenshot of the Guild Hall rendered in that theme.

---

## Seller Onboarding

**Flow:** Creator wants to sell → "Sell your creations" → Stripe Connect OAuth → Back to seller dashboard.

| Step | What's Needed | Status |
|---|---|---|
| 1. "Sell" button | Visible on Store page | ❌ Not built |
| 2. Stripe Connect | OAuth flow, collect bank details | ❌ Stripe handler not built |
| 3. Submission | Upload agent/theme/voice + set price | ❌ Wizard not built |
| 4. Review | Heimdall scans for malicious content | ✅ Spec'd (SVG sanitization, prompt injection check) |
| 5. Published | Item appears in store | ✅ Uses existing marketplace publish flow |

**Key concern:** Stripe Connect requires business registration in many countries. This could be a blocker for casual creators. **Alternative:** Start with free items only (community sharing), add payments when there's demand.

---

## Pricing Display

| Rule | Why |
|---|---|
| Show price on card (not just detail page) | Users filter by affordability before clicking |
| Show "FREE" prominently for free items | Free items drive traffic and trust |
| Platform fee visible to sellers (30%) | Transparency prevents surprises |
| No hidden fees for buyers | What you see is what you pay |

---

## Launch Recommendation

### 🚫 Don't launch with payments.

The store needs:
1. Enough items to browse (< 10 items = empty store = bad first impression)
2. Stripe integration complete + tested
3. Seller onboarding flow that doesn't require a business license

**Instead:** Launch with a community store (all free). Let creators share agents, themes, voices for free. When there are 50+ items and demand for paid content, enable payments.

This follows the Obsidian/VS Code playbook: extensions are free and community-driven first. Paid marketplace comes later when the ecosystem is healthy.

---

## Recommendations

| Priority | Fix |
|---|---|
| Must | Launch store as free/community only |
| Must | Add theme screenshots to preview cards |
| Should | Add audio player for voice previews |
| Should | Add sample conversation for personality presets |
| Later | Stripe payments when 50+ items exist |
| Later | Seller dashboard with earnings charts |

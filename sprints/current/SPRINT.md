# Sprint 18 — "Pixel Perfect"

> **Goal:** Replace all emoji/placeholder art with PREMIUM Game Dev Story-quality pixel sprites. 1-2 levels above Claude Office. These environment packs and skins are the commercialization strategy — this is the product people BUY in the store.
> **Timeline:** 2 days
> **Source:** User feedback + Claude Office / Game Dev Story / Kairosoft research

---

## How Claude Office & Game Dev Story Do It

The technique is well-documented:

1. **Tiny sprite sheets** — Characters are 16×16 or 32×32 PNG images with 2-4 animation frames per action (idle, walking, working, sleeping)
2. **`image-rendering: pixelated`** — THE critical CSS property. Prevents browser anti-aliasing when you scale up small sprites. Without it, pixel art looks blurry at 2x-4x.
3. **Limited color palette** — 8-16 colors per character max. No gradients. Every pixel is deliberate.
4. **NO anti-aliasing** — Hard pixel edges only. This is what makes it feel retro vs generic.
5. **Sprite sheet animation** — Single PNG with all frames laid out horizontally. CSS `background-position` shifts to animate. `steps()` timing function for frame-by-frame.
6. **Top-down perspective** — Characters viewed at ~45° angle (3/4 view), like Game Dev Story.

### CSS Pattern
```css
.sprite {
  image-rendering: pixelated;
  image-rendering: crisp-edges; /* Firefox fallback */
  width: 64px;   /* display size (4x upscale of 16px source) */
  height: 64px;
  background: url('/sprites/agent.png') no-repeat;
  background-size: 256px 64px; /* 4 frames × 64px */
  animation: walk 0.6s steps(4) infinite;
}
@keyframes walk {
  to { background-position: -256px 0; }
}
```

### Why We Go ABOVE Claude Office
Claude Office = functional. Fireside = **sellable**. Environment packs and character skins are the revenue model. Every sprite, every animation, every particle effect is a potential store item. Quality must be premium.

---

## 🎨 Freya (Art + UI)

### F1: Create sprite sheet system
- `dashboard/public/sprites/` directory for all sprite PNGs
- `SpriteCharacter.tsx` component that renders a sprite with:
  - `image-rendering: pixelated` (crisp scaling)
  - `background-position` animation (sprite sheet frames)
  - `steps()` CSS timing for frame stepping
  - Props: `sprite`, `action`, `scale`, `direction`
- Support actions: idle, walk, work, sleep, chat

### F2: Agent sprites (48×48 base — premium detail)
- Generate sprite sheets for each agent style:
  - `analytical` — glasses, neat hair, focused pose
  - `creative` — beret, paint splatter, expressive
  - `direct` — military cut, sharp features
  - `warm` — soft features, scarf, gentle
- 4 frames per action × 6 actions = 24 frames per sheet
- Use `generate_image` tool to create base sprites, then hand-clean

### F3: Companion sprites (32×32 base)
- All 6 species: cat, dog, penguin, fox, owl, dragon
- Each with: idle (2 frames), walking (4 frames), sleeping (2 frames), happy (2 frames)
- Pixel art style matching agents — same palette approach

### F4: 🔥 Kairosoft Status Effects (Game Dev Story "On a Roll")
- **Status overlay sprites** that float above characters:
  - 🔥 **On a Roll** flame — AI processing fast / high quality responses
  - ⚡ **Spark** — learning something new / training
  - 💤 **Zzz** bubble — agent idle / sleeping
  - 😰 **Sweat drops** — VRAM maxed out / struggling
  - 🎉 **Celebration** — task completed successfully
  - 💀 **Burned out** — error state / crash recovery
  - 💡 **Lightbulb** — generating ideas / brainstorming
  - ❤️ **Heart** — companion affection level high
- Animated overlays (3-4 frames each), positioned above character head
- Status driven by actual backend state (CPU/VRAM load, task status, uptime)
- **Premium variants** for the store: golden flame, lightning bolt, rainbow celebration

### F5: Guild Hall environment sprites
- Fireplace (animated, 4 frames flickering + ember particles)
- Desk/workstation with tiny monitor glow
- Bookshelf (filled based on memory/knowledge count)
- Cauldron (crucible mode — bubbling animation)
- Floor tiles / wood planks as tileable patterns
- Window with animated light rays (day/night shift)

### F6: Parallax depth layers
- **Background** — walls, windows, decorations (moves slow)
- **Midground** — characters, furniture (static)
- **Foreground** — fire particles, table edges, shadows (moves fast)
- Subtle parallax shift on mouse hover for depth illusion

### F7: Particle systems (CSS-only)
- Fire embers rising from fireplace
- Dust motes floating in light rays
- Theme-specific: snow (space station), cherry blossoms (garden), bubbles (alchemist)

### F8: Replace AvatarSprite.tsx with real sprites
- Current `AvatarSprite.tsx` draws CSS rectangles
- Replace with `SpriteCharacter.tsx` using actual PNG sheets
- Scale: 3x (48px source → 144px display in guild hall)
- Smaller scale for sidebar/chat avatars (2x = 96px)

### F9: Apply `image-rendering: pixelated` globally
- Add to `globals.css`:
  ```css
  .sprite, [data-sprite] {
    image-rendering: pixelated;
    image-rendering: crisp-edges;
  }
  ```
- Ensure all scaled pixel art uses this — no blur

### F10: Environment pack structure (store-ready)
- Each pack = folder with: `manifest.json` + sprite PNGs + palette + particle config
- Default free pack: "Norse Hall" (ships with app)
- Structure ready for future paid packs:
  - 🚀 Space Station
  - 🌸 Japanese Garden
  - 🏴‍☠️ Pirate Ship
  - 🧪 Alchemist Lab

---

## 🔨 Thor (Backend)

### T1: Serve sprite assets from dashboard/public
- Ensure `/sprites/` directory is included in Next.js static export
- Verify sprites load in Tauri WebView (no CSP blocking)
- Add `img-src 'self' data: blob:` already in CSP (verified)

### T2: Status effect API
- `/api/v1/status/agent` returns current agent state
- Map to status effects: `{ status: "on_a_roll" | "idle" | "working" | "error" | "learning" }`
- Guild Hall polls this to update character overlays

---

## 🛡️ Heimdall (Audit)

### H1: Pixel quality audit
- Verify NO anti-aliasing on any sprite at any scale
- Check all sprites render sharp at 2x, 3x, 4x
- Verify sprite sheet alignment (no sub-pixel drift)
- Check performance: sprite animations + particles at 60fps

### H2: Store pack structure audit
- Verify manifest.json schema is extensible
- Verify pack loading doesn't break if pack is missing assets

---

## ✅ Valkyrie (QA)

### V1: Visual comparison test
- Screenshot Guild Hall before/after
- Verify agents animate correctly (idle → work → chat)
- Verify companions animate (idle → walk → sleep → happy)
- Verify status effects appear/disappear based on state
- Check all 6 species × 4 agent styles render correctly
- Test at different window sizes

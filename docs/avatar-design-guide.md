# Avatar Design Guide

> **Design philosophy:** Avatars should be charming, inclusive, and tiny. They appear in the sidebar (24px), profile page (120px), and guild hall (48px). They must be readable at every size.

---

## Format

- **Pixel style** (default): 32×32 grid, 4x scaled for display. Crisp edges, no anti-aliasing.
- **Minimal style**: SVG with 2px stroke, flat fills, no gradients.
- **Emoji style**: Single emoji character. Simplest option.

All avatars are pure SVG or CSS — **zero GPU, zero VRAM, ~5KB per avatar.** No images to download.

---

## Grid Specification (Pixel Style)

```
Canvas: 32×32 pixels
Stroke: none (filled pixels only)
Display sizes:
  Sidebar:     24×24 (0.75x)
  Guild Hall:  48×48 (1.5x)
  Profile:     128×128 (4x)
  Tooltip:     64×64 (2x)

Rendering: image-rendering: pixelated (crisp upscale)
```

---

## Color Palette

### Norse / Valhalla Theme (Default)

| Swatch | Hex | Use |
|---|---|---|
| 🟤 | `#8B4513` | Default hair (brown) |
| ⬛ | `#1A1A2E` | Outline / dark accent |
| 🟡 | `#D4A843` | Gold accents / crown |
| 🔴 | `#C0392B` | Warrior outfit |
| 🔵 | `#2E86C1` | Scholar outfit |
| 🟢 | `#27AE60` | Guardian outfit |
| 🟣 | `#8E44AD` | Artist outfit |
| ⬜ | `#ECF0F1` | Light accents |

### Hair Colors

| Color | Hex | Notes |
|---|---|---|
| Brown | `#8B4513` | Default |
| Black | `#1C1C1C` | — |
| Blonde | `#D4A843` | — |
| Red | `#B74223` | — |
| Gray | `#95A5A6` | — |
| White | `#ECF0F1` | — |
| Blue | `#3498DB` | Creative option |
| Pink | `#E91E63` | Creative option |
| Green | `#27AE60` | Creative option |
| Purple | `#8E44AD` | Creative option |

### Skin Tones

Based on the Fitzpatrick scale. Always available, never default-gated.

| Tone | Hex | Name |
|---|---|---|
| 1 | `#FDEBD0` | Light |
| 2 | `#F5CBA7` | Light-Medium |
| 3 | `#E0AC69` | Medium |
| 4 | `#C68642` | Medium-Dark |
| 5 | `#8D5524` | Dark |
| 6 | `#5C3D2E` | Deep |

---

## Outfits

Outfits map to agent roles. Users can override.

| Outfit | Emoji | Default For | Visual Description |
|---|---|---|---|
| ⚔️ Warrior | ⚔️ | Thor (Builder) | Chest plate, shoulder pads, hammer |
| 🧑‍💻 Developer | 💻 | Freya (Frontend) | Hoodie, headphones, laptop |
| 🎨 Artist | 🎨 | — | Beret, paint splash on smock |
| 🛡️ Guardian | 🛡️ | Heimdall (Security) | Shield, helmet, cape |
| 📚 Scholar | 📚 | — | Robes, book, quill |
| 👑 Crown | 👑 | Valkyrie (Strategy) | Crown, ornate cloak |

### Outfit-Role Mapping

| Agent Role | Suggested Outfit | Rationale |
|---|---|---|
| orchestrator / Main AI | 👑 Crown | The leader |
| backend / Helper | ⚔️ Warrior | The builder |
| memory / Memory Assistant | 📚 Scholar | The librarian |
| security / Security Guard | 🛡️ Guardian | The protector |
| Custom agent | 🧑‍💻 Developer | Neutral default |

---

## Accessories

| Accessory | Notes |
|---|---|
| None | Default |
| 👓 Glasses | Slightly oversized for pixel readability |
| 🎧 Headphones | On ears, visible at 48px |
| 🎩 Hat | Replaces hair top pixels |
| ⚡ Aura | Glowing outline (achievement-unlocked only) |

---

## Inclusivity Guidelines

### Required
- **All skin tones available equally.** No tone is default — first-time setup prompts the user to choose.
- **All hair colors available to all skin tones.** No restrictive combinations.
- **Gender-neutral base.** The pixel sprite has no gendered features (no exaggerated body shapes). Hair and outfit provide expression.
- **No cultural stereotypes.** Outfits reference fantasy archetypes (warrior, scholar), not real-world cultures.
- **Accessibility in naming.** Skin tone picker uses color swatches, not names like "dark" or "light." Screen readers get Fitzpatrick scale numbers.

### Recommended
- **Disability representation.** Add optional accessories: wheelchair (replaces standing sprite), hearing aid (small pixel on ear), service animal (small companion sprite).
- **Age range.** Hair color includes gray/white. No outfit is age-locked.
- **Testing.** Show the avatar creator to 5 people of different backgrounds. If anyone says "I can't make one that looks like me," add options.

---

## Size Guidelines

| Context | Size | What's Visible |
|---|---|---|
| Sidebar list | 24×24px | Shape + outfit color only. No detail. |
| Guild Hall sprite | 48×48px | Hair, skin, outfit, accessory visible. Name label required below. |
| Tooltip / hover | 64×64px | All details clear. |
| Profile page | 128×128px | Everything crisp at 4x. Border/frame around sprite. |
| Achievement toast | 32×32px | Inline with text. Outfit color + shape. |

### Rule: If you can't tell what it is at sidebar size (24px), simplify the design.

---

## Animation Guidelines (Guild Hall)

Sprites animate with CSS keyframes. No JavaScript animation loops.

| State | Animation | Duration |
|---|---|---|
| Idle | Gentle bob (2px up/down) | 3s ease-in-out loop |
| Working (typing) | Arms move, subtle head bob | 1.5s loop |
| Walking | 4-frame walk cycle | 0.8s per cross |
| Sleeping | ZZZ particles float up | 4s loop |
| Celebrating (level up) | Jump + sparkle particles | 2s, then idle |
| Talking (chat) | Speech bubble pulses | 2s loop |

### Performance rules
- Max 6 agents animated simultaneously
- Use `will-change: transform` on moving elements
- Pause animations when tab/window is not visible (`document.hidden`)
- No canvas, no WebGL, no requestAnimationFrame — pure CSS

---

## File Structure

```
assets/
  sprites/
    pixel-base.svg          # Base 32×32 template
    hair/                   # 6 hair styles × 10 colors
    outfits/                # 6 outfits
    accessories/            # 4 accessories
  themes/
    valhalla/               # Scene backgrounds + furniture SVGs
    office/                 # Scene backgrounds + furniture SVGs
```

Each SVG should be:
- `<svg viewBox="0 0 32 32">` for pixel sprites
- Named: `{part}-{variant}.svg` (e.g., `hair-short.svg`, `outfit-warrior.svg`)
- Under 2KB per file
- No embedded raster images
- No external font dependencies

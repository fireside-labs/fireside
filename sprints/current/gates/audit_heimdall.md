# 🛡️ Heimdall Security Audit — Sprint 18 (Pixel Perfect)

**Sprint:** Pixel Perfect
**Auditor:** Heimdall (Security)
**Date:** 2026-03-16
**Verdict:** ✅ PASS — Zero HIGH, Zero MEDIUM, 1 LOW.

---

## H1 — Pixel Quality Audit ✅

### Anti-Aliasing Prevention

| Layer | Implementation | Verified |
|---|---|---|
| Component inline | `imageRendering: "pixelated"` on `SpriteCharacter.tsx:219` | ✅ |
| Global CSS | `.sprite, [data-sprite] { image-rendering: pixelated; image-rendering: crisp-edges; }` in `globals.css:854-855` | ✅ |
| Firefox fallback | `crisp-edges` keyword present | ✅ |

### Sprite Sheet Animation

| Check | Result |
|---|---|
| `steps(N)` CSS timing | ✅ `animation: ${animName} ${speed}s steps(${frames}) infinite` (line 220) |
| Frame alignment | ✅ `backgroundPosition` calculated from `row * frameHeight * scale` — integer math, no sub-pixel drift |
| Scale integrity | ✅ Display size = `frameWidth × scale` — always integer pixels |
| `background-size` | ✅ `sheetWidth = frameWidth * frames * scale` — matches sheet dimensions |

### Sprite Asset Summary

| Category | Sheets | Base Size | Frames/Action | Actions |
|---|---|---|---|---|
| Agents | 4 (analytical, creative, direct, warm) | 48×48 | 2-4 | 6 (idle, walk, work, sleep, chat, happy) |
| Companions | 6 (cat, dog, penguin, fox, owl, dragon) | 32×32 | 2-4 | 4 (idle, walk, sleep, happy) |
| Environment | 3 (fireplace, desk, bookshelf) | Varies | — | — |

### Graceful Fallback
`SpriteOrEmoji` (line 231-262) renders emoji under sprite layer — if PNG fails to load, emoji remains visible. ✅

---

## H2 — Store Pack Structure Audit ✅

### Manifest Schema

All 4 packs use consistent schema:

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "version": "semver",
  "price": "number (cents)",
  "tier": "free | premium",
  "author": "string",
  "assets": { "key": "filename.png" },
  "palette": { "wall": "#hex", "floor": "#hex", "accent": "#hex", "glow": "#hex" },
  "particles": { "embers": bool, "dust": bool, ... }
}
```

### Pack Inventory

| Pack | Price | Tier | Assets | Particles |
|---|---|---|---|---|
| norse-hall | Free | free | 5 (fireplace, desk, bookshelf, floor, window) | embers, dust |
| space-station | $2.99 | premium | 5 (console, viewport, cryo, hologram, reactor) | dust, sparks |
| japanese-garden | $2.99 | premium | — | — |
| anime-cafe | $2.99 | premium | — | — |

### Extensibility Check

| Check | Result |
|---|---|
| Extra fields in particles (e.g. `sparks`) | ✅ Space-station adds `sparks: true` — won't break readers that only check known keys |
| Missing assets | ⚠️ Pack references assets like `command_console.png` but PNGs don't exist yet for premium packs. **Not a security risk** — `SpriteOrEmoji` handles this gracefully with emoji fallback |
| `futurePacks[]` in norse-hall | ✅ Informational only — no code reads this for loading |

### 🟢 LOW — Premium pack asset PNGs don't exist yet

Space-station, japanese-garden, anime-cafe manifests reference PNG files that haven't been created yet. This is expected for v1 (placeholders for store), but the pack loader should handle missing files gracefully.

---

## New Endpoint: `GET /api/v1/status/agent` ✅

| Check | Result |
|---|---|
| Process enumeration | ✅ Uses `psutil.process_iter` with exception handling for `NoSuchProcess`/`AccessDenied` |
| LLM detection | ✅ Checks process names for `llama`, `ollama`, `vllm`, `mlx` |
| CPU measurement | ✅ `psutil.cpu_percent(interval=0.1)` — short interval, non-blocking |
| State mapping | ✅ Clear thresholds: CPU>50+LLM→on_a_roll, CPU>10+LLM→working, mem>90→error |
| No mutation | ✅ Read-only endpoint |

---

## Findings Summary

| Severity | Finding | Action |
|---|---|---|
| 🟢 **LOW** | Premium pack PNGs don't exist yet | Expected — create assets before selling packs |

## Cumulative Posture (Sprints 1-18)

| Metric | Value |
|---|---|
| Total tests | 501 |
| Open HIGHs | 0 |
| Open MEDIUMs | 3 (S11 network-status, S14 brains-SSRF, S14 nodes-auth) |
| Open LOWs | ~3 |

— Heimdall 🛡️

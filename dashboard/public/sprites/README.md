# Fireside Sprites

This directory contains all pixel art sprite sheets for the Fireside dashboard.

## Structure

```
sprites/
├── agents/        # Agent character sprites (48×48 base)
│   ├── analytical.png
│   ├── creative.png
│   ├── direct.png
│   └── warm.png
├── companions/    # Companion sprites (32×32 base)
│   ├── cat.png
│   ├── dog.png
│   ├── penguin.png
│   ├── fox.png
│   ├── owl.png
│   └── dragon.png
├── effects/       # Status effect overlays
│   ├── on_a_roll.png
│   ├── spark.png
│   ├── zzz.png
│   ├── sweat.png
│   ├── celebration.png
│   └── lightbulb.png
├── environment/   # Guild Hall environment tiles
│   ├── fireplace.png
│   ├── desk.png
│   ├── bookshelf.png
│   └── floor.png
└── packs/         # Store environment packs
    └── norse-hall/
        └── manifest.json
```

## Rendering Rules

- All sprites use `image-rendering: pixelated` (no anti-aliasing)
- Base sizes: agents 48×48, companions 32×32, effects 16×16
- Display at 2x-4x scale via CSS
- Animation via `background-position` + `steps()` timing

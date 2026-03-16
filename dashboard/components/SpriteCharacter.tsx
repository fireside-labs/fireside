"use client";

/**
 * 🎮 SpriteCharacter — Sprint 18 F1.
 *
 * Renders a pixel-art sprite sheet with frame-by-frame animation.
 * Uses `image-rendering: pixelated` for crisp upscaling.
 * CSS `steps()` timing for authentic retro feel.
 */
import { useMemo } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SpriteAction = "idle" | "walk" | "work" | "sleep" | "chat" | "happy";

export interface SpriteSheetConfig {
    /** URL to the sprite sheet PNG (relative to /public) */
    src: string;
    /** Width of a single frame in the source sheet (px) */
    frameWidth: number;
    /** Height of a single frame in the source sheet (px) */
    frameHeight: number;
    /** Map of action → { row, frames, speed } */
    actions: Record<string, { row: number; frames: number; speed?: number }>;
}

export interface SpriteCharacterProps {
    /** Sprite sheet configuration */
    sheet: SpriteSheetConfig;
    /** Current action to animate */
    action?: SpriteAction;
    /** Display scale multiplier (e.g. 3 = 3x base size) */
    scale?: number;
    /** Flip horizontally (face left) */
    flipX?: boolean;
    /** Additional CSS class */
    className?: string;
    /** Click handler */
    onClick?: () => void;
}

// ---------------------------------------------------------------------------
// Pre-built sprite sheet configs
// ---------------------------------------------------------------------------

/** Agent sprite sheets — 48×48 base, 6 actions × 4 frames */
export const AGENT_SHEETS: Record<string, SpriteSheetConfig> = {
    analytical: {
        src: "/sprites/agent_analytical.png",
        frameWidth: 48, frameHeight: 48,
        actions: {
            idle: { row: 0, frames: 4, speed: 1.2 },
            walk: { row: 1, frames: 4, speed: 0.6 },
            work: { row: 2, frames: 4, speed: 0.8 },
            sleep: { row: 3, frames: 2, speed: 2.0 },
            chat: { row: 4, frames: 4, speed: 0.8 },
            happy: { row: 5, frames: 2, speed: 0.6 },
        },
    },
    creative: {
        src: "/sprites/agent_creative.png",
        frameWidth: 48, frameHeight: 48,
        actions: {
            idle: { row: 0, frames: 4, speed: 1.2 },
            walk: { row: 1, frames: 4, speed: 0.6 },
            work: { row: 2, frames: 4, speed: 0.8 },
            sleep: { row: 3, frames: 2, speed: 2.0 },
            chat: { row: 4, frames: 4, speed: 0.8 },
            happy: { row: 5, frames: 2, speed: 0.6 },
        },
    },
    direct: {
        src: "/sprites/agent_direct.png",
        frameWidth: 48, frameHeight: 48,
        actions: {
            idle: { row: 0, frames: 4, speed: 1.2 },
            walk: { row: 1, frames: 4, speed: 0.6 },
            work: { row: 2, frames: 4, speed: 0.8 },
            sleep: { row: 3, frames: 2, speed: 2.0 },
            chat: { row: 4, frames: 4, speed: 0.8 },
            happy: { row: 5, frames: 2, speed: 0.6 },
        },
    },
    warm: {
        src: "/sprites/agent_warm.png",
        frameWidth: 48, frameHeight: 48,
        actions: {
            idle: { row: 0, frames: 4, speed: 1.2 },
            walk: { row: 1, frames: 4, speed: 0.6 },
            work: { row: 2, frames: 4, speed: 0.8 },
            sleep: { row: 3, frames: 2, speed: 2.0 },
            chat: { row: 4, frames: 4, speed: 0.8 },
            happy: { row: 5, frames: 2, speed: 0.6 },
        },
    },
};

/** Companion sprite sheets — 32×32 base, 4 actions */
export const COMPANION_SHEETS: Record<string, SpriteSheetConfig> = {
    cat: {
        src: "/sprites/companion_cat.png",
        frameWidth: 32, frameHeight: 32,
        actions: {
            idle: { row: 0, frames: 2, speed: 1.5 },
            walk: { row: 1, frames: 4, speed: 0.5 },
            sleep: { row: 2, frames: 2, speed: 2.5 },
            happy: { row: 3, frames: 2, speed: 0.6 },
        },
    },
    dog: {
        src: "/sprites/companion_dog.png",
        frameWidth: 32, frameHeight: 32,
        actions: {
            idle: { row: 0, frames: 2, speed: 1.5 },
            walk: { row: 1, frames: 4, speed: 0.5 },
            sleep: { row: 2, frames: 2, speed: 2.5 },
            happy: { row: 3, frames: 2, speed: 0.6 },
        },
    },
    penguin: {
        src: "/sprites/companion_penguin.png",
        frameWidth: 32, frameHeight: 32,
        actions: {
            idle: { row: 0, frames: 2, speed: 1.5 },
            walk: { row: 1, frames: 4, speed: 0.7 },
            sleep: { row: 2, frames: 2, speed: 2.5 },
            happy: { row: 3, frames: 2, speed: 0.6 },
        },
    },
    fox: {
        src: "/sprites/companion_fox.png",
        frameWidth: 32, frameHeight: 32,
        actions: {
            idle: { row: 0, frames: 2, speed: 1.5 },
            walk: { row: 1, frames: 4, speed: 0.5 },
            sleep: { row: 2, frames: 2, speed: 2.5 },
            happy: { row: 3, frames: 2, speed: 0.6 },
        },
    },
    owl: {
        src: "/sprites/companion_owl.png",
        frameWidth: 32, frameHeight: 32,
        actions: {
            idle: { row: 0, frames: 2, speed: 1.8 },
            walk: { row: 1, frames: 4, speed: 0.7 },
            sleep: { row: 2, frames: 2, speed: 2.5 },
            happy: { row: 3, frames: 2, speed: 0.6 },
        },
    },
    dragon: {
        src: "/sprites/companion_dragon.png",
        frameWidth: 32, frameHeight: 32,
        actions: {
            idle: { row: 0, frames: 2, speed: 1.5 },
            walk: { row: 1, frames: 4, speed: 0.6 },
            sleep: { row: 2, frames: 2, speed: 2.5 },
            happy: { row: 3, frames: 2, speed: 0.6 },
        },
    },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SpriteCharacter({
    sheet,
    action = "idle",
    scale = 3,
    flipX = false,
    className = "",
    onClick,
}: SpriteCharacterProps) {
    const actionConfig = sheet.actions[action] || sheet.actions.idle;
    const { row, frames, speed = 1.0 } = actionConfig;

    const displayWidth = sheet.frameWidth * scale;
    const displayHeight = sheet.frameHeight * scale;
    const sheetWidth = sheet.frameWidth * frames * scale;

    // Generate unique animation name based on sheet + action
    const animName = useMemo(() => {
        const id = `sprite_${sheet.src.replace(/[^a-z0-9]/gi, '_')}_${action}`;
        return id;
    }, [sheet.src, action]);

    // Build CSS keyframes for this specific animation
    const totalSheetWidth = sheet.frameWidth * frames;
    const keyframesCSS = `
        @keyframes ${animName} {
            to { background-position: -${totalSheetWidth * scale}px ${-row * sheet.frameHeight * scale}px; }
        }
    `;

    return (
        <div
            className={`sprite ${className}`}
            onClick={onClick}
            style={{
                width: displayWidth,
                height: displayHeight,
                position: "relative",
                cursor: onClick ? "pointer" : undefined,
                transform: flipX ? "scaleX(-1)" : undefined,
            }}
        >
            <style>{keyframesCSS}</style>
            <div
                data-sprite
                style={{
                    width: displayWidth,
                    height: displayHeight,
                    backgroundImage: `url(${sheet.src})`,
                    backgroundSize: `${sheetWidth}px auto`,
                    backgroundPosition: `0px ${-row * sheet.frameHeight * scale}px`,
                    backgroundRepeat: "no-repeat",
                    imageRendering: "pixelated",
                    animation: `${animName} ${speed}s steps(${frames}) infinite`,
                }}
            />
        </div>
    );
}

/**
 * Fallback: renders an emoji placeholder when sprite PNG isn't available yet.
 * This allows us to progressively replace placeholders with real sprites.
 */
export function SpriteOrEmoji({
    sheet,
    fallbackEmoji,
    action = "idle",
    scale = 3,
    flipX = false,
    className = "",
}: SpriteCharacterProps & { fallbackEmoji: string }) {
    // Check if sprite PNG exists by attempting to render it
    // In production, we'd do an actual existence check; for now, 
    // we render the sprite and show emoji as CSS fallback
    return (
        <div className={`relative ${className}`} style={{ width: sheet.frameWidth * scale, height: sheet.frameHeight * scale }}>
            {/* Emoji fallback layer */}
            <div
                className="absolute inset-0 flex items-center justify-center"
                style={{ fontSize: sheet.frameWidth * scale * 0.6, zIndex: 0 }}
            >
                {fallbackEmoji}
            </div>
            {/* Sprite layer (will cover emoji when PNG loads) */}
            <div className="absolute inset-0 z-10">
                <SpriteCharacter
                    sheet={sheet}
                    action={action}
                    scale={scale}
                    flipX={flipX}
                />
            </div>
        </div>
    );
}

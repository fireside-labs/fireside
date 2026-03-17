"use client";

/**
 * 🎮 SpriteCharacter — Sprint 18+19 Fix.
 *
 * Renders pixel-art character images with CSS animation.
 * Uses `image-rendering: pixelated` + `<img>` for AI-generated PNGs.
 * CSS breathing/bob animation for life-like idle feel.
 *
 * NOTE: The AI-generated PNGs are full illustrations, not proper
 * sprite sheets. This component renders them as fixed-size images
 * with CSS animations instead of sprite sheet frame-stepping.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SpriteAction = "idle" | "walk" | "work" | "sleep" | "chat" | "happy";

export interface SpriteSheetConfig {
    /** URL to the sprite PNG (relative to /public) */
    src: string;
    /** Display size in pixels (the image will be forced to this size) */
    frameWidth: number;
    /** Display height in pixels */
    frameHeight: number;
    /** Map of action → { row, frames, speed } — kept for API compat */
    actions: Record<string, { row: number; frames: number; speed?: number }>;
}

export interface SpriteCharacterProps {
    sheet: SpriteSheetConfig;
    action?: SpriteAction;
    scale?: number;
    flipX?: boolean;
    className?: string;
    onClick?: () => void;
}

// ---------------------------------------------------------------------------
// Pre-built sprite configs (display sizing only — no sheet math needed)
// ---------------------------------------------------------------------------

/** Agent sprites — rendered at 48×48 base, scaled up */
export const AGENT_SHEETS: Record<string, SpriteSheetConfig> = {
    analytical: {
        src: "/sprites/agent_analytical.png",
        frameWidth: 48, frameHeight: 48,
        actions: { idle: { row: 0, frames: 1, speed: 1.2 }, walk: { row: 0, frames: 1, speed: 0.6 }, work: { row: 0, frames: 1, speed: 0.8 }, sleep: { row: 0, frames: 1, speed: 2.0 }, chat: { row: 0, frames: 1, speed: 0.8 }, happy: { row: 0, frames: 1, speed: 0.6 } },
    },
    creative: {
        src: "/sprites/agent_creative.png",
        frameWidth: 48, frameHeight: 48,
        actions: { idle: { row: 0, frames: 1, speed: 1.2 }, walk: { row: 0, frames: 1, speed: 0.6 }, work: { row: 0, frames: 1, speed: 0.8 }, sleep: { row: 0, frames: 1, speed: 2.0 }, chat: { row: 0, frames: 1, speed: 0.8 }, happy: { row: 0, frames: 1, speed: 0.6 } },
    },
    direct: {
        src: "/sprites/agent_direct.png",
        frameWidth: 48, frameHeight: 48,
        actions: { idle: { row: 0, frames: 1, speed: 1.2 }, walk: { row: 0, frames: 1, speed: 0.6 }, work: { row: 0, frames: 1, speed: 0.8 }, sleep: { row: 0, frames: 1, speed: 2.0 }, chat: { row: 0, frames: 1, speed: 0.8 }, happy: { row: 0, frames: 1, speed: 0.6 } },
    },
    warm: {
        src: "/sprites/agent_warm.png",
        frameWidth: 48, frameHeight: 48,
        actions: { idle: { row: 0, frames: 1, speed: 1.2 }, walk: { row: 0, frames: 1, speed: 0.6 }, work: { row: 0, frames: 1, speed: 0.8 }, sleep: { row: 0, frames: 1, speed: 2.0 }, chat: { row: 0, frames: 1, speed: 0.8 }, happy: { row: 0, frames: 1, speed: 0.6 } },
    },
};

/** Companion sprites — rendered at 32×32 base */
export const COMPANION_SHEETS: Record<string, SpriteSheetConfig> = {
    cat: { src: "/sprites/companion_cat.png", frameWidth: 32, frameHeight: 32, actions: { idle: { row: 0, frames: 1, speed: 1.5 }, walk: { row: 0, frames: 1, speed: 0.5 }, sleep: { row: 0, frames: 1, speed: 2.5 }, happy: { row: 0, frames: 1, speed: 0.6 } } },
    dog: { src: "/sprites/companion_dog.png", frameWidth: 32, frameHeight: 32, actions: { idle: { row: 0, frames: 1, speed: 1.5 }, walk: { row: 0, frames: 1, speed: 0.5 }, sleep: { row: 0, frames: 1, speed: 2.5 }, happy: { row: 0, frames: 1, speed: 0.6 } } },
    penguin: { src: "/sprites/companion_penguin.png", frameWidth: 32, frameHeight: 32, actions: { idle: { row: 0, frames: 1, speed: 1.5 }, walk: { row: 0, frames: 1, speed: 0.7 }, sleep: { row: 0, frames: 1, speed: 2.5 }, happy: { row: 0, frames: 1, speed: 0.6 } } },
    fox: { src: "/sprites/companion_fox.png", frameWidth: 32, frameHeight: 32, actions: { idle: { row: 0, frames: 1, speed: 1.5 }, walk: { row: 0, frames: 1, speed: 0.5 }, sleep: { row: 0, frames: 1, speed: 2.5 }, happy: { row: 0, frames: 1, speed: 0.6 } } },
    owl: { src: "/sprites/companion_owl.png", frameWidth: 32, frameHeight: 32, actions: { idle: { row: 0, frames: 1, speed: 1.8 }, walk: { row: 0, frames: 1, speed: 0.7 }, sleep: { row: 0, frames: 1, speed: 2.5 }, happy: { row: 0, frames: 1, speed: 0.6 } } },
    dragon: { src: "/sprites/companion_dragon.png", frameWidth: 32, frameHeight: 32, actions: { idle: { row: 0, frames: 1, speed: 1.5 }, walk: { row: 0, frames: 1, speed: 0.6 }, sleep: { row: 0, frames: 1, speed: 2.5 }, happy: { row: 0, frames: 1, speed: 0.6 } } },
};

// ---------------------------------------------------------------------------
// CSS animation per action
// ---------------------------------------------------------------------------

const ACTION_ANIMATION: Record<SpriteAction, string> = {
    idle: "spriteBreath 2.5s ease-in-out infinite",
    walk: "spriteBob 0.6s ease-in-out infinite",
    work: "spriteWork 1.2s ease-in-out infinite",
    sleep: "spriteSleep 3s ease-in-out infinite",
    chat: "spriteChat 1s ease-in-out infinite",
    happy: "spriteHappy 0.5s ease-in-out infinite",
};

const KEYFRAMES = `
@keyframes spriteBreath {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-2px); }
}
@keyframes spriteBob {
    0%, 100% { transform: translateY(0) translateX(0); }
    25% { transform: translateY(-3px) translateX(2px); }
    75% { transform: translateY(-1px) translateX(-2px); }
}
@keyframes spriteWork {
    0%, 100% { transform: rotate(0deg); }
    25% { transform: rotate(-2deg) translateY(-1px); }
    75% { transform: rotate(2deg) translateY(-1px); }
}
@keyframes spriteSleep {
    0%, 100% { transform: translateY(0) scale(1); opacity: 0.7; }
    50% { transform: translateY(1px) scale(0.98); opacity: 0.5; }
}
@keyframes spriteChat {
    0%, 100% { transform: translateY(0); }
    30% { transform: translateY(-3px); }
    60% { transform: translateY(-1px); }
}
@keyframes spriteHappy {
    0%, 100% { transform: translateY(0) scale(1); }
    50% { transform: translateY(-4px) scale(1.05); }
}
`;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

import { useState } from "react";

export default function SpriteCharacter({
    sheet,
    action = "idle",
    scale = 2,
    flipX = false,
    className = "",
    onClick,
}: SpriteCharacterProps) {
    const [imgError, setImgError] = useState(false);
    const displayWidth = sheet.frameWidth * scale;
    const displayHeight = sheet.frameHeight * scale;
    const anim = ACTION_ANIMATION[action] || ACTION_ANIMATION.idle;

    return (
        <div
            className={`sprite-character ${className}`}
            onClick={onClick}
            style={{
                width: displayWidth,
                height: displayHeight,
                position: "relative",
                cursor: onClick ? "pointer" : undefined,
            }}
        >
            <style>{KEYFRAMES}</style>
            {!imgError ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                    src={sheet.src}
                    alt="character"
                    draggable={false}
                    onError={() => setImgError(true)}
                    style={{
                        width: displayWidth,
                        height: displayHeight,
                        objectFit: "contain",
                        imageRendering: "pixelated",
                        transform: flipX ? "scaleX(-1)" : undefined,
                        animation: anim,
                        filter: "drop-shadow(0 4px 6px rgba(0,0,0,0.6))",
                    }}
                />
            ) : (
                <div style={{
                    width: displayWidth,
                    height: displayHeight,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: displayWidth * 0.6,
                    animation: anim,
                }}>
                    🔥
                </div>
            )}
        </div>
    );
}

/**
 * Fallback: renders sprite if available, emoji if not.
 */
export function SpriteOrEmoji({
    sheet,
    fallbackEmoji,
    action = "idle",
    scale = 2,
    flipX = false,
    className = "",
}: SpriteCharacterProps & { fallbackEmoji: string }) {
    return (
        <div className={`relative ${className}`} style={{ width: sheet.frameWidth * scale, height: sheet.frameHeight * scale }}>
            {/* Emoji fallback */}
            <div className="absolute inset-0 flex items-center justify-center" style={{ fontSize: sheet.frameWidth * scale * 0.6, zIndex: 0 }}>
                {fallbackEmoji}
            </div>
            {/* Sprite layer */}
            <div className="absolute inset-0 z-10">
                <SpriteCharacter sheet={sheet} action={action} scale={scale} flipX={flipX} />
            </div>
        </div>
    );
}

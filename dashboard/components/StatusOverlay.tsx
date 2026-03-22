"use client";

/**
 * 🎮 StatusOverlay — Sprint 18 F4.
 *
 * Kairosoft-style animated status effects that float above characters.
 * Driven by agent/system state. Premium variants available in the store.
 */

export type StatusEffect =
    | "on_a_roll"   // 🔥 AI processing fast
    | "spark"       // ⚡ Learning something new
    | "sleeping"    // 💤 Agent idle
    | "struggling"  // 😰 VRAM maxed
    | "celebration" // 🎉 Task completed
    | "burned_out"  // 💀 Error state
    | "lightbulb"   // 💡 Brainstorming
    | "heart"       // ❤️ Companion affection high
    | null;

interface StatusOverlayProps {
    status: StatusEffect;
    /** Use premium (golden) variant */
    premium?: boolean;
    /** Size in px */
    size?: number;
    className?: string;
}

const STATUS_CONFIG: Record<string, {
    emoji: string;
    premiumEmoji?: string;
    animation: string;
    color: string;
}> = {
    on_a_roll: {
        emoji: "🔥",
        premiumEmoji: "🌟",
        animation: "animate-[statusBounce_0.6s_ease-in-out_infinite]",
        color: "#f59e0b",
    },
    spark: {
        emoji: "⚡",
        premiumEmoji: "🌩️",
        animation: "animate-[statusFlash_0.4s_steps(2)_infinite]",
        color: "#eab308",
    },
    sleeping: {
        emoji: "💤",
        animation: "animate-[statusFloat_2s_ease-in-out_infinite]",
        color: "#8b5cf6",
    },
    struggling: {
        emoji: "😰",
        animation: "animate-[statusShake_0.3s_ease-in-out_infinite]",
        color: "#ef4444",
    },
    celebration: {
        emoji: "🎉",
        premiumEmoji: "🌈",
        animation: "animate-[statusPop_0.5s_ease-out_infinite]",
        color: "#22c55e",
    },
    burned_out: {
        emoji: "💀",
        animation: "animate-[statusPulse_1.5s_ease-in-out_infinite]",
        color: "#6b7280",
    },
    lightbulb: {
        emoji: "💡",
        premiumEmoji: "✨",
        animation: "animate-[statusGlow_1s_ease-in-out_infinite]",
        color: "#fbbf24",
    },
    heart: {
        emoji: "❤️",
        premiumEmoji: "💖",
        animation: "animate-[statusBeat_0.8s_ease-in-out_infinite]",
        color: "#ec4899",
    },
};

// CSS migrated to globals.css

export default function StatusOverlay({ status, premium = false, size = 20, className = "" }: StatusOverlayProps) {
    if (!status) return null;

    const config = STATUS_CONFIG[status];
    if (!config) return null;

    const emoji = (premium && config.premiumEmoji) ? config.premiumEmoji : config.emoji;

    return (
        <>
            {/* CSS in globals.css */}
            <div
                className={`absolute z-20 pointer-events-none ${config.animation} ${className}`}
                style={{
                    top: -size * 0.6,
                    left: "50%",
                    transform: "translateX(-50%)",
                    fontSize: size,
                    lineHeight: 1,
                    filter: `drop-shadow(0 0 4px ${config.color})`,
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    '--glow-color': config.color,
                } as any}
            >
                {emoji}
            </div>
        </>
    );
}

/**
 * Map backend agent status to a StatusEffect.
 */
export function mapAgentStatus(backendStatus: string): StatusEffect {
    const map: Record<string, StatusEffect> = {
        "on_a_roll": "on_a_roll",
        "working": "on_a_roll",
        "processing": "on_a_roll",
        "learning": "spark",
        "training": "spark",
        "idle": "sleeping",
        "sleeping": "sleeping",
        "error": "burned_out",
        "crashed": "burned_out",
        "overloaded": "struggling",
        "brainstorming": "lightbulb",
        "completed": "celebration",
        "happy": "heart",
    };
    return map[backendStatus] || null;
}

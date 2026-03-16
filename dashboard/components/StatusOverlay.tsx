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

const STATUS_CSS = `
    @keyframes statusBounce {
        0%, 100% { transform: translateY(0) scale(1); }
        50% { transform: translateY(-6px) scale(1.15); }
    }
    @keyframes statusFloat {
        0%, 100% { transform: translateY(0) translateX(0); opacity: 0.8; }
        25% { transform: translateY(-8px) translateX(3px); opacity: 1; }
        75% { transform: translateY(-4px) translateX(-3px); opacity: 0.6; }
    }
    @keyframes statusFlash {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.3; transform: scale(0.8); }
    }
    @keyframes statusShake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-3px) rotate(-5deg); }
        75% { transform: translateX(3px) rotate(5deg); }
    }
    @keyframes statusPop {
        0% { transform: scale(0.8); opacity: 0.5; }
        50% { transform: scale(1.3); opacity: 1; }
        100% { transform: scale(1); opacity: 0.8; }
    }
    @keyframes statusPulse {
        0%, 100% { opacity: 0.4; filter: grayscale(0.5); }
        50% { opacity: 0.8; filter: grayscale(0); }
    }
    @keyframes statusGlow {
        0%, 100% { filter: drop-shadow(0 0 2px var(--glow-color)); }
        50% { filter: drop-shadow(0 0 10px var(--glow-color)) drop-shadow(0 0 20px var(--glow-color)); }
    }
    @keyframes statusBeat {
        0%, 100% { transform: scale(1); }
        15% { transform: scale(1.3); }
        30% { transform: scale(1); }
        45% { transform: scale(1.2); }
    }
`;

export default function StatusOverlay({ status, premium = false, size = 20, className = "" }: StatusOverlayProps) {
    if (!status) return null;

    const config = STATUS_CONFIG[status];
    if (!config) return null;

    const emoji = (premium && config.premiumEmoji) ? config.premiumEmoji : config.emoji;

    return (
        <>
            <style>{STATUS_CSS}</style>
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

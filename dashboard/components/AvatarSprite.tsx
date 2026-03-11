"use client";

/**
 * AvatarSprite — Pure SVG avatar renderer.
 * Takes an avatar config and renders a character at any size.
 * Zero VRAM, zero GPU, ~5KB per avatar.
 */

interface AvatarConfig {
    style: "pixel" | "minimal" | "emoji";
    emoji?: string;
    hairStyle: number;    // 0-5
    hairColor: string;    // hex
    skinTone: string;     // hex
    outfit: "warrior" | "developer" | "artist" | "guardian" | "scholar" | "crown";
    accessory: "none" | "glasses" | "headphones" | "hat";
}

interface AvatarSpriteProps {
    config: AvatarConfig;
    size?: number;
    status?: "online" | "busy" | "offline" | "hurt";
    className?: string;
}

const OUTFIT_COLORS: Record<string, string> = {
    warrior: "#c0392b",
    developer: "#2c3e50",
    artist: "#8e44ad",
    guardian: "#27ae60",
    scholar: "#2980b9",
    crown: "#f39c12",
};

const OUTFIT_ICONS: Record<string, string> = {
    warrior: "⚔️",
    developer: "🧑‍💻",
    artist: "🎨",
    guardian: "🛡️",
    scholar: "📚",
    crown: "👑",
};

const HAIR_PATHS = [
    "M12,4 Q16,1 20,4 L20,8 Q16,6 12,8Z",         // short
    "M10,4 Q16,0 22,4 L22,10 Q16,7 10,10Z",         // medium
    "M10,4 Q16,-1 22,4 L24,14 Q16,10 8,14Z",        // long
    "M12,4 Q16,2 20,4 Q22,6 20,8 Q16,5 12,8Z",      // wavy
    "M11,4 Q13,2 15,4 Q17,2 19,4 Q21,2 21,5 L20,8 Q16,5 12,8Z", // spiky
    "M14,3 Q16,1 18,3 Q20,5 18,7 Q16,5 14,7 Q12,5 14,3Z",       // curly
];

export default function AvatarSprite({ config, size = 64, status, className }: AvatarSpriteProps) {
    if (config.style === "emoji") {
        return (
            <div
                className={`relative flex items-center justify-center rounded-full ${className || ""}`}
                style={{
                    width: size,
                    height: size,
                    background: "var(--color-glass)",
                    border: "2px solid var(--color-glass-border)",
                    fontSize: size * 0.5,
                }}
            >
                {config.emoji || OUTFIT_ICONS[config.outfit]}
                {status === "hurt" && (
                    <span className="absolute -bottom-1 -right-1 text-xs">🩹</span>
                )}
                {status && <StatusDot status={status} size={size} />}
            </div>
        );
    }

    // SVG avatar (pixel or minimal)
    const outfitColor = OUTFIT_COLORS[config.outfit];
    const strokeWidth = config.style === "pixel" ? 0.8 : 0.5;
    const isHurt = status === "hurt";

    return (
        <div className={`relative ${className || ""}`} style={{ width: size, height: size }}>
            <svg
                viewBox="0 0 32 32"
                width={size}
                height={size}
                className={isHurt ? "animate-[wobble_2s_ease-in-out_infinite]" : ""}
                style={{ opacity: isHurt ? 0.7 : 1 }}
            >
                {/* Head */}
                <circle cx="16" cy="10" r="6" fill={config.skinTone} stroke="#333" strokeWidth={strokeWidth} />

                {/* Hair */}
                <path d={HAIR_PATHS[config.hairStyle] || HAIR_PATHS[0]} fill={config.hairColor} stroke="#333" strokeWidth={strokeWidth * 0.5} />

                {/* Eyes */}
                {isHurt ? (
                    <>
                        <text x="13" y="11" fontSize="3" textAnchor="middle">✕</text>
                        <text x="19" y="11" fontSize="3" textAnchor="middle">✕</text>
                    </>
                ) : (
                    <>
                        <circle cx="13.5" cy="10" r="1" fill="#333" />
                        <circle cx="18.5" cy="10" r="1" fill="#333" />
                    </>
                )}

                {/* Mouth */}
                {isHurt ? (
                    <path d="M14,13 Q16,12 18,13" fill="none" stroke="#333" strokeWidth={strokeWidth} />
                ) : (
                    <path d="M14,12.5 Q16,14 18,12.5" fill="none" stroke="#333" strokeWidth={strokeWidth} />
                )}

                {/* Body / Outfit */}
                <path d="M10,16 Q16,15 22,16 L24,28 Q16,30 8,28Z" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />

                {/* Outfit detail */}
                {config.outfit === "warrior" && <path d="M16,16 L16,24" stroke="#f39c12" strokeWidth="1" />}
                {config.outfit === "guardian" && <circle cx="16" cy="21" r="3" fill="none" stroke="#f1c40f" strokeWidth="0.8" />}
                {config.outfit === "scholar" && <path d="M13,19 L19,19 M13,21 L19,21 M13,23 L17,23" stroke="#ecf0f1" strokeWidth="0.5" />}
                {config.outfit === "crown" && <path d="M13,16 L14.5,14 L16,16 L17.5,14 L19,16" fill="#f39c12" stroke="#e67e22" strokeWidth="0.3" />}

                {/* Accessory */}
                {config.accessory === "glasses" && (
                    <g stroke="#333" strokeWidth="0.6" fill="none">
                        <circle cx="13.5" cy="10" r="2.2" />
                        <circle cx="18.5" cy="10" r="2.2" />
                        <path d="M15.7,10 L16.3,10" />
                    </g>
                )}
                {config.accessory === "headphones" && (
                    <g stroke="#555" strokeWidth="1" fill="none">
                        <path d="M9,10 Q9,3 16,3 Q23,3 23,10" />
                        <rect x="8" y="9" width="2.5" height="3" rx="1" fill="#555" />
                        <rect x="21.5" y="9" width="2.5" height="3" rx="1" fill="#555" />
                    </g>
                )}
                {config.accessory === "hat" && (
                    <path d="M10,6 Q16,0 22,6 L23,7 Q16,5 9,7Z" fill="#2c3e50" stroke="#333" strokeWidth="0.3" />
                )}

                {/* Hurt bandage */}
                {isHurt && (
                    <g>
                        <rect x="20" y="8" width="4" height="2.5" rx="0.5" fill="white" stroke="#e74c3c" strokeWidth="0.3" />
                        <line x1="21" y1="8.5" x2="21" y2="10" stroke="#e74c3c" strokeWidth="0.3" />
                        <line x1="20.5" y1="9.25" x2="23.5" y2="9.25" stroke="#e74c3c" strokeWidth="0.3" />
                    </g>
                )}
            </svg>
            {status && <StatusDot status={status} size={size} />}
        </div>
    );
}

function StatusDot({ status, size }: { status: string; size: number }) {
    const colors: Record<string, string> = {
        online: "var(--color-neon)",
        busy: "var(--color-warning)",
        offline: "var(--color-rune-dim)",
        hurt: "var(--color-danger)",
    };
    const dotSize = Math.max(8, size * 0.2);
    return (
        <div
            className="absolute rounded-full border-2"
            style={{
                width: dotSize,
                height: dotSize,
                background: colors[status] || colors.offline,
                borderColor: "var(--color-void-light)",
                bottom: 0,
                right: 0,
            }}
        />
    );
}

export type { AvatarConfig };

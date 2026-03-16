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
    outfit: "warrior" | "developer" | "artist" | "guardian" | "scholar" | "crown" | "cat" | "dog" | "penguin" | "fox" | "owl" | "dragon";
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
    cat: "#f39c12",
    dog: "#a0522d",
    penguin: "#2c3e50",
    fox: "#d35400",
    owl: "#8B7355",
    dragon: "#27ae60",
};

const OUTFIT_ICONS: Record<string, string> = {
    warrior: "⚔️",
    developer: "🧑‍💻",
    artist: "🎨",
    guardian: "🛡️",
    scholar: "📚",
    crown: "👑",
    cat: "🐱",
    dog: "🐕",
    penguin: "🐧",
    fox: "🦊",
    owl: "🦉",
    dragon: "🐉",
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
    const outfitColor = OUTFIT_COLORS[config.outfit] || "#888";
    const strokeWidth = config.style === "pixel" ? 0.8 : 0.5;
    const isHurt = status === "hurt";
    const isAnimal = ["cat", "dog", "penguin", "fox", "owl", "dragon"].includes(config.outfit);

    // Animal avatar — completely different SVG
    if (isAnimal) {
        return (
            <div className={`relative ${className || ""}`} style={{ width: size, height: size }}>
                <svg
                    viewBox="0 0 32 32"
                    width={size}
                    height={size}
                    className={isHurt ? "animate-[wobble_2s_ease-in-out_infinite]" : ""}
                    style={{ opacity: isHurt ? 0.7 : 1, filter: "drop-shadow(0px 4px 4px rgba(0,0,0,0.5))" }}
                >
                    {config.outfit === "cat" && (
                        <g>
                            {/* Ears */}
                            <path d="M9,8 L12,4 L14,9Z" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            <path d="M18,9 L20,4 L23,8Z" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Head */}
                            <circle cx="16" cy="13" r="7" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Eyes */}
                            <ellipse cx="13" cy="12" rx="1.5" ry="2" fill={isHurt ? "none" : "#2ecc71"} stroke="#333" strokeWidth="0.4" />
                            <ellipse cx="19" cy="12" rx="1.5" ry="2" fill={isHurt ? "none" : "#2ecc71"} stroke="#333" strokeWidth="0.4" />
                            {!isHurt && <><circle cx="13" cy="12" r="0.7" fill="#333" /><circle cx="19" cy="12" r="0.7" fill="#333" /></>}
                            {isHurt && <><text x="13" y="13" fontSize="3" textAnchor="middle">✕</text><text x="19" y="13" fontSize="3" textAnchor="middle">✕</text></>}
                            {/* Nose + whiskers */}
                            <circle cx="16" cy="14.5" r="0.8" fill="#e91e63" />
                            <line x1="10" y1="14" x2="14" y2="14.5" stroke="#333" strokeWidth="0.3" />
                            <line x1="10" y1="15.5" x2="14" y2="15" stroke="#333" strokeWidth="0.3" />
                            <line x1="18" y1="14.5" x2="22" y2="14" stroke="#333" strokeWidth="0.3" />
                            <line x1="18" y1="15" x2="22" y2="15.5" stroke="#333" strokeWidth="0.3" />
                            {/* Body */}
                            <ellipse cx="16" cy="24" rx="6" ry="5" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Tail */}
                            <path d="M22,22 Q28,18 26,12" fill="none" stroke={outfitColor} strokeWidth="2" strokeLinecap="round" />
                        </g>
                    )}
                    {config.outfit === "dog" && (
                        <g>
                            {/* Ears (floppy) */}
                            <ellipse cx="9" cy="10" rx="3" ry="5" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            <ellipse cx="23" cy="10" rx="3" ry="5" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Head */}
                            <circle cx="16" cy="12" r="7" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Eyes */}
                            {isHurt ? <><text x="13" y="12" fontSize="3" textAnchor="middle">✕</text><text x="19" y="12" fontSize="3" textAnchor="middle">✕</text></> : <><circle cx="13" cy="11" r="1.2" fill="#333" /><circle cx="19" cy="11" r="1.2" fill="#333" /><circle cx="13.4" cy="10.6" r="0.4" fill="white" /><circle cx="19.4" cy="10.6" r="0.4" fill="white" /></>}
                            {/* Nose + tongue */}
                            <ellipse cx="16" cy="14" rx="2" ry="1.2" fill="#333" />
                            {!isHurt && <path d="M16,15.2 Q16.5,17 16,18" fill="#e91e63" stroke="none" strokeWidth="0" />}
                            {/* Body */}
                            <ellipse cx="16" cy="24" rx="6" ry="5" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Tail (wagging) */}
                            <path d="M22,21 Q26,17 24,14" fill="none" stroke={outfitColor} strokeWidth="2" strokeLinecap="round" className={isHurt ? "" : "animate-[sway_0.5s_ease-in-out_infinite]"} />
                        </g>
                    )}
                    {config.outfit === "penguin" && (
                        <g>
                            {/* Body (black) */}
                            <ellipse cx="16" cy="18" rx="8" ry="11" fill="#2c3e50" stroke="#333" strokeWidth={strokeWidth} />
                            {/* Belly (white) */}
                            <ellipse cx="16" cy="20" rx="5" ry="8" fill="white" />
                            {/* Eyes */}
                            {isHurt ? <><text x="13" y="12" fontSize="3" textAnchor="middle">✕</text><text x="19" y="12" fontSize="3" textAnchor="middle">✕</text></> : <><circle cx="13" cy="11" r="1.5" fill="white" /><circle cx="19" cy="11" r="1.5" fill="white" /><circle cx="13" cy="11" r="0.8" fill="#333" /><circle cx="19" cy="11" r="0.8" fill="#333" /></>}
                            {/* Beak */}
                            <path d="M14.5,13.5 L16,15 L17.5,13.5Z" fill="#f39c12" />
                            {/* Feet */}
                            <ellipse cx="13" cy="29" rx="2.5" ry="1" fill="#f39c12" />
                            <ellipse cx="19" cy="29" rx="2.5" ry="1" fill="#f39c12" />
                        </g>
                    )}
                    {config.outfit === "fox" && (
                        <g>
                            {/* Ears */}
                            <path d="M8,7 L12,2 L14,8Z" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            <path d="M18,8 L20,2 L24,7Z" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Head */}
                            <circle cx="16" cy="12" r="7" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* White muzzle */}
                            <path d="M12,13 Q16,18 20,13 Q16,15 12,13Z" fill="white" />
                            {/* Eyes */}
                            {isHurt ? <><text x="13" y="11" fontSize="3" textAnchor="middle">✕</text><text x="19" y="11" fontSize="3" textAnchor="middle">✕</text></> : <><ellipse cx="13" cy="10.5" rx="1" ry="1.3" fill="#f39c12" stroke="#333" strokeWidth="0.3" /><ellipse cx="19" cy="10.5" rx="1" ry="1.3" fill="#f39c12" stroke="#333" strokeWidth="0.3" /><circle cx="13" cy="10.5" r="0.5" fill="#333" /><circle cx="19" cy="10.5" r="0.5" fill="#333" /></>}
                            {/* Nose */}
                            <circle cx="16" cy="14" r="0.8" fill="#333" />
                            {/* Body */}
                            <ellipse cx="16" cy="24" rx="6" ry="5" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Fluffy tail */}
                            <path d="M22,22 Q28,16 25,10" fill="none" stroke={outfitColor} strokeWidth="3" strokeLinecap="round" />
                            <path d="M25,10 Q24,9 25,8" fill="white" stroke="none" />
                        </g>
                    )}
                    {config.outfit === "owl" && (
                        <g>
                            {/* Body */}
                            <ellipse cx="16" cy="18" rx="8" ry="10" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Ear tufts */}
                            <path d="M10,8 L12,4 L14,9" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            <path d="M18,9 L20,4 L22,8" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Face disc */}
                            <circle cx="16" cy="13" r="6" fill="#D2B48C" stroke="#333" strokeWidth="0.3" />
                            {/* Big eyes */}
                            {isHurt ? <><text x="13" y="13" fontSize="4" textAnchor="middle">✕</text><text x="19" y="13" fontSize="4" textAnchor="middle">✕</text></> : <><circle cx="13" cy="12" r="2.5" fill="#f39c12" stroke="#333" strokeWidth="0.3" /><circle cx="19" cy="12" r="2.5" fill="#f39c12" stroke="#333" strokeWidth="0.3" /><circle cx="13" cy="12" r="1.2" fill="#333" /><circle cx="19" cy="12" r="1.2" fill="#333" /></>}
                            {/* Beak */}
                            <path d="M15,14.5 L16,16 L17,14.5Z" fill="#f39c12" />
                            {/* Belly pattern */}
                            <ellipse cx="16" cy="22" rx="4" ry="5" fill="#D2B48C" opacity="0.5" />
                        </g>
                    )}
                    {config.outfit === "dragon" && (
                        <g>
                            {/* Horns */}
                            <path d="M10,7 L11,2 L13,8" fill="#333" />
                            <path d="M19,8 L21,2 L22,7" fill="#333" />
                            {/* Head */}
                            <circle cx="16" cy="12" r="7" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Eyes (slitted) */}
                            {isHurt ? <><text x="13" y="12" fontSize="3" textAnchor="middle">✕</text><text x="19" y="12" fontSize="3" textAnchor="middle">✕</text></> : <><ellipse cx="13" cy="11" rx="1.5" ry="1" fill="#f1c40f" stroke="#333" strokeWidth="0.3" /><ellipse cx="19" cy="11" rx="1.5" ry="1" fill="#f1c40f" stroke="#333" strokeWidth="0.3" /><ellipse cx="13" cy="11" rx="0.3" ry="1" fill="#333" /><ellipse cx="19" cy="11" rx="0.3" ry="1" fill="#333" /></>}
                            {/* Nostrils + smoke */}
                            <circle cx="14.5" cy="14.5" r="0.5" fill="#333" />
                            <circle cx="17.5" cy="14.5" r="0.5" fill="#333" />
                            {!isHurt && <text x="16" y="17" fontSize="3" textAnchor="middle" opacity="0.5">💨</text>}
                            {/* Body */}
                            <ellipse cx="16" cy="24" rx="7" ry="5" fill={outfitColor} stroke="#333" strokeWidth={strokeWidth} />
                            {/* Wings */}
                            <path d="M8,18 Q4,12 7,8 L10,16Z" fill={outfitColor} stroke="#333" strokeWidth="0.3" opacity="0.7" />
                            <path d="M24,18 Q28,12 25,8 L22,16Z" fill={outfitColor} stroke="#333" strokeWidth="0.3" opacity="0.7" />
                            {/* Belly scales */}
                            <ellipse cx="16" cy="24" rx="4" ry="3" fill="#a8e6cf" opacity="0.5" />
                        </g>
                    )}
                    {/* Hurt bandage on animals */}
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

    return (
        <div className={`relative ${className || ""}`} style={{ width: size, height: size }}>
            <svg
                viewBox="0 0 32 32"
                width={size}
                height={size}
                className={isHurt ? "animate-[wobble_2s_ease-in-out_infinite]" : ""}
                style={{ opacity: isHurt ? 0.7 : 1, filter: "drop-shadow(0px 4px 4px rgba(0,0,0,0.5))" }}
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

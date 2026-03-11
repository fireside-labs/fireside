"use client";

interface BrainCardProps {
    id: string;
    emoji: string;
    name: string;
    label: string;
    description: string;
    size?: string;
    speed?: string;
    badge: "FREE" | "PAID";
    compatibility: "compatible" | "needs-more-memory" | "cloud";
    compatibilityNote?: string;
    installed?: boolean;
    active?: boolean;
    onInstall?: () => void;
    onSwitch?: () => void;
    onRemove?: () => void;
}

export default function BrainCard({
    emoji,
    label,
    description,
    size,
    speed,
    badge,
    compatibility,
    compatibilityNote,
    installed,
    active,
    onInstall,
    onSwitch,
    onRemove,
}: BrainCardProps) {
    const compatBadge = {
        compatible: { text: "✅ Compatible", color: "var(--color-neon)" },
        "needs-more-memory": { text: "⚠️ Needs more memory", color: "var(--color-warning)" },
        cloud: { text: "☁️ Cloud", color: "var(--color-info)" },
    }[compatibility];

    return (
        <div
            className="glass-card p-5 flex flex-col h-full"
            style={{
                borderColor: active ? "var(--color-neon)" : "var(--color-glass-border)",
                borderWidth: active ? 2 : 1,
            }}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <span className="text-2xl">{emoji}</span>
                    <div>
                        <h3 className="text-white font-semibold">{label}</h3>
                        {active && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-neon-glow)] text-[var(--color-neon)] font-bold">
                                ACTIVE
                            </span>
                        )}
                    </div>
                </div>
                <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${badge === "FREE"
                            ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)]"
                            : "bg-[rgba(168,85,247,0.15)] text-purple-400"
                        }`}
                >
                    {badge}
                </span>
            </div>

            {/* Description */}
            <p className="text-xs text-[var(--color-rune)] leading-relaxed mb-3 flex-1">
                {description}
            </p>

            {/* Stats */}
            <div className="flex flex-wrap gap-3 text-xs text-[var(--color-rune-dim)] mb-3">
                {size && <span>📦 {size}</span>}
                {speed && <span>⚡ ~{speed}</span>}
                <span style={{ color: compatBadge.color }}>{compatBadge.text}</span>
            </div>

            {/* Compatibility warning */}
            {compatibilityNote && compatibility === "needs-more-memory" && (
                <p className="text-xs text-[var(--color-warning)] mb-3">
                    ⚠️ {compatibilityNote}
                </p>
            )}

            {/* Actions */}
            <div className="flex gap-2">
                {!installed && compatibility !== "needs-more-memory" && (
                    <button onClick={onInstall} className="btn-neon px-4 py-2 text-xs flex-1">
                        Install
                    </button>
                )}
                {!installed && compatibility === "needs-more-memory" && (
                    <button disabled className="px-4 py-2 text-xs flex-1 rounded-lg bg-[var(--color-glass)] text-[var(--color-rune-dim)] cursor-not-allowed">
                        Not enough memory
                    </button>
                )}
                {installed && !active && (
                    <button onClick={onSwitch} className="btn-neon px-4 py-2 text-xs flex-1">
                        Switch to this brain
                    </button>
                )}
                {installed && active && (
                    <span className="px-4 py-2 text-xs text-[var(--color-neon)] text-center flex-1">
                        Currently active
                    </span>
                )}
                {installed && !active && (
                    <button
                        onClick={onRemove}
                        className="px-3 py-2 text-xs rounded-lg border border-[var(--color-danger)] text-[var(--color-danger)] hover:bg-[rgba(255,68,102,0.12)] transition-colors"
                    >
                        Remove
                    </button>
                )}
            </div>
        </div>
    );
}

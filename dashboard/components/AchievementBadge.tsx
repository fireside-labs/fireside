"use client";

interface AchievementBadgeProps {
    id: string;
    name: string;
    description: string;
    emoji?: string;
    earned?: boolean;
    earnedDate?: string;
    size?: "sm" | "md" | "lg";
}

export default function AchievementBadge({
    name,
    description,
    emoji,
    earned = false,
    earnedDate,
    size = "md",
}: AchievementBadgeProps) {
    const sizes = {
        sm: { box: "w-12 h-12", icon: "text-lg", text: "text-[9px]" },
        md: { box: "w-16 h-16", icon: "text-2xl", text: "text-[10px]" },
        lg: { box: "w-20 h-20", icon: "text-3xl", text: "text-xs" },
    };
    const s = sizes[size];

    const BADGE_ICONS: Record<string, string> = {
        streak_10: "🔥",
        streak_25: "💀",
        crucible_100: "⚔️",
        debate_win_3: "🗣️",
        tasks_50: "📋",
        knowledge_100: "📚",
        first_task: "🌟",
        night_owl: "🦉",
        team_player: "🤝",
        level_10: "⭐",
        level_25: "🏅",
        level_50: "👑",
    };

    const icon = emoji || BADGE_ICONS[name.toLowerCase().replace(/\s/g, "_")] || "🏆";

    return (
        <div className="group relative">
            <div
                className={`${s.box} rounded-xl flex flex-col items-center justify-center transition-all ${earned
                        ? "glass-card border-[var(--color-neon)] cursor-pointer hover:scale-110"
                        : "bg-[var(--color-glass)] border border-[var(--color-glass-border)] opacity-30 grayscale"
                    }`}
                style={{ borderWidth: earned ? 1 : 1 }}
            >
                <span className={s.icon}>{icon}</span>
                <span className={`${s.text} text-[var(--color-rune-dim)] mt-0.5 text-center leading-tight px-1 truncate w-full`}>
                    {name}
                </span>
            </div>

            {/* Hover tooltip */}
            {earned && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                    <div className="glass-card p-3 text-center whitespace-nowrap" style={{ borderColor: "var(--color-neon)" }}>
                        <p className="text-xs text-white font-semibold mb-0.5">{name}</p>
                        <p className="text-[10px] text-[var(--color-rune-dim)]">{description}</p>
                        {earnedDate && (
                            <p className="text-[9px] text-[var(--color-neon)] mt-1">Earned {earnedDate}</p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

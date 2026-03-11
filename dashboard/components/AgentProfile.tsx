"use client";

import AvatarSprite from "@/components/AvatarSprite";
import PersonalitySliders from "@/components/PersonalitySliders";
import AchievementBadge from "@/components/AchievementBadge";
import Link from "next/link";
import type { AvatarConfig } from "@/components/AvatarSprite";

interface AgentStats {
    tasks_completed: number;
    knowledge_count: number;
    accuracy: number;
    crucible_survival: number;
    streak: number;
    skills: Record<string, number>;
}

interface Achievement {
    id: string;
    name: string;
    desc: string;
    earned: boolean;
    date?: string;
}

interface AgentProfileProps {
    name: string;
    level: number;
    xp: number;
    xpToNext: number;
    avatar: AvatarConfig;
    stats: AgentStats;
    personality: Record<string, number>;
    achievements: Achievement[];
    status: "online" | "busy" | "offline" | "hurt";
    onPersonalityChange?: (id: string, value: number) => void;
}

export default function AgentProfile({
    name,
    level,
    xp,
    xpToNext,
    avatar,
    stats,
    personality,
    achievements,
    status,
    onPersonalityChange,
}: AgentProfileProps) {
    const xpPercent = Math.min(100, (xp / xpToNext) * 100);

    const statCards = [
        { label: "Tasks Done", value: stats.tasks_completed, icon: "📋", desc: "Total tasks completed" },
        { label: "Knowledge", value: stats.knowledge_count, icon: "📚", desc: "Things your AI remembers" },
        { label: "Accuracy", value: `${Math.round(stats.accuracy * 100)}%`, icon: "🎯", desc: "How often answers are right" },
        { label: "Knowledge Check", value: `${Math.round(stats.crucible_survival * 100)}%`, icon: "🛡️", desc: "Score on knowledge tests" },
        { label: "Streak", value: `${stats.streak} 🔥`, icon: "", desc: "Tasks in a row without errors" },
    ];

    return (
        <div className="space-y-6">
            {/* Header: Avatar + Name + Level */}
            <div className="glass-card p-6 flex flex-col items-center text-center">
                <AvatarSprite config={avatar} size={128} status={status} className="mb-4" />
                <h2 className="text-2xl font-bold text-white capitalize">{name}</h2>
                <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm text-[var(--color-neon)] font-bold">Level {level}</span>
                    {status === "hurt" && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-[rgba(255,68,102,0.15)] text-[var(--color-danger)]">
                            🩹 Wounded
                        </span>
                    )}
                    {status === "online" && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-neon-glow)] text-[var(--color-neon)]">
                            ✅ Online
                        </span>
                    )}
                </div>

                {/* XP Bar */}
                <div className="w-full max-w-xs mt-3">
                    <div className="flex justify-between text-[10px] text-[var(--color-rune-dim)] mb-1">
                        <span>{xp} XP</span>
                        <span>{xpToNext} XP to level {level + 1}</span>
                    </div>
                    <div className="h-2 rounded-full bg-[var(--color-glass)] overflow-hidden">
                        <div
                            className="h-2 rounded-full transition-all duration-700"
                            style={{
                                width: `${xpPercent}%`,
                                background: "linear-gradient(90deg, var(--color-neon-dim), var(--color-neon))",
                            }}
                        />
                    </div>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-5 gap-2">
                {statCards.map((s) => (
                    <div key={s.label} className="glass-card p-3 text-center">
                        {s.icon && <div className="text-lg mb-1">{s.icon}</div>}
                        <div className="text-lg text-white font-bold">{s.value}</div>
                        <div className="text-[10px] text-[var(--color-rune-dim)]">{s.label}</div>
                        <div className="text-[8px] text-[var(--color-rune-dim)] mt-0.5 opacity-60">{s.desc}</div>
                    </div>
                ))}
            </div>

            {/* Skills */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-3">Skills</h3>
                <div className="grid grid-cols-2 gap-2">
                    {Object.entries(stats.skills).map(([skill, level]) => (
                        <div key={skill} className="flex items-center justify-between">
                            <span className="text-sm text-[var(--color-rune)] capitalize">{skill}</span>
                            <span className="text-sm text-[var(--color-neon)]">
                                {"★".repeat(level)}{"☆".repeat(5 - level)}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Personality Sliders */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-3">Personality</h3>
                <PersonalitySliders
                    values={personality}
                    onChange={onPersonalityChange}
                    readOnly={!onPersonalityChange}
                />
            </div>

            {/* Achievements */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-3">Achievements</h3>
                <div className="flex flex-wrap gap-3">
                    {achievements.map((a) => (
                        <AchievementBadge
                            key={a.id}
                            id={a.id}
                            name={a.name}
                            description={a.desc}
                            earned={a.earned}
                            earnedDate={a.date}
                        />
                    ))}
                </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
                <Link href="/" className="btn-neon px-5 py-2.5 text-sm flex-1 text-center">
                    💬 Chat with {name}
                </Link>
                <Link href="/pipeline" className="px-5 py-2.5 text-sm flex-1 text-center rounded-lg border border-[var(--color-glass-border)] text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)] transition-colors">
                    📋 Assign Task
                </Link>
                <Link href="/soul" className="px-5 py-2.5 text-sm flex-1 text-center rounded-lg border border-[var(--color-glass-border)] text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)] transition-colors">
                    🧠 Edit Soul
                </Link>
            </div>
        </div>
    );
}

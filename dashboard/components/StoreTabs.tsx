"use client";

interface StoreTabsProps {
    selected: string;
    onSelect: (tab: string) => void;
    counts?: Record<string, number>;
}

const TABS = [
    { id: "agents", label: "Agents", emoji: "🤖" },
    { id: "themes", label: "Themes", emoji: "🏰" },
    { id: "avatars", label: "Avatars", emoji: "👤" },
    { id: "voices", label: "Voices", emoji: "🎤" },
    { id: "personalities", label: "Personalities", emoji: "💬" },
];

export default function StoreTabs({ selected, onSelect, counts }: StoreTabsProps) {
    return (
        <div className="flex gap-1 overflow-x-auto pb-1" role="tablist" aria-label="Store categories">
            {TABS.map((tab) => (
                <button
                    key={tab.id}
                    onClick={() => onSelect(tab.id)}
                    role="tab"
                    aria-selected={selected === tab.id}
                    className={`
            flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all
            ${selected === tab.id
                            ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)] border border-[rgba(0,255,136,0.15)]"
                            : "text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)]"
                        }
          `}
                >
                    <span>{tab.emoji}</span>
                    {tab.label}
                    {counts?.[tab.id] !== undefined && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--color-glass)] text-[var(--color-rune-dim)]">
                            {counts[tab.id]}
                        </span>
                    )}
                </button>
            ))}
        </div>
    );
}

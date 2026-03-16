"use client";

interface StoreTabsProps {
    tabs?: { id: string; label: string; emoji: string }[];
    selected: string;
    onSelect: (tab: string) => void;
    counts?: Record<string, number>;
}

const DEFAULT_TABS = [
    { id: "plugins", label: "Plugins", emoji: "🧩" },
    { id: "agents", label: "Agents", emoji: "🤖" },
    { id: "themes", label: "Themes", emoji: "🏰" },
    { id: "avatars", label: "Avatars", emoji: "👤" },
    { id: "voices", label: "Voices", emoji: "🎤" },
    { id: "personalities", label: "Personalities", emoji: "💬" },
];

export default function StoreTabs({ tabs = DEFAULT_TABS, selected, onSelect, counts }: StoreTabsProps) {
    const activeTabs = tabs;
    return (
        <div className="flex gap-1 overflow-x-auto pb-1" role="tablist" aria-label="Store categories">
            {activeTabs.map((tab) => (
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

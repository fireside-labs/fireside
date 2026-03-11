"use client";

interface ThemePickerProps {
    selected: string;
    onSelect: (theme: string) => void;
}

const THEMES = [
    { id: "valhalla", emoji: "🏰", label: "Valhalla", desc: "Norse great hall", free: true },
    { id: "office", emoji: "🏢", label: "Office", desc: "Modern workspace", free: true },
    { id: "space", emoji: "🚀", label: "Space", desc: "Space station", free: false },
    { id: "cozy", emoji: "🏡", label: "Cozy", desc: "Living room", free: false },
    { id: "dungeon", emoji: "⚔️", label: "Pixel Dungeon", desc: "RPG dungeon", free: false },
];

export default function ThemePicker({ selected, onSelect }: ThemePickerProps) {
    return (
        <div className="flex gap-2">
            {THEMES.map((t) => (
                <button
                    key={t.id}
                    onClick={() => onSelect(t.id)}
                    role="radio"
                    aria-checked={selected === t.id}
                    className="glass-card px-3 py-2 text-center transition-all"
                    style={{
                        borderColor: selected === t.id ? "var(--color-neon)" : "var(--color-glass-border)",
                        borderWidth: selected === t.id ? 2 : 1,
                        opacity: !t.free && selected !== t.id ? 0.6 : 1,
                    }}
                >
                    <span className="text-lg block">{t.emoji}</span>
                    <span className="text-[10px] text-white block">{t.label}</span>
                    {!t.free && (
                        <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-[rgba(168,85,247,0.15)] text-purple-400 block mt-0.5">
                            PREMIUM
                        </span>
                    )}
                </button>
            ))}
        </div>
    );
}

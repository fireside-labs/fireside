"use client";

interface BrainOption {
    id: string;
    emoji: string;
    name: string;
    label: string;
    badge: "FREE" | "PAID";
    description: string;
    vram_needed: number;
    compatible: boolean;
    warning?: string;
}

const BRAIN_OPTIONS: BrainOption[] = [
    {
        id: "fast", emoji: "⚡", name: "llama-3.1-8b", label: "Smart & Fast",
        badge: "FREE", description: "Best for quick questions and chat.",
        vram_needed: 6, compatible: true,
    },
    {
        id: "deep", emoji: "🧠", name: "qwen-2.5-35b", label: "Deep Thinker",
        badge: "FREE", description: "Best for complex analysis. Needs 24GB AI Memory.",
        vram_needed: 24, compatible: false, warning: "You have 16GB. This needs 24GB.",
    },
    {
        id: "cloud", emoji: "🌙", name: "kimi-k2", label: "Cloud Expert",
        badge: "PAID", description: "128K memory window. Great for reading long documents. Needs internet.",
        vram_needed: 0, compatible: true,
    },
];

export default function BrainPicker({
    selected,
    onSelect,
}: {
    selected: string;
    onSelect: (id: string) => void;
}) {
    return (
        <div className="space-y-2" role="radiogroup" aria-label="AI Brain selection">
            {BRAIN_OPTIONS.map((b) => (
                <button
                    key={b.id}
                    onClick={() => onSelect(b.id)}
                    role="radio"
                    aria-checked={selected === b.id}
                    aria-label={`${b.label} — ${b.description}`}
                    className="w-full text-left glass-card p-4 transition-all"
                    style={{
                        borderColor: selected === b.id ? "var(--color-neon)" : "var(--color-glass-border)",
                        borderWidth: selected === b.id ? 2 : 1,
                        opacity: !b.compatible ? 0.7 : 1,
                    }}
                >
                    <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                            <span className="text-lg">{b.emoji}</span>
                            <span className="text-sm text-white font-semibold">{b.label}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${b.badge === "FREE"
                                ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)]"
                                : "bg-[rgba(168,85,247,0.15)] text-purple-400"
                                }`}>
                                {b.badge}
                            </span>
                            <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${selected === b.id ? "border-[var(--color-neon)]" : "border-[var(--color-glass-border)]"
                                }`}>
                                {selected === b.id && <div className="w-2 h-2 rounded-full bg-[var(--color-neon)]" />}
                            </div>
                        </div>
                    </div>
                    <p className="text-xs text-[var(--color-rune-dim)] ml-7">{b.description}</p>
                    {b.warning && !b.compatible && (
                        <p className="text-xs text-[var(--color-warning)] ml-7 mt-1">⚠️ {b.warning}</p>
                    )}
                </button>
            ))}
        </div>
    );
}

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

export const BRAIN_OPTIONS: BrainOption[] = [
    {
        id: "fast", emoji: "⚡", name: "llama-3.1-8b", label: "Smart & Fast",
        badge: "FREE", description: "Best for quick questions. Requires 10GB VRAM.",
        vram_needed: 8, compatible: true,
    },
    {
        id: "deep", emoji: "🧠", name: "qwen-2.5-35b", label: "Deep Thinker",
        badge: "FREE", description: "Best for complex analysis. Requires 24GB VRAM.",
        vram_needed: 24, compatible: false, warning: "You have 16GB. This needs 24GB.",
    },
    {
        id: "cloud", emoji: "🌙", name: "kimi-k2", label: "Cloud Expert",
        badge: "PAID", description: "128K window. No VRAM required (Cloud).",
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
    // Get detected VRAM from localStorage
    const detectedVram = (() => {
        if (typeof window === "undefined") return 0;
        return parseFloat(localStorage.getItem("fireside_vram") || "0");
    })();

    return (
        <div className="space-y-3" role="radiogroup" aria-label="AI Brain selection">
            {BRAIN_OPTIONS.map((b) => {
                const isCompatible = b.vram_needed === 0 || detectedVram >= b.vram_needed;
                const warning = !isCompatible ? `Your system has ${detectedVram}GB VRAM. This brain needs ${b.vram_needed}GB.` : null;

                return (
                    <button
                        key={b.id}
                        onClick={() => onSelect(b.id)}
                        role="radio"
                        aria-checked={selected === b.id}
                        className="w-full text-left glass-card p-4 transition-all relative border-2"
                        style={{
                            borderColor: selected === b.id ? "var(--color-neon)" : "var(--color-glass-border)",
                            opacity: !isCompatible && selected !== b.id ? 0.6 : 1,
                        }}
                    >
                        <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                                <span className="text-xl">{b.emoji}</span>
                                <div>
                                    <span className="text-sm text-white font-bold block">{b.label}</span>
                                    <span className="text-[10px] text-[var(--color-rune-dim)] font-mono">{b.name}</span>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${b.badge === "FREE"
                                    ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)]"
                                    : "bg-[rgba(168,85,247,0.15)] text-purple-400"
                                    }`}>
                                    {b.badge}
                                </span>
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${selected === b.id ? "border-[var(--color-neon)]" : "border-[var(--color-glass-border)]"
                                    }`}>
                                    {selected === b.id && <div className="w-2.5 h-2.5 rounded-full bg-[var(--color-neon)]" />}
                                </div>
                            </div>
                        </div>
                        <p className="text-xs text-[var(--color-rune-dim)] ml-8 mt-1">{b.description}</p>
                        {warning && (
                            <div className="ml-8 mt-2 p-2 bg-[rgba(245,158,11,0.1)] rounded border border-[var(--color-warning)]-20">
                                <p className="text-[10px] text-[var(--color-warning)] font-medium">
                                    ⚠️ Performance Alert: {warning}
                                </p>
                            </div>
                        )}
                    </button>
                );
            })}
        </div>
    );
}

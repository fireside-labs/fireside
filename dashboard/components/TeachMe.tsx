"use client";

import { useState } from "react";
import type { PetSpecies } from "@/components/CompanionSim";

const CONFIRM_RESPONSES: Record<PetSpecies, (fact: string) => string> = {
    cat: (fact) => `*yawns* Fine. I'll remember "${fact}." Don't expect me to care.`,
    dog: (fact) => `OH WOW!! "${fact}" — GOT IT!! I'll NEVER forget!! Promise!! 🎾`,
    penguin: (fact) => `Noted. "${fact}" has been filed under Personal Facts, subsection User Preferences.`,
    fox: (fact) => `*ears perk up* Interesting... "${fact}." I'll keep that one close.`,
    owl: (fact) => `Wisdom shared is wisdom doubled. "${fact}" — archived in the library of knowing.`,
    dragon: (fact) => `"${fact}" — INSCRIBED INTO THE HOARD OF KNOWLEDGE! It shall not be forgotten!`,
};

interface TeachMeProps {
    petName: string;
    species: PetSpecies;
    onTeach?: (fact: string) => void;
}

export default function TeachMe({ petName, species, onTeach }: TeachMeProps) {
    const [open, setOpen] = useState(false);
    const [input, setInput] = useState("");
    const [confirmation, setConfirmation] = useState<string | null>(null);
    const [factCount, setFactCount] = useState(() => {
        if (typeof window === "undefined") return 0;
        const stored = localStorage.getItem("fireside_taught_facts");
        if (!stored) return 0;
        try { return JSON.parse(stored).length; } catch { return 0; }
    });

    const handleTeach = () => {
        if (!input.trim()) return;
        const fact = input.trim();

        // Store fact locally
        const stored = localStorage.getItem("fireside_taught_facts");
        const facts = stored ? JSON.parse(stored) : [];
        facts.push({ fact, timestamp: Date.now() });
        localStorage.setItem("fireside_taught_facts", JSON.stringify(facts));

        // Show confirmation
        setConfirmation(CONFIRM_RESPONSES[species](fact));
        setFactCount(facts.length);
        setInput("");
        onTeach?.(fact);

        // Auto-dismiss after 4 seconds
        setTimeout(() => {
            setConfirmation(null);
            setOpen(false);
        }, 4000);
    };

    if (!open) {
        return (
            <button
                onClick={() => setOpen(true)}
                className="w-full p-3 rounded-lg bg-[var(--color-glass)] hover:bg-[var(--color-glass-hover)] transition-colors text-left"
            >
                <div className="flex items-center gap-2">
                    <span className="text-lg">💡</span>
                    <div>
                        <p className="text-xs text-white font-medium">Teach {petName}</p>
                        <p className="text-[9px] text-[var(--color-rune-dim)]">
                            {factCount > 0
                                ? `${factCount} fact${factCount === 1 ? "" : "s"} learned · Tap to teach more`
                                : "Tell your companion something to remember"
                            }
                        </p>
                    </div>
                </div>
            </button>
        );
    }

    return (
        <div className="glass-card p-4 animate-[slideIn_0.2s_ease-out]">
            <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-white font-medium">💡 Teach {petName}</p>
                <button onClick={() => setOpen(false)} className="text-[var(--color-rune-dim)] hover:text-white text-xs">✕</button>
            </div>

            {confirmation ? (
                <div className="p-3 rounded-lg bg-[var(--color-neon-glow)] border border-[rgba(0,255,136,0.1)]">
                    <p className="text-xs text-[var(--color-rune)] italic">{confirmation}</p>
                    <p className="text-[9px] text-[var(--color-neon)] mt-1">📚 {factCount} fact{factCount === 1 ? "" : "s"} learned total</p>
                </div>
            ) : (
                <>
                    <p className="text-[10px] text-[var(--color-rune-dim)] mb-2">What should {petName} remember?</p>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleTeach()}
                            placeholder="I'm allergic to shellfish..."
                            className="flex-1 bg-[var(--color-glass)] text-white text-xs px-3 py-2 rounded-lg border border-[var(--color-glass-border)] outline-none focus:border-[var(--color-neon)]"
                            autoFocus
                        />
                        <button
                            onClick={handleTeach}
                            disabled={!input.trim()}
                            className="btn-neon px-3 py-2 text-xs disabled:opacity-30"
                        >
                            Remember
                        </button>
                    </div>
                    <p className="text-[8px] text-[var(--color-rune-dim)] mt-1.5">
                        Facts are stored locally and used in future conversations
                    </p>
                </>
            )}
        </div>
    );
}

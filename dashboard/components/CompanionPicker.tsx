"use client";

import { useState } from "react";
import AvatarSprite from "@/components/AvatarSprite";
import type { PetSpecies } from "@/components/CompanionSim";

interface CompanionPickerProps {
    onSelect: (species: PetSpecies, name: string) => void;
}

const PETS: { species: PetSpecies; emoji: string; label: string; personality: string; example: string }[] = [
    { species: "cat", emoji: "🐱", label: "Cat", personality: "Aloof & judgy", example: "Fine. Here's your answer. You're welcome." },
    { species: "dog", emoji: "🐕", label: "Dog", personality: "Excited about everything", example: "OMG YES!! I can help with that!! 🎾" },
    { species: "penguin", emoji: "🐧", label: "Penguin", personality: "Formal & dry humor", example: "Per your request. Shall I elaborate? No? Very well." },
    { species: "fox", emoji: "🦊", label: "Fox", personality: "Clever & mischievous", example: "Interesting question... here's what I'd do 😏" },
    { species: "owl", emoji: "🦉", label: "Owl", personality: "Wise & patient", example: "Good question. But first — what are you really asking?" },
    { species: "dragon", emoji: "🐉", label: "Dragon", personality: "Bold & dramatic", example: "OBVIOUSLY the answer is X. Was there ever any doubt?" },
];

export default function CompanionPicker({ onSelect }: CompanionPickerProps) {
    const [selected, setSelected] = useState<PetSpecies>("cat");
    const [name, setName] = useState("");
    const selectedPet = PETS.find((p) => p.species === selected)!;

    return (
        <div className="glass-card p-6">
            <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white mb-1">Choose Your Companion</h2>
                <p className="text-xs text-[var(--color-rune-dim)]">
                    Your companion travels with you. Your brain stays home.
                </p>
            </div>

            {/* Species grid */}
            <div className="grid grid-cols-3 gap-2 mb-5">
                {PETS.map((pet) => (
                    <button
                        key={pet.species}
                        onClick={() => setSelected(pet.species)}
                        className="p-3 rounded-lg text-center transition-all"
                        role="radio"
                        aria-checked={selected === pet.species}
                        style={{
                            background: selected === pet.species ? "var(--color-neon-glow)" : "var(--color-glass)",
                            borderLeft: selected === pet.species ? "2px solid var(--color-neon)" : "2px solid transparent",
                        }}
                    >
                        <AvatarSprite
                            config={{ style: "emoji", emoji: pet.emoji, hairStyle: 0, hairColor: "#333", skinTone: "#fad7a0", outfit: pet.species, accessory: "none" }}
                            size={48}
                            className="mx-auto mb-1.5"
                        />
                        <p className="text-xs text-white font-medium">{pet.label}</p>
                        <p className="text-[9px] text-[var(--color-rune-dim)]">{pet.personality}</p>
                    </button>
                ))}
            </div>

            {/* Preview */}
            <div className="p-3 rounded-lg bg-[var(--color-glass)] mb-4">
                <p className="text-[10px] text-[var(--color-rune-dim)] mb-1">💬 Example response:</p>
                <p className="text-xs text-[var(--color-rune)] italic">&quot;{selectedPet.example}&quot;</p>
            </div>

            {/* Name input */}
            <div className="mb-4">
                <label htmlFor="pet-name" className="text-xs text-[var(--color-rune-dim)] block mb-1">
                    Name your {selectedPet.label}
                </label>
                <input
                    id="pet-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={selected === "cat" ? "Whiskers" : selected === "dog" ? "Buddy" : selected === "penguin" ? "Sir Wadsworth" : selected === "fox" ? "Loki" : selected === "owl" ? "Sage" : "Ember"}
                    className="w-full bg-[var(--color-glass)] text-white text-sm px-3 py-2 rounded-lg border border-[var(--color-glass-border)] outline-none focus:border-[var(--color-neon)]"
                />
            </div>

            <button
                onClick={() => onSelect(selected, name || selectedPet.label)}
                className="btn-neon w-full py-2.5 text-sm"
            >
                🐾 Adopt {name || selectedPet.label}
            </button>
        </div>
    );
}

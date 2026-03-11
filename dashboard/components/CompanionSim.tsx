"use client";

import { useState, useEffect, useCallback } from "react";

type PetSpecies = "cat" | "dog" | "penguin" | "fox" | "owl" | "dragon";

interface PetState {
    name: string;
    species: PetSpecies;
    hunger: number;     // 0-100 (100 = full)
    mood: number;       // 0-100 (100 = happy)
    energy: number;     // 0-100 (100 = rested)
    xp: number;
    level: number;
}

interface WalkEvent {
    text: string;
    moodChange: number;
    xpGain: number;
    emoji: string;
}

const WALK_EVENTS: Record<PetSpecies, WalkEvent[]> = {
    cat: [
        { text: "found a mysterious USB drive on the sidewalk", moodChange: 15, xpGain: 5, emoji: "🔌" },
        { text: "knocked a flower pot off a ledge. No regrets.", moodChange: 20, xpGain: 3, emoji: "🌸" },
        { text: "stared at a wall for 10 minutes. Enlightenment achieved.", moodChange: 10, xpGain: 8, emoji: "🧘" },
        { text: "hissed at a cloud. The cloud left.", moodChange: 25, xpGain: 4, emoji: "☁️" },
        { text: "found a warm spot of sunshine. Napped instantly.", moodChange: 30, xpGain: 2, emoji: "☀️" },
    ],
    dog: [
        { text: "met another dog! BEST. DAY. EVER!", moodChange: 30, xpGain: 5, emoji: "🐕" },
        { text: "found a stick. THE GREATEST STICK IN HISTORY!", moodChange: 25, xpGain: 3, emoji: "🪵" },
        { text: "chased a squirrel up a tree. Lost. But gained experience.", moodChange: 15, xpGain: 7, emoji: "🐿️" },
        { text: "got belly rubs from a stranger. Absolutely lost it.", moodChange: 35, xpGain: 4, emoji: "🥰" },
        { text: "rolled in something unidentified. Smells AMAZING.", moodChange: 20, xpGain: 2, emoji: "💩" },
    ],
    penguin: [
        { text: "organized local rocks by size. Very satisfying.", moodChange: 15, xpGain: 6, emoji: "🪨" },
        { text: "attempted to fly. Results: inconclusive.", moodChange: 10, xpGain: 4, emoji: "✈️" },
        { text: "found a fish. Filed it under 'snacks, misc.'", moodChange: 25, xpGain: 5, emoji: "🐟" },
        { text: "encountered slippery ice. Slid with dignity.", moodChange: 20, xpGain: 3, emoji: "🧊" },
        { text: "drafted a formal complaint about the weather.", moodChange: 5, xpGain: 8, emoji: "📝" },
    ],
    fox: [
        { text: "outsmarted a vending machine. Free snack acquired.", moodChange: 25, xpGain: 7, emoji: "🍫" },
        { text: "hid behind a bush for no reason. Just felt right.", moodChange: 15, xpGain: 3, emoji: "🌿" },
        { text: "found a shiny thing. Pocketed it. Don't ask.", moodChange: 20, xpGain: 5, emoji: "✨" },
        { text: "discovered a secret path. Led to a dead end. Classic.", moodChange: 10, xpGain: 6, emoji: "🗺️" },
        { text: "convinced a crow to trade secrets. Worth it.", moodChange: 30, xpGain: 8, emoji: "🐦‍⬛" },
    ],
    owl: [
        { text: "counted 47 stars. Lost count. Started over.", moodChange: 15, xpGain: 5, emoji: "⭐" },
        { text: "overheard a philosophical argument between trees.", moodChange: 20, xpGain: 8, emoji: "🌳" },
        { text: "found an old book. Read it twice.", moodChange: 25, xpGain: 10, emoji: "📖" },
        { text: "hooted at the moon. The moon did not respond.", moodChange: 10, xpGain: 3, emoji: "🌙" },
        { text: "meditated on the nature of wisdom. Fell asleep.", moodChange: 30, xpGain: 4, emoji: "💤" },
    ],
    dragon: [
        { text: "SET A BUSH ON FIRE. Accidentally. Mostly.", moodChange: 25, xpGain: 5, emoji: "🔥" },
        { text: "found a pile of coins. ADDED TO THE HOARD!", moodChange: 35, xpGain: 8, emoji: "💰" },
        { text: "tried to scare a mailman. He was unimpressed.", moodChange: 10, xpGain: 3, emoji: "📮" },
        { text: "practiced flying. Hit a tree. Trees: 1, Dragon: 0.", moodChange: 15, xpGain: 6, emoji: "🌲" },
        { text: "ROARED at the horizon. Something roared back. Concerning.", moodChange: 20, xpGain: 7, emoji: "🏔️" },
    ],
};

const FOOD_ITEMS = [
    { emoji: "🐟", name: "Fish", hungerRestore: 30, moodBoost: 5 },
    { emoji: "🍖", name: "Treat", hungerRestore: 20, moodBoost: 15 },
    { emoji: "🥗", name: "Salad", hungerRestore: 15, moodBoost: 0 },
    { emoji: "🍰", name: "Cake", hungerRestore: 10, moodBoost: 25 },
];

interface CompanionSimProps {
    petState: PetState;
    onStateChange: (state: PetState) => void;
}

export default function CompanionSim({ petState, onStateChange }: CompanionSimProps) {
    const [walkResult, setWalkResult] = useState<WalkEvent | null>(null);
    const [feeding, setFeeding] = useState(false);
    const [walking, setWalking] = useState(false);

    // Passive stat decay every 60 seconds
    useEffect(() => {
        const decay = setInterval(() => {
            onStateChange({
                ...petState,
                hunger: Math.max(0, petState.hunger - 2),
                energy: Math.max(0, petState.energy - 1),
                mood: Math.max(0, petState.mood - (petState.hunger < 20 ? 3 : 1)),
            });
        }, 60000);
        return () => clearInterval(decay);
    }, [petState, onStateChange]);

    const feedPet = (food: typeof FOOD_ITEMS[0]) => {
        setFeeding(true);
        setTimeout(() => {
            onStateChange({
                ...petState,
                hunger: Math.min(100, petState.hunger + food.hungerRestore),
                mood: Math.min(100, petState.mood + food.moodBoost),
                xp: petState.xp + 2,
            });
            setFeeding(false);
        }, 800);
    };

    const walkPet = useCallback(() => {
        if (walking) return;
        setWalking(true);
        setWalkResult(null);
        const events = WALK_EVENTS[petState.species];
        const event = events[Math.floor(Math.random() * events.length)];
        setTimeout(() => {
            setWalkResult(event);
            const newXp = petState.xp + event.xpGain;
            const levelUp = newXp >= (petState.level * 20);
            onStateChange({
                ...petState,
                mood: Math.min(100, petState.mood + event.moodChange),
                energy: Math.max(0, petState.energy - 15),
                xp: levelUp ? newXp - (petState.level * 20) : newXp,
                level: levelUp ? petState.level + 1 : petState.level,
            });
            setWalking(false);
        }, 2000);
    }, [walking, petState, onStateChange]);

    const moodEmoji = petState.mood > 70 ? "😊" : petState.mood > 40 ? "😐" : "😢";
    const hungerEmoji = petState.hunger > 60 ? "😋" : petState.hunger > 30 ? "🤔" : "😫";

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold">{petState.name}&apos;s Status</h3>
                <span className="text-xs text-[var(--color-rune-dim)]">Level {petState.level}</span>
            </div>

            {/* Stat Bars */}
            <div className="space-y-2.5 mb-4">
                {[
                    { label: "Hunger", value: petState.hunger, emoji: hungerEmoji, color: "#e74c3c" },
                    { label: "Mood", value: petState.mood, emoji: moodEmoji, color: "#f39c12" },
                    { label: "Energy", value: petState.energy, emoji: "⚡", color: "#2ecc71" },
                ].map((stat) => (
                    <div key={stat.label}>
                        <div className="flex justify-between text-[10px] text-[var(--color-rune-dim)] mb-0.5">
                            <span>{stat.emoji} {stat.label}</span>
                            <span>{stat.value}%</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-[var(--color-glass)] overflow-hidden">
                            <div
                                className="h-1.5 rounded-full transition-all duration-700"
                                style={{
                                    width: `${stat.value}%`,
                                    background: stat.color,
                                    opacity: stat.value < 20 ? 1 : 0.7,
                                }}
                            />
                        </div>
                    </div>
                ))}

                {/* XP bar */}
                <div>
                    <div className="flex justify-between text-[10px] text-[var(--color-rune-dim)] mb-0.5">
                        <span>✨ XP</span>
                        <span>{petState.xp}/{petState.level * 20}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-[var(--color-glass)] overflow-hidden">
                        <div
                            className="h-1.5 rounded-full transition-all duration-700"
                            style={{
                                width: `${(petState.xp / (petState.level * 20)) * 100}%`,
                                background: "linear-gradient(90deg, var(--color-neon-dim), var(--color-neon))",
                            }}
                        />
                    </div>
                </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 mb-3">
                <button
                    onClick={walkPet}
                    disabled={walking || petState.energy < 15}
                    className="btn-neon px-4 py-2 text-xs flex-1 disabled:opacity-40"
                >
                    {walking ? "🚶 Walking..." : "🚶 Go for a walk"}
                </button>
            </div>

            {/* Food items */}
            <div className="flex gap-1.5 mb-3">
                {FOOD_ITEMS.map((food) => (
                    <button
                        key={food.name}
                        onClick={() => feedPet(food)}
                        disabled={feeding || petState.hunger >= 95}
                        className="flex-1 p-2 rounded-lg bg-[var(--color-glass)] hover:bg-[var(--color-glass-hover)] transition-colors text-center disabled:opacity-30"
                        title={`${food.name}: +${food.hungerRestore} hunger, +${food.moodBoost} mood`}
                    >
                        <span className="text-lg block">{food.emoji}</span>
                        <span className="text-[8px] text-[var(--color-rune-dim)]">{food.name}</span>
                    </button>
                ))}
            </div>

            {/* Walk result */}
            {walkResult && (
                <div className="p-3 rounded-lg bg-[var(--color-neon-glow)] border border-[rgba(0,255,136,0.1)] animate-[slideIn_0.3s_ease-out]">
                    <p className="text-xs text-[var(--color-rune)]">
                        <span className="text-lg mr-1.5">{walkResult.emoji}</span>
                        {petState.name} {walkResult.text}
                    </p>
                    <p className="text-[9px] text-[var(--color-neon)] mt-1">
                        +{walkResult.moodChange} mood · +{walkResult.xpGain} XP
                    </p>
                </div>
            )}
        </div>
    );
}

export type { PetState, PetSpecies };

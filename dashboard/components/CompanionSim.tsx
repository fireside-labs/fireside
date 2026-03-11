"use client";

import { useState, useEffect, useCallback } from "react";

type PetSpecies = "cat" | "dog" | "penguin" | "fox" | "owl" | "dragon";

interface PetState {
    name: string;
    species: PetSpecies;
    happiness: number; // 0-100
    xp: number;
    level: number;
    streak: number;    // consecutive days checked in
}

interface WalkEvent {
    text: string;
    happinessBoost: number;
    xpGain: number;
    emoji: string;
}

const WALK_EVENTS: Record<PetSpecies, WalkEvent[]> = {
    cat: [
        { text: "found a mysterious USB drive on the sidewalk", happinessBoost: 8, xpGain: 5, emoji: "🔌" },
        { text: "knocked a flower pot off a ledge. No regrets.", happinessBoost: 10, xpGain: 3, emoji: "🌸" },
        { text: "stared at a wall for 10 minutes. Enlightenment achieved.", happinessBoost: 6, xpGain: 8, emoji: "🧘" },
        { text: "hissed at a cloud. The cloud left.", happinessBoost: 12, xpGain: 4, emoji: "☁️" },
        { text: "found a warm spot of sunshine. Napped instantly.", happinessBoost: 15, xpGain: 2, emoji: "☀️" },
    ],
    dog: [
        { text: "met another dog! BEST. DAY. EVER!", happinessBoost: 15, xpGain: 5, emoji: "🐕" },
        { text: "found a stick. THE GREATEST STICK IN HISTORY!", happinessBoost: 12, xpGain: 3, emoji: "🪵" },
        { text: "chased a squirrel up a tree. Lost. But gained experience.", happinessBoost: 8, xpGain: 7, emoji: "🐿️" },
        { text: "got belly rubs from a stranger. Absolutely lost it.", happinessBoost: 18, xpGain: 4, emoji: "🥰" },
        { text: "rolled in something unidentified. Smells AMAZING.", happinessBoost: 10, xpGain: 2, emoji: "💩" },
    ],
    penguin: [
        { text: "organized local rocks by size. Very satisfying.", happinessBoost: 8, xpGain: 6, emoji: "🪨" },
        { text: "attempted to fly. Results: inconclusive.", happinessBoost: 5, xpGain: 4, emoji: "✈️" },
        { text: "found a fish. Filed it under 'snacks, misc.'", happinessBoost: 12, xpGain: 5, emoji: "🐟" },
        { text: "encountered slippery ice. Slid with dignity.", happinessBoost: 10, xpGain: 3, emoji: "🧊" },
        { text: "drafted a formal complaint about the weather.", happinessBoost: 3, xpGain: 8, emoji: "📝" },
    ],
    fox: [
        { text: "outsmarted a vending machine. Free snack acquired.", happinessBoost: 12, xpGain: 7, emoji: "🍫" },
        { text: "hid behind a bush for no reason. Just felt right.", happinessBoost: 8, xpGain: 3, emoji: "🌿" },
        { text: "found a shiny thing. Pocketed it. Don't ask.", happinessBoost: 10, xpGain: 5, emoji: "✨" },
        { text: "discovered a secret path. Led to a dead end. Classic.", happinessBoost: 5, xpGain: 6, emoji: "🗺️" },
        { text: "convinced a crow to trade secrets. Worth it.", happinessBoost: 15, xpGain: 8, emoji: "🐦‍⬛" },
    ],
    owl: [
        { text: "counted 47 stars. Lost count. Started over.", happinessBoost: 8, xpGain: 5, emoji: "⭐" },
        { text: "overheard a philosophical argument between trees.", happinessBoost: 10, xpGain: 8, emoji: "🌳" },
        { text: "found an old book. Read it twice.", happinessBoost: 12, xpGain: 10, emoji: "📖" },
        { text: "hooted at the moon. The moon did not respond.", happinessBoost: 5, xpGain: 3, emoji: "🌙" },
        { text: "meditated on the nature of wisdom. Fell asleep.", happinessBoost: 15, xpGain: 4, emoji: "💤" },
    ],
    dragon: [
        { text: "SET A BUSH ON FIRE. Accidentally. Mostly.", happinessBoost: 12, xpGain: 5, emoji: "🔥" },
        { text: "found a pile of coins. ADDED TO THE HOARD!", happinessBoost: 18, xpGain: 8, emoji: "💰" },
        { text: "tried to scare a mailman. He was unimpressed.", happinessBoost: 5, xpGain: 3, emoji: "📮" },
        { text: "practiced flying. Hit a tree. Trees: 1, Dragon: 0.", happinessBoost: 8, xpGain: 6, emoji: "🌲" },
        { text: "ROARED at the horizon. Something roared back. Concerning.", happinessBoost: 10, xpGain: 7, emoji: "🏔️" },
    ],
};

const TREAT_ITEMS = [
    { emoji: "🐟", name: "Fish", happinessBoost: 8 },
    { emoji: "🍖", name: "Treat", happinessBoost: 12 },
    { emoji: "🍰", name: "Cake", happinessBoost: 15 },
    { emoji: "⭐", name: "Pats", happinessBoost: 5 },
];

const WANDERED_TEXT: Record<PetSpecies, string> = {
    cat: "Your cat got bored and left. Interact to bring them back.",
    dog: "Your dog wandered off looking for you. They miss you!",
    penguin: "Your penguin has filed a formal notice of departure.",
    fox: "Your fox slipped away while you weren't looking.",
    owl: "Your owl flew off to contemplate elsewhere.",
    dragon: "Your dragon is off on a solo adventure. They'll be back.",
};

interface CompanionSimProps {
    petState: PetState;
    onStateChange: (state: PetState) => void;
}

export default function CompanionSim({ petState, onStateChange }: CompanionSimProps) {
    const [walkResult, setWalkResult] = useState<WalkEvent | null>(null);
    const [treating, setTreating] = useState(false);
    const [walking, setWalking] = useState(false);

    const isWandered = petState.happiness <= 0;

    // Passive happiness decay: ~1% every 12 minutes (720000ms)
    // Full → needs attention in ~2 hours
    useEffect(() => {
        const decay = setInterval(() => {
            onStateChange({
                ...petState,
                happiness: Math.max(0, petState.happiness - 1),
            });
        }, 720000); // 12 minutes
        return () => clearInterval(decay);
    }, [petState, onStateChange]);

    const treatPet = (treat: typeof TREAT_ITEMS[0]) => {
        setTreating(true);
        setTimeout(() => {
            onStateChange({
                ...petState,
                happiness: Math.min(100, petState.happiness + treat.happinessBoost),
                xp: petState.xp + 2,
            });
            setTreating(false);
        }, 600);
    };

    const walkPet = useCallback(() => {
        if (walking || isWandered) return;
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
                happiness: Math.min(100, petState.happiness + event.happinessBoost),
                xp: levelUp ? newXp - (petState.level * 20) : newXp,
                level: levelUp ? petState.level + 1 : petState.level,
            });
            setWalking(false);
        }, 2000);
    }, [walking, isWandered, petState, onStateChange]);

    // Bring pet back from wandering
    const callBack = () => {
        onStateChange({ ...petState, happiness: 20 });
    };

    const happinessEmoji = petState.happiness > 70 ? "💚" : petState.happiness > 30 ? "💛" : petState.happiness > 0 ? "🧡" : "💔";
    const happinessColor = petState.happiness > 70 ? "#2ecc71" : petState.happiness > 30 ? "#f39c12" : "#e74c3c";

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold">{petState.name}&apos;s Status</h3>
                <span className="text-xs text-[var(--color-rune-dim)]">Level {petState.level}</span>
            </div>

            {/* Wandered state */}
            {isWandered ? (
                <div className="text-center py-6">
                    <p className="text-3xl mb-3">🌫️</p>
                    <p className="text-sm text-[var(--color-rune-dim)] mb-1">{WANDERED_TEXT[petState.species]}</p>
                    <p className="text-[10px] text-[var(--color-rune-dim)] mb-4">{petState.name} misses you 🥺</p>
                    <button onClick={callBack} className="btn-neon px-6 py-2 text-sm">
                        🐾 Call {petState.name} Back
                    </button>
                </div>
            ) : (
                <>
                    {/* Happiness Bar */}
                    <div className="mb-4">
                        <div className="flex justify-between text-xs text-[var(--color-rune-dim)] mb-1">
                            <span>{happinessEmoji} Happiness</span>
                            <span>{petState.happiness}%</span>
                        </div>
                        <div className="h-2.5 rounded-full bg-[var(--color-glass)] overflow-hidden">
                            <div
                                className="h-2.5 rounded-full transition-all duration-700"
                                style={{ width: `${petState.happiness}%`, background: happinessColor }}
                            />
                        </div>
                        {petState.happiness < 30 && (
                            <p className="text-[10px] text-[var(--color-warning)] mt-1 animate-pulse">
                                Your companion misses you 🥺
                            </p>
                        )}
                    </div>

                    {/* XP bar */}
                    <div className="mb-4">
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

                    {/* Walk */}
                    <div className="flex gap-2 mb-3">
                        <button
                            onClick={walkPet}
                            disabled={walking}
                            className="btn-neon px-4 py-2 text-xs flex-1 disabled:opacity-40"
                        >
                            {walking ? "🚶 Walking..." : "🚶 Go for a walk"}
                        </button>
                    </div>

                    {/* Treats */}
                    <div className="flex gap-1.5 mb-3">
                        {TREAT_ITEMS.map((treat) => (
                            <button
                                key={treat.name}
                                onClick={() => treatPet(treat)}
                                disabled={treating || petState.happiness >= 100}
                                className="flex-1 p-2 rounded-lg bg-[var(--color-glass)] hover:bg-[var(--color-glass-hover)] transition-colors text-center disabled:opacity-30"
                                title={`${treat.name}: +${treat.happinessBoost}% happiness`}
                            >
                                <span className="text-lg block">{treat.emoji}</span>
                                <span className="text-[8px] text-[var(--color-rune-dim)]">{treat.name}</span>
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
                                +{walkResult.happinessBoost}% happiness · +{walkResult.xpGain} XP
                            </p>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export type { PetState, PetSpecies };

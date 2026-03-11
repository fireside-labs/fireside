"use client";

import { useState } from "react";
import type { PetSpecies } from "@/components/CompanionSim";

interface LootItem {
    item: string;
    chance: number;
    emoji?: string;
    happiness?: number;
    equippable?: boolean;
    rare?: boolean;
    description?: string;
}

interface Choice {
    text: string;
    reward: { xp?: number; happiness?: number; item?: string };
}

interface Adventure {
    type: "riddle" | "treasure" | "merchant" | "forage" | "lost_pet" | "weather" | "storyteller" | "challenge";
    intro: string;
    // Riddle
    riddle?: string;
    answer?: string;
    acceptAnswers?: string[];
    failText?: string;
    // Treasure
    lootTable?: LootItem[];
    // Choices (lost_pet, etc.)
    choices?: Choice[];
    // Weather / Storyteller
    story?: string;
    moral?: string;
    text?: string;
    // Rewards
    reward?: { xp?: number; happiness?: number; item?: string };
    failReward?: { xp?: number; happiness?: number };
    // Challenge
    miniGame?: string;
    winReward?: { xp?: number; happiness?: number; item?: string };
    loseReward?: { xp?: number; happiness?: number };
}

const TYPE_ICONS: Record<string, string> = {
    riddle: "🗿", treasure: "🎁", merchant: "👻", forage: "🌿",
    lost_pet: "🐾", weather: "⛈️", storyteller: "🎭", challenge: "🏴‍☠️",
};

const TYPE_LABELS: Record<string, string> = {
    riddle: "Riddle Guardian", treasure: "Treasure Chest", merchant: "Ghostly Merchant",
    forage: "Herb Foraging", lost_pet: "Lost Pet", weather: "Weather Event",
    storyteller: "The Storyteller", challenge: "The Challenger",
};

// Mock adventure for demo
const MOCK_ADVENTURES: Record<PetSpecies, Adventure> = {
    cat: {
        type: "riddle", intro: "A stone cat statue blocks the path. Its eyes glow. 'Answer my riddle, mortal.'",
        riddle: "I have cities but no houses, forests but no trees, water but no fish. What am I?",
        answer: "a map", acceptAnswers: ["map", "a map"],
        reward: { xp: 25, happiness: 15, item: "ancient_compass" },
        failText: "The statue yawns. 'Disappointing. Even for a human.'",
        failReward: { xp: 5, happiness: 5 },
    },
    dog: {
        type: "treasure", intro: "YOUR NOSE IS GOING CRAZY!! There's something buried here!!",
        lootTable: [
            { item: "golden_treat", chance: 0.4, emoji: "🍬✨", happiness: 30 },
            { item: "tiny_hat", chance: 0.3, emoji: "🎩", equippable: true },
            { item: "mystery_egg", chance: 0.2, emoji: "🥚", description: "It's warm..." },
            { item: "legendary_bone", chance: 0.1, emoji: "🦴✨", happiness: 50, rare: true },
        ],
    },
    penguin: {
        type: "storyteller", intro: "An old raven perches on a formal lectern. 'Shall I read the minutes of a prior age?'",
        story: "Once, a penguin filed a complaint about the temperature of the ocean. It took 400 years, but eventually, the currents shifted. Bureaucracy wins in the end.",
        moral: "Persistence outlasts everything.", reward: { xp: 10, happiness: 10, item: "story_fragment" },
    },
    fox: {
        type: "lost_pet", intro: "A tiny hamster is shivering behind a mushroom. It looks lost...",
        choices: [
            { text: "🤝 Help it find home", reward: { xp: 20, happiness: 25, item: "friendship_badge" } },
            { text: "🐟 Give it some food", reward: { xp: 10, happiness: 15 } },
            { text: "👋 Walk away", reward: { xp: 0, happiness: -5 } },
        ],
    },
    owl: {
        type: "forage", intro: "A patch of moonlit herbs rustles with potential. Your owl investigates...",
        lootTable: [
            { item: "moonpetal", chance: 0.5, emoji: "🌸", happiness: 25, description: "+25 happiness when used" },
            { item: "sunroot", chance: 0.3, emoji: "☀️", description: "Double XP on next walk" },
            { item: "dreamberry", chance: 0.2, emoji: "🫐", description: "Extra detailed morning briefing" },
        ],
    },
    dragon: {
        type: "challenge", intro: "A rival dragon lands with a THUD. 'I can roar louder than you! PROVE ME WRONG!'",
        miniGame: "tap_count",
        winReward: { xp: 30, happiness: 20, item: "champion_scarf" },
        loseReward: { xp: 10, happiness: 5 },
    },
};

interface AdventureCardProps {
    species: PetSpecies;
    petName: string;
    onComplete: (reward: { xp?: number; happiness?: number; item?: string }) => void;
    onDismiss: () => void;
}

export default function AdventureCard({ species, petName, onComplete, onDismiss }: AdventureCardProps) {
    const adventure = MOCK_ADVENTURES[species];
    const [phase, setPhase] = useState<"intro" | "active" | "result">("intro");
    const [riddleInput, setRiddleInput] = useState("");
    const [resultText, setResultText] = useState("");
    const [resultReward, setResultReward] = useState<{ xp?: number; happiness?: number; item?: string } | null>(null);
    const [tapCount, setTapCount] = useState(0);
    const [tapping, setTapping] = useState(false);

    const handleRiddleSubmit = () => {
        const isCorrect = adventure.acceptAnswers?.some(
            (a) => riddleInput.trim().toLowerCase() === a.toLowerCase()
        );
        if (isCorrect) {
            setResultText(`✅ Correct! ${petName} puffs with pride.`);
            setResultReward(adventure.reward || { xp: 10, happiness: 10 });
        } else {
            setResultText(adventure.failText || "Not quite...");
            setResultReward(adventure.failReward || { xp: 5 });
        }
        setPhase("result");
    };

    const handleTreasure = () => {
        const table = adventure.lootTable || [];
        const roll = Math.random();
        let cumulative = 0;
        for (const loot of table) {
            cumulative += loot.chance;
            if (roll <= cumulative) {
                const rareTag = loot.rare ? " ✨ RARE!" : "";
                setResultText(`${loot.emoji || "📦"} Found: ${loot.item.replace(/_/g, " ")}${rareTag}${loot.description ? ` — ${loot.description}` : ""}`);
                setResultReward({ xp: 15, happiness: loot.happiness || 10, item: loot.item });
                setPhase("result");
                return;
            }
        }
    };

    const handleChoice = (choice: Choice) => {
        setResultText(`${petName} chose: "${choice.text.slice(2)}"`);
        setResultReward(choice.reward);
        setPhase("result");
    };

    const handleChallenge = () => {
        setTapping(true);
        setTapCount(0);
        setTimeout(() => {
            setTapping(false);
            if (tapCount >= 10) {
                setResultText(`🏆 YOU WIN! ${petName} roars triumphantly!`);
                setResultReward(adventure.winReward || { xp: 20, happiness: 15 });
            } else {
                setResultText(`Close! ${tapCount}/10 taps. ${petName} shakes it off. "Next time!"`);
                setResultReward(adventure.loseReward || { xp: 5, happiness: 5 });
            }
            setPhase("result");
        }, 5000);
    };

    const handleCollect = () => {
        if (resultReward) onComplete(resultReward);
        onDismiss();
    };

    return (
        <div className="glass-card p-5 border-l-2 border-[var(--color-neon)]">
            {/* Header */}
            <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{TYPE_ICONS[adventure.type]}</span>
                <div>
                    <p className="text-xs text-[var(--color-neon)] font-medium">{TYPE_LABELS[adventure.type]}</p>
                    <p className="text-[9px] text-[var(--color-rune-dim)]">Adventure Encounter</p>
                </div>
            </div>

            {/* Intro */}
            {phase === "intro" && (
                <div>
                    <p className="text-sm text-[var(--color-rune)] mb-4 leading-relaxed italic">{adventure.intro}</p>
                    <button
                        onClick={() => {
                            setPhase("active");
                            if (adventure.type === "treasure" || adventure.type === "forage") handleTreasure();
                            if (adventure.type === "weather") {
                                setResultText(adventure.text || "Something happened!");
                                setResultReward(adventure.reward || { xp: 5 });
                                setPhase("result");
                            }
                            if (adventure.type === "storyteller") {
                                // Story shows in active, result after "continue"
                            }
                        }}
                        className="btn-neon px-4 py-2 text-xs w-full"
                    >
                        🗡️ Enter the Adventure
                    </button>
                </div>
            )}

            {/* Active — depends on type */}
            {phase === "active" && (
                <div>
                    {/* Riddle */}
                    {adventure.type === "riddle" && (
                        <div>
                            <p className="text-sm text-[var(--color-rune)] mb-3 italic">&quot;{adventure.riddle}&quot;</p>
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={riddleInput}
                                    onChange={(e) => setRiddleInput(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && handleRiddleSubmit()}
                                    placeholder="Your answer..."
                                    className="flex-1 bg-[var(--color-glass)] text-white text-sm px-3 py-2 rounded-lg border border-[var(--color-glass-border)] outline-none focus:border-[var(--color-neon)]"
                                />
                                <button onClick={handleRiddleSubmit} className="btn-neon px-4 py-2 text-xs">Answer</button>
                            </div>
                        </div>
                    )}

                    {/* Story */}
                    {adventure.type === "storyteller" && (
                        <div>
                            <p className="text-sm text-[var(--color-rune)] mb-2 leading-relaxed italic">&quot;{adventure.story}&quot;</p>
                            {adventure.moral && (
                                <p className="text-[10px] text-[var(--color-neon)] mb-3">💡 Moral: {adventure.moral}</p>
                            )}
                            <button
                                onClick={() => { setResultReward(adventure.reward || { xp: 10 }); setResultText(`📜 ${petName} remembers this story.`); setPhase("result"); }}
                                className="btn-neon px-4 py-2 text-xs w-full"
                            >
                                Continue →
                            </button>
                        </div>
                    )}

                    {/* Choices */}
                    {adventure.type === "lost_pet" && adventure.choices && (
                        <div className="space-y-2">
                            <p className="text-xs text-[var(--color-rune-dim)] mb-2">What will {petName} do?</p>
                            {adventure.choices.map((choice, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleChoice(choice)}
                                    className="w-full text-left p-2.5 rounded-lg bg-[var(--color-glass)] hover:bg-[var(--color-glass-hover)] transition-colors text-xs text-[var(--color-rune)]"
                                >
                                    {choice.text}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Challenge */}
                    {adventure.type === "challenge" && (
                        <div className="text-center">
                            {!tapping ? (
                                <button onClick={handleChallenge} className="btn-neon px-6 py-3 text-sm">
                                    ⚔️ Accept Challenge!
                                </button>
                            ) : (
                                <div>
                                    <p className="text-xs text-[var(--color-rune-dim)] mb-2">TAP! TAP! TAP! (10 taps in 5 seconds)</p>
                                    <button
                                        onClick={() => setTapCount((c) => c + 1)}
                                        className="w-24 h-24 rounded-full bg-[var(--color-neon-glow)] border-2 border-[var(--color-neon)] text-2xl active:scale-90 transition-transform"
                                    >
                                        {tapCount}
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Result */}
            {phase === "result" && (
                <div>
                    <p className="text-sm text-[var(--color-rune)] mb-2">{resultText}</p>
                    {resultReward && (
                        <div className="flex gap-3 text-[10px] text-[var(--color-neon)] mb-3">
                            {resultReward.xp && <span>+{resultReward.xp} XP</span>}
                            {resultReward.happiness && <span>+{resultReward.happiness}% 💚</span>}
                            {resultReward.item && <span>📦 {resultReward.item.replace(/_/g, " ")}</span>}
                        </div>
                    )}
                    <button onClick={handleCollect} className="btn-neon px-4 py-2 text-xs w-full">
                        ✨ Collect & Continue
                    </button>
                </div>
            )}
        </div>
    );
}

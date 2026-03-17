"use client";

import { useState, useEffect } from "react";
import CompanionPicker from "@/components/CompanionPicker";
import CompanionChat from "@/components/CompanionChat";
import TaskQueue from "@/components/TaskQueue";
import MorningBriefing from "@/components/MorningBriefing";
import DailyGift from "@/components/DailyGift";
import TeachMe from "@/components/TeachMe";
import type { PetSpecies } from "@/components/CompanionSim";

interface PetState {
    name: string;
    species: PetSpecies;
    happiness: number;
    xp: number;
    level: number;
    streak: number;
}

const SPECIES_EMOJI: Record<string, string> = {
    cat: "🐱", dog: "🐶", penguin: "🐧", fox: "🦊", owl: "🦉", dragon: "🐉",
};

const STORAGE_KEY = "fireside_companion";

function loadCompanion(): PetState | null {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    try { return JSON.parse(stored); } catch { return null; }
}

function saveCompanion(state: PetState) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export default function CompanionPage() {
    const [companion, setCompanion] = useState<PetState | null>(null);
    const [loaded, setLoaded] = useState(false);
    const [tab, setTab] = useState<"chat" | "tasks">("chat");

    useEffect(() => {
        setCompanion(loadCompanion());
        setLoaded(true);
    }, []);

    const handleAdopt = (species: PetSpecies, name: string) => {
        const newPet: PetState = {
            name, species, happiness: 80, xp: 0, level: 1, streak: 0,
        };
        setCompanion(newPet);
        saveCompanion(newPet);
    };

    const handleStateChange = (state: PetState) => {
        setCompanion(state);
        saveCompanion(state);
    };

    if (!loaded) return null;

    // No companion yet — show picker
    if (!companion) {
        return (
            <div className="max-w-md mx-auto pt-8">
                <CompanionPicker onSelect={handleAdopt} />
            </div>
        );
    }

    return (
        <div className="max-w-lg mx-auto">
            {/* Morning Briefing — shows once per day */}
            <MorningBriefing
                petName={companion.name}
                species={companion.species}
                onDismiss={() => { }}
            />

            {/* Daily Gift — shows once per day */}
            <DailyGift
                petName={companion.name}
                species={companion.species}
                onCollect={(gift) => {
                    if (gift.happinessBoost) {
                        handleStateChange({
                            ...companion,
                            happiness: Math.min(100, companion.happiness + gift.happinessBoost),
                        });
                    }
                }}
            />

            {/* Companion header */}
            <div className="flex items-center gap-4 mb-5 pt-2">
                <div className="w-16 h-16 rounded-xl bg-[var(--color-neon-glow)] flex items-center justify-center text-3xl border border-[var(--color-neon)]/20">
                    {SPECIES_EMOJI[companion.species] || "🦊"}
                </div>
                <div>
                    <h1 className="text-xl font-bold text-white">{companion.name}</h1>
                    <p className="text-xs text-[var(--color-rune-dim)]">
                        Your companion · {companion.happiness > 70 ? "Happy 😊" : "At the fireside 🔥"}
                    </p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-4 bg-[var(--color-glass)] rounded-lg p-1">
                {[
                    { id: "chat" as const, label: "💬 Chat" },
                    { id: "tasks" as const, label: "📋 Tasks" },
                ].map((t) => (
                    <button
                        key={t.id}
                        onClick={() => setTab(t.id)}
                        className="flex-1 py-2 text-xs rounded-md transition-colors"
                        style={{
                            background: tab === t.id ? "var(--color-glass-hover)" : "transparent",
                            color: tab === t.id ? "var(--color-neon)" : "var(--color-rune-dim)",
                        }}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {/* Tab content */}
            {tab === "chat" && (
                <div className="space-y-3">
                    <CompanionChat species={companion.species} petName={companion.name} mood={companion.happiness} />
                    <TeachMe petName={companion.name} species={companion.species} />
                </div>
            )}

            {tab === "tasks" && <TaskQueue />}
        </div>
    );
}

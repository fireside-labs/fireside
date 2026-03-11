"use client";

import { useState, useEffect } from "react";
import CompanionPicker from "@/components/CompanionPicker";
import CompanionSim from "@/components/CompanionSim";
import CompanionChat from "@/components/CompanionChat";
import TaskQueue from "@/components/TaskQueue";
import AvatarSprite from "@/components/AvatarSprite";
import type { PetState, PetSpecies } from "@/components/CompanionSim";

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
    const [tab, setTab] = useState<"chat" | "care" | "tasks">("chat");

    useEffect(() => {
        setCompanion(loadCompanion());
        setLoaded(true);
    }, []);

    const handleAdopt = (species: PetSpecies, name: string) => {
        const newPet: PetState = {
            name, species, hunger: 80, mood: 100, energy: 100, xp: 0, level: 1,
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
            {/* Companion header */}
            <div className="flex items-center gap-4 mb-5 pt-4">
                <AvatarSprite
                    config={{ style: "pixel", hairStyle: 0, hairColor: "#333", skinTone: "#fad7a0", outfit: companion.species, accessory: "none" }}
                    size={64}
                    status={companion.mood < 20 ? "hurt" : companion.mood < 50 ? "busy" : "online"}
                />
                <div>
                    <h1 className="text-xl font-bold text-white">{companion.name}</h1>
                    <p className="text-xs text-[var(--color-rune-dim)]">
                        Level {companion.level} {companion.species} · {companion.mood > 70 ? "Happy 😊" : companion.mood > 40 ? "Content 😐" : "Needs attention 😢"}
                    </p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-4 bg-[var(--color-glass)] rounded-lg p-1">
                {[
                    { id: "chat" as const, label: "💬 Chat", },
                    { id: "care" as const, label: "🐾 Care" },
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
                <CompanionChat species={companion.species} petName={companion.name} mood={companion.mood} />
            )}

            {tab === "care" && (
                <div className="space-y-4">
                    <CompanionSim petState={companion} onStateChange={handleStateChange} />

                    {/* Reset companion */}
                    <button
                        onClick={() => { localStorage.removeItem(STORAGE_KEY); setCompanion(null); }}
                        className="w-full text-center text-[10px] text-[var(--color-rune-dim)] hover:text-[var(--color-danger)] transition-colors py-2"
                    >
                        Release {companion.name} into the wild (reset)
                    </button>
                </div>
            )}

            {tab === "tasks" && <TaskQueue />}
        </div>
    );
}

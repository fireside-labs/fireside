"use client";

import { useState, useEffect } from "react";
import type { PetSpecies } from "@/components/CompanionSim";

const MORNING_PREFIX: Record<PetSpecies, string> = {
    cat: "*stretches lazily*",
    dog: "OMG GOOD MORNING!!",
    penguin: "Good morning. Status report:",
    fox: "*yawns cleverly*",
    owl: "The dawn brings clarity.",
    dragon: "THE SUN RISES! And so do I!",
};

interface MorningBriefingProps {
    petName: string;
    species: PetSpecies;
    onDismiss: () => void;
}

export default function MorningBriefing({ petName, species, onDismiss }: MorningBriefingProps) {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        // Check if we've shown the briefing today
        const lastShown = localStorage.getItem("fireside_morning_briefing");
        const today = new Date().toDateString();
        if (lastShown !== today) {
            setVisible(true);
            localStorage.setItem("fireside_morning_briefing", today);
        }
    }, []);

    if (!visible) return null;

    // Mock stats — would pull from real learning data
    const stats = {
        conversationsReviewed: Math.floor(Math.random() * 15) + 5,
        factsTested: Math.floor(Math.random() * 10) + 3,
        factsPassed: 0,
        smarterPct: (Math.random() * 3 + 0.5).toFixed(1),
        overnightFind: Math.random() > 0.5,
    };
    stats.factsPassed = stats.factsTested - Math.floor(Math.random() * 3);

    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

    // Get user name from localStorage
    const userName = (() => {
        try {
            const onboarding = localStorage.getItem("fireside_onboarding");
            if (onboarding) {
                const data = JSON.parse(onboarding);
                return data.user_name || data.name || "friend";
            }
        } catch { /* ignore */ }
        return "friend";
    })();

    return (
        <div className="glass-card p-5 border-l-2 border-[var(--color-neon)] mb-4 animate-[slideIn_0.4s_ease-out]">
            <div className="flex items-center justify-between mb-3">
                <p className="text-sm text-white font-medium">☀️ {greeting}, {userName}!</p>
                <button
                    onClick={() => { setVisible(false); onDismiss(); }}
                    className="text-[var(--color-rune-dim)] hover:text-white text-xs"
                >
                    ✕
                </button>
            </div>

            <p className="text-[10px] text-[var(--color-rune-dim)] italic mb-3">
                {MORNING_PREFIX[species]} {petName} here.
            </p>

            <div className="space-y-1.5 mb-3">
                <div className="flex items-center gap-2 text-xs text-[var(--color-rune)]">
                    <span>📚</span>
                    <span>Reviewed {stats.conversationsReviewed} conversations</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-[var(--color-rune)]">
                    <span>✅</span>
                    <span>Tested {stats.factsTested} facts ({stats.factsPassed} passed, {stats.factsTested - stats.factsPassed} refined)</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-[var(--color-neon)]">
                    <span>📈</span>
                    <span>Got {stats.smarterPct}% smarter overall</span>
                </div>
            </div>

            {stats.overnightFind && (
                <div className="p-2 rounded bg-[var(--color-glass)] mb-3">
                    <p className="text-[10px] text-[var(--color-rune)]">
                        🌙 {petName} went on an overnight walk and found a <span className="text-[var(--color-neon)]">moonpetal 🌿</span>! Check your inventory.
                    </p>
                </div>
            )}

            <button
                onClick={() => { setVisible(false); onDismiss(); }}
                className="btn-neon w-full py-2 text-xs"
            >
                Start a Fireside →
            </button>
        </div>
    );
}

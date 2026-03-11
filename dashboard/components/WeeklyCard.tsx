"use client";

import { useState } from "react";

interface WeeklyInsight {
    text: string;
    type: "learned" | "remembered" | "improved" | "suggestion";
}

const MOCK_INSIGHTS: WeeklyInsight[] = [
    { text: "Learned 12 new things about you", type: "learned" },
    { text: "Remembered 3 conversations", type: "remembered" },
    { text: "Knowledge check score: 89% → 94%", type: "improved" },
    { text: "You talked about your presentation anxiety twice. Want me to help you prepare next time?", type: "suggestion" },
];

const INSIGHT_ICONS: Record<string, string> = {
    learned: "📚",
    remembered: "🧠",
    improved: "📈",
    suggestion: "💡",
};

export default function WeeklyCard() {
    const [dismissed, setDismissed] = useState(false);

    if (dismissed) return null;

    const today = new Date();
    const isMonday = today.getDay() === 1;
    const weekLabel = isMonday ? "This Week" : "Last Week";

    return (
        <div className="glass-card p-5" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
            <div className="flex items-start justify-between mb-3">
                <div>
                    <h3 className="text-white font-semibold flex items-center gap-2">
                        🧠 {weekLabel} with Fireside
                    </h3>
                    <p className="text-[10px] text-[var(--color-rune-dim)] mt-0.5">
                        Monday summary — here&apos;s what happened
                    </p>
                </div>
                <button
                    onClick={() => setDismissed(true)}
                    className="text-[var(--color-rune-dim)] hover:text-white text-sm"
                    aria-label="Dismiss weekly summary"
                >
                    ✕
                </button>
            </div>

            <div className="space-y-2.5">
                {MOCK_INSIGHTS.map((insight, i) => (
                    <div key={i} className="flex items-start gap-2.5">
                        <span className="text-sm mt-0.5">{INSIGHT_ICONS[insight.type]}</span>
                        <p className={`text-xs leading-relaxed ${insight.type === "suggestion"
                                ? "text-[var(--color-neon)] italic"
                                : "text-[var(--color-rune)]"
                            }`}>
                            {insight.text}
                        </p>
                    </div>
                ))}
            </div>

            {/* Action buttons */}
            <div className="flex gap-2 mt-4">
                <button className="btn-neon px-4 py-1.5 text-xs flex-1">
                    Tell me more
                </button>
                <button
                    onClick={() => setDismissed(true)}
                    className="px-4 py-1.5 text-xs rounded-lg border border-[var(--color-glass-border)] text-[var(--color-rune-dim)] hover:text-white hover:bg-[var(--color-glass-hover)] transition-colors flex-1"
                >
                    Got it
                </button>
            </div>
        </div>
    );
}

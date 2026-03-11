"use client";

import { useState } from "react";

interface SliderPair {
    id: string;
    leftLabel: string;
    rightLabel: string;
    leftEmoji: string;
    rightEmoji: string;
    value: number; // 0.0 - 1.0
}

interface PersonalitySlidersProps {
    values: Record<string, number>;
    onChange?: (id: string, value: number) => void;
    readOnly?: boolean;
    showPreview?: boolean;
}

const SLIDER_PAIRS: Omit<SliderPair, "value">[] = [
    { id: "creative_precise", leftLabel: "Creative", rightLabel: "Precise", leftEmoji: "🎨", rightEmoji: "🎯" },
    { id: "verbose_concise", leftLabel: "Detailed", rightLabel: "Brief", leftEmoji: "📝", rightEmoji: "⚡" },
    { id: "bold_cautious", leftLabel: "Bold", rightLabel: "Cautious", leftEmoji: "🦁", rightEmoji: "🛡️" },
    { id: "warm_formal", leftLabel: "Warm", rightLabel: "Formal", leftEmoji: "😊", rightEmoji: "💼" },
];

const PREVIEW_RESPONSES: Record<string, { low: string; mid: string; high: string }> = {
    creative_precise: {
        low: "Based on the data, the optimal solution is X with 94% confidence.",
        mid: "I'd suggest trying X — it's the most reliable approach, though Y could also work.",
        high: "What if we tried something completely different? Here's a wild idea...",
    },
    verbose_concise: {
        low: "Use X.",
        mid: "I'd recommend X. Here's why: it handles edge cases well and is easy to maintain.",
        high: "Great question! Let me walk you through this step by step. First, we need to understand the underlying problem. The core issue is...",
    },
    bold_cautious: {
        low: "I'd recommend testing this thoroughly before deploying. Let me verify a few things first.",
        mid: "This looks good to ship. I've checked the main cases — want me to run a final test?",
        high: "Ship it! I already pushed to prod. We'll fix any issues as they come up. 🚀",
    },
    warm_formal: {
        low: "Per your request, please find the analysis attached. Regards.",
        mid: "Here's what I found — let me know if you need anything else!",
        high: "Hey! 😊 So I looked into this and omg it's actually really cool — check this out!",
    },
};

function getPreviewText(values: Record<string, number>): string {
    // Pick the most extreme slider to show its preview
    let maxDelta = 0;
    let activeId = "creative_precise";
    for (const pair of SLIDER_PAIRS) {
        const val = values[pair.id] ?? 0.5;
        const delta = Math.abs(val - 0.5);
        if (delta > maxDelta) {
            maxDelta = delta;
            activeId = pair.id;
        }
    }
    const val = values[activeId] ?? 0.5;
    const responses = PREVIEW_RESPONSES[activeId];
    if (val < 0.33) return responses.low;
    if (val > 0.67) return responses.high;
    return responses.mid;
}

export default function PersonalitySliders({ values, onChange, readOnly, showPreview = true }: PersonalitySlidersProps) {
    return (
        <div className="space-y-4">
            {SLIDER_PAIRS.map((pair) => {
                const val = values[pair.id] ?? 0.5;
                return (
                    <div key={pair.id}>
                        <div className="flex justify-between mb-1.5">
                            <span className="text-xs text-[var(--color-rune)]">
                                {pair.leftEmoji} {pair.leftLabel}
                            </span>
                            <span className="text-xs text-[var(--color-rune)]">
                                {pair.rightLabel} {pair.rightEmoji}
                            </span>
                        </div>
                        <div className="relative h-6 flex items-center">
                            {/* Track */}
                            <div className="absolute inset-x-0 h-2 rounded-full bg-[var(--color-glass)]">
                                {/* Fill */}
                                <div
                                    className="h-2 rounded-full transition-all"
                                    style={{
                                        width: `${val * 100}%`,
                                        background: "linear-gradient(90deg, var(--color-neon-dim), var(--color-neon))",
                                        opacity: 0.6,
                                    }}
                                />
                            </div>
                            {/* 5 notch marks */}
                            <div className="absolute inset-x-0 flex justify-between px-0.5">
                                {[0, 0.25, 0.5, 0.75, 1].map((n) => (
                                    <div
                                        key={n}
                                        className="w-1 h-1 rounded-full"
                                        style={{
                                            background: Math.abs(val - n) < 0.13 ? "var(--color-neon)" : "var(--color-glass-border)",
                                        }}
                                    />
                                ))}
                            </div>
                            {/* Range input */}
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.05"
                                value={val}
                                onChange={(e) => onChange?.(pair.id, parseFloat(e.target.value))}
                                disabled={readOnly}
                                aria-label={`${pair.leftLabel} to ${pair.rightLabel}`}
                                className="absolute inset-x-0 w-full h-6 opacity-0 cursor-pointer disabled:cursor-default"
                                style={{ zIndex: 10 }}
                            />
                            {/* Thumb indicator */}
                            <div
                                className="absolute w-4 h-4 rounded-full border-2 border-[var(--color-neon)] bg-[var(--color-void-light)] shadow-[0_0_8px_var(--color-neon-glow-strong)] transition-all pointer-events-none"
                                style={{ left: `calc(${val * 100}% - 8px)` }}
                            />
                        </div>
                    </div>
                );
            })}

            {/* Preview text */}
            {showPreview && !readOnly && (
                <div className="mt-3 p-3 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)]">
                    <p className="text-[10px] text-[var(--color-rune-dim)] mb-1.5">💬 Example response with these settings:</p>
                    <p className="text-xs text-[var(--color-rune)] italic leading-relaxed">
                        &quot;{getPreviewText(values)}&quot;
                    </p>
                </div>
            )}
        </div>
    );
}


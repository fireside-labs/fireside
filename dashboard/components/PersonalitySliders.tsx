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
}

const SLIDER_PAIRS: Omit<SliderPair, "value">[] = [
    { id: "creative_precise", leftLabel: "Creative", rightLabel: "Precise", leftEmoji: "🎨", rightEmoji: "🎯" },
    { id: "verbose_concise", leftLabel: "Detailed", rightLabel: "Brief", leftEmoji: "📝", rightEmoji: "⚡" },
    { id: "bold_cautious", leftLabel: "Bold", rightLabel: "Cautious", leftEmoji: "🦁", rightEmoji: "🛡️" },
    { id: "warm_formal", leftLabel: "Warm", rightLabel: "Formal", leftEmoji: "😊", rightEmoji: "💼" },
];

export default function PersonalitySliders({ values, onChange, readOnly }: PersonalitySlidersProps) {
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
        </div>
    );
}

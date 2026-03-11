"use client";

import { SelfModel } from "@/lib/api";

interface Props {
    model: SelfModel;
    onReflect?: () => void;
    reflecting?: boolean;
}

export default function SelfModelCard({ model, onReflect, reflecting }: Props) {
    const confidencePct = Math.round(model.confidence * 100);

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold text-sm">🪞 Self-Model</h3>
                <span className="text-xs text-[var(--color-rune-dim)]">
                    {model.reflection_count} reflections
                </span>
            </div>

            {/* Confidence Ring */}
            <div className="flex items-center gap-4 mb-4">
                <div className="confidence-ring">
                    <svg width="56" height="56" viewBox="0 0 56 56">
                        <circle
                            cx="28" cy="28" r="24"
                            fill="none"
                            stroke="var(--color-void-lighter)"
                            strokeWidth="4"
                        />
                        <circle
                            cx="28" cy="28" r="24"
                            fill="none"
                            stroke="var(--color-neon)"
                            strokeWidth="4"
                            strokeLinecap="round"
                            strokeDasharray={2 * Math.PI * 24}
                            strokeDashoffset={2 * Math.PI * 24 * (1 - model.confidence)}
                            transform="rotate(-90 28 28)"
                            style={{ transition: "stroke-dashoffset 0.8s ease" }}
                        />
                    </svg>
                    <span className="confidence-ring-text">{confidencePct}%</span>
                </div>
                <div>
                    <div className="text-white text-sm font-medium">{model.node_name}</div>
                    <div className="text-xs text-[var(--color-rune-dim)]">
                        Last reflect: {new Date(model.last_reflection).toLocaleTimeString()}
                    </div>
                </div>
            </div>

            {/* Strengths */}
            <div className="mb-3">
                <span className="text-xs text-[var(--color-rune-dim)] block mb-2">Strengths</span>
                <div className="flex flex-wrap gap-1.5">
                    {model.strengths.map((s) => (
                        <span key={s} className="tag tag-strength">{s}</span>
                    ))}
                </div>
            </div>

            {/* Weaknesses */}
            <div className="mb-4">
                <span className="text-xs text-[var(--color-rune-dim)] block mb-2">Weaknesses</span>
                <div className="flex flex-wrap gap-1.5">
                    {model.weaknesses.map((w) => (
                        <span key={w} className="tag tag-weakness">{w}</span>
                    ))}
                </div>
            </div>

            {/* Reflect Button */}
            {onReflect && (
                <button
                    onClick={onReflect}
                    disabled={reflecting}
                    className="btn-neon w-full text-xs py-2"
                    style={{ opacity: reflecting ? 0.5 : 1 }}
                >
                    {reflecting ? "Reflecting..." : "🪞 Trigger Reflection"}
                </button>
            )}
        </div>
    );
}

"use client";

import { Hypothesis } from "@/lib/api";

interface Props {
    hypothesis: Hypothesis;
    onTest?: (id: string, result: "confirmed" | "refuted") => void;
}

export default function HypothesisCard({ hypothesis, onTest }: Props) {
    const statusColors: Record<string, string> = {
        active: "var(--color-info)",
        confirmed: "var(--color-neon)",
        refuted: "var(--color-danger)",
    };

    const statusIcons: Record<string, string> = {
        active: "🧪",
        confirmed: "✅",
        refuted: "❌",
    };

    const confidencePct = Math.round(hypothesis.confidence * 100);

    return (
        <div className="glass-card p-5 hypothesis-card">
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="text-lg">{statusIcons[hypothesis.status]}</span>
                    <h4 className="text-white font-semibold text-sm truncate">{hypothesis.title}</h4>
                </div>
                <span
                    className="hypothesis-badge text-xs px-2 py-1 rounded-full font-medium whitespace-nowrap ml-2"
                    style={{
                        color: statusColors[hypothesis.status],
                        background: statusColors[hypothesis.status] + "18",
                        border: "1px solid " + statusColors[hypothesis.status] + "40",
                    }}
                >
                    {hypothesis.status}
                </span>
            </div>

            {/* Description */}
            <p className="text-xs text-[var(--color-rune-dim)] mb-3 leading-relaxed line-clamp-2">
                {hypothesis.description}
            </p>

            {/* Confidence Bar */}
            <div className="mb-3">
                <div className="flex justify-between text-xs mb-1">
                    <span className="text-[var(--color-rune-dim)]">Confidence</span>
                    <span className="font-mono" style={{ color: statusColors[hypothesis.status] }}>
                        {confidencePct}%
                    </span>
                </div>
                <div className="confidence-bar-track">
                    <div
                        className="confidence-bar-fill"
                        style={{
                            width: confidencePct + "%",
                            background: "linear-gradient(90deg, " + statusColors[hypothesis.status] + "80, " + statusColors[hypothesis.status] + ")",
                        }}
                    />
                </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--color-rune-dim)]">
                    {hypothesis.source_node} · {new Date(hypothesis.created_at).toLocaleDateString()}
                </span>
                {hypothesis.status === "active" && onTest && (
                    <div className="flex gap-2">
                        <button
                            onClick={() => onTest(hypothesis.id, "confirmed")}
                            className="text-xs px-2 py-1 rounded border border-[var(--color-neon)] text-[var(--color-neon)] hover:bg-[var(--color-neon-glow)] transition-colors"
                        >
                            Confirm
                        </button>
                        <button
                            onClick={() => onTest(hypothesis.id, "refuted")}
                            className="text-xs px-2 py-1 rounded border border-[var(--color-danger)] text-[var(--color-danger)] hover:bg-[rgba(255,68,102,0.1)] transition-colors"
                        >
                            Refute
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

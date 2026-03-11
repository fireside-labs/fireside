"use client";

import type { PipelineStage } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
    passed: "var(--color-neon)",
    running: "var(--color-info)",
    failed: "var(--color-danger)",
    pending: "var(--color-rune-dim)",
};

const STATUS_ICONS: Record<string, string> = {
    passed: "✔",
    running: "🔄",
    failed: "❌",
    pending: "○",
};

export default function StageTimeline({ stages }: { stages: PipelineStage[] }) {
    return (
        <div className="flex items-center gap-1 w-full overflow-x-auto py-2">
            {stages.map((stage, i) => (
                <div key={stage.name} className="flex items-center">
                    {/* Node */}
                    <div className="flex flex-col items-center gap-1 min-w-[72px]">
                        <div
                            className="w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 transition-all duration-300"
                            style={{
                                borderColor: STATUS_COLORS[stage.status],
                                background: stage.status === "running" ? STATUS_COLORS[stage.status] + "22" : "transparent",
                                boxShadow: stage.status === "running" ? `0 0 12px ${STATUS_COLORS[stage.status]}44` : "none",
                            }}
                        >
                            {STATUS_ICONS[stage.status]}
                        </div>
                        <span className="text-xs text-center" style={{ color: STATUS_COLORS[stage.status] }}>
                            {stage.name}
                        </span>
                        <span className="text-[10px] text-[var(--color-rune-dim)]">{stage.agent}</span>
                    </div>

                    {/* Connector */}
                    {i < stages.length - 1 && (
                        <div
                            className="h-0.5 w-8 mx-1 transition-all duration-500"
                            style={{
                                background: stage.status === "passed" ? STATUS_COLORS.passed : "var(--color-glass-border)",
                            }}
                        />
                    )}
                </div>
            ))}
        </div>
    );
}

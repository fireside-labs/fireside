"use client";

import Link from "next/link";
import type { Pipeline } from "@/lib/api";
import StageTimeline from "./StageTimeline";

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
    running: { label: "🔄 Running", color: "var(--color-info)", bg: "rgba(68,170,255,0.12)" },
    completed: { label: "✅ Complete", color: "var(--color-neon)", bg: "var(--color-neon-glow)" },
    failed: { label: "❌ Failed", color: "var(--color-danger)", bg: "rgba(255,68,102,0.12)" },
    escalated: { label: "🖐 Needs Review", color: "var(--color-warning)", bg: "rgba(255,170,34,0.12)" },
    cancelled: { label: "⏹ Cancelled", color: "var(--color-rune-dim)", bg: "var(--color-glass)" },
};

export default function PipelineCard({ pipeline }: { pipeline: Pipeline }) {
    const badge = STATUS_BADGE[pipeline.status] || STATUS_BADGE.running;
    const progress = pipeline.stages.filter(s => s.status === "passed").length / pipeline.stages.length;

    return (
        <Link href={`/pipeline/${pipeline.id}`}>
            <div className="glass-card p-5 cursor-pointer group">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                    <div>
                        <h3 className="text-white font-semibold group-hover:text-[var(--color-neon)] transition-colors">
                            {pipeline.title}
                        </h3>
                        <p className="text-xs text-[var(--color-rune-dim)] mt-0.5">
                            Iteration {pipeline.iteration}/{pipeline.max_iterations}
                            {pipeline.eta_minutes && ` · ETA ~${pipeline.eta_minutes}min`}
                        </p>
                    </div>
                    <span
                        className="text-xs px-2 py-1 rounded-full font-medium"
                        style={{ color: badge.color, background: badge.bg }}
                    >
                        {badge.label}
                    </span>
                </div>

                {/* Progress bar */}
                <div className="confidence-bar-track mb-3">
                    <div
                        className="confidence-bar-fill transition-all duration-500"
                        style={{ width: `${progress * 100}%`, background: badge.color }}
                    />
                </div>

                {/* Stage Timeline */}
                <StageTimeline stages={pipeline.stages} />

                {/* Token info for completed */}
                {pipeline.status === "completed" && (
                    <div className="mt-3 pt-3 border-t border-[var(--color-glass-border)] flex gap-4 text-xs text-[var(--color-rune-dim)]">
                        <span>☁️ {(pipeline.cloud_tokens / 1000).toFixed(1)}K cloud</span>
                        <span>🖥️ {(pipeline.local_tokens / 1000).toFixed(0)}K local (free)</span>
                    </div>
                )}
            </div>
        </Link>
    );
}

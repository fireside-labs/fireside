"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getPipeline, cancelPipeline, advancePipeline } from "@/lib/api";
import type { Pipeline } from "@/lib/api";
import StageTimeline from "@/components/StageTimeline";
import { useToast } from "@/components/Toast";
import { useWebSocket } from "@/hooks/useWebSocket";

const VERDICT_COLORS: Record<string, string> = {
    PASS: "var(--color-neon)",
    PROGRESS: "var(--color-info)",
    FAIL: "var(--color-danger)",
    REGRESS: "var(--color-warning)",
};

export default function PipelineDetailPage() {
    const { id } = useParams<{ id: string }>();
    const [pipeline, setPipeline] = useState<Pipeline | null>(null);
    const [loading, setLoading] = useState(true);
    const { toast } = useToast();
    const { lastEvent } = useWebSocket();

    useEffect(() => {
        if (id) {
            getPipeline(id).then((data) => {
                setPipeline(data);
                setLoading(false);
            });
        }
    }, [id]);

    // Real-time updates
    useEffect(() => {
        if (lastEvent?.topic === "pipeline" && id) {
            getPipeline(id).then(setPipeline);
        }
    }, [lastEvent, id]);

    const handleCancel = async () => {
        if (id) {
            await cancelPipeline(id);
            toast("Pipeline cancelled", "info");
        }
    };

    const handleAdvance = async () => {
        if (id) {
            await advancePipeline(id);
            toast("Force advancing pipeline", "warning");
        }
    };

    if (loading) {
        return (
            <div className="page-enter max-w-5xl">
                <div className="glass-card p-8 animate-pulse">
                    <div className="h-6 w-64 bg-[var(--color-void-lighter)] rounded mb-4" />
                    <div className="h-4 w-48 bg-[var(--color-void-lighter)] rounded" />
                </div>
            </div>
        );
    }

    if (!pipeline) {
        return (
            <div className="page-enter max-w-5xl text-center py-20">
                <p className="text-[var(--color-rune-dim)]">Pipeline not found</p>
            </div>
        );
    }

    return (
        <div className="page-enter max-w-5xl">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white mb-1">{pipeline.title}</h1>
                <p className="text-sm text-[var(--color-rune-dim)]">
                    {pipeline.status === "running" ? "🔄" : pipeline.status === "completed" ? "✅" : pipeline.status === "escalated" ? "🖐" : "⏹"}
                    {" "}{pipeline.status.charAt(0).toUpperCase() + pipeline.status.slice(1)} · Iteration {pipeline.iteration}/{pipeline.max_iterations} · Started {new Date(pipeline.started_at).toLocaleTimeString()}
                    {pipeline.eta_minutes && ` · ETA ~${pipeline.eta_minutes}min`}
                </p>
            </div>

            {/* Stage Timeline */}
            <div className="glass-card p-5 mb-6">
                <h2 className="text-sm font-semibold text-[var(--color-rune-dim)] uppercase tracking-wider mb-3">Stage Timeline</h2>
                <StageTimeline stages={pipeline.stages} />
            </div>

            {/* Escalation warning */}
            {pipeline.status === "escalated" && (
                <div className="glass-card p-5 mb-6" style={{ borderLeft: "3px solid var(--color-warning)" }}>
                    <h3 className="text-white font-semibold mb-2">⚠️ REGRESSION DETECTED — Iteration {pipeline.iteration}</h3>
                    <p className="text-sm text-[var(--color-rune)] mb-4">{pipeline.iterations[0]?.summary}</p>
                    <div className="flex gap-3">
                        <button className="btn-neon text-xs px-3 py-1.5">🔄 Retry from Last Good</button>
                        <button className="text-xs px-3 py-1.5 rounded border border-[var(--color-glass-border)] text-[var(--color-rune)] hover:text-white transition-colors">📝 Give Guidance</button>
                        <button onClick={handleCancel} className="text-xs px-3 py-1.5 rounded border border-[var(--color-danger)] text-[var(--color-danger)] hover:bg-[rgba(255,68,102,0.12)] transition-colors">❌ Cancel</button>
                    </div>
                </div>
            )}

            {/* Completion stats */}
            {pipeline.status === "completed" && (
                <div className="glass-card p-5 mb-6" style={{ borderLeft: "3px solid var(--color-neon)" }}>
                    <h3 className="text-white font-semibold mb-3">✅ Pipeline Complete</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                        <div><p className="text-lg font-bold text-white">{pipeline.iteration}</p><p className="text-xs text-[var(--color-rune-dim)]">Iterations</p></div>
                        <div><p className="text-lg font-bold text-white">{pipeline.iterations[0]?.tests_total}</p><p className="text-xs text-[var(--color-rune-dim)]">Tests Passing</p></div>
                        <div><p className="text-lg font-bold text-[var(--color-neon)]">{(pipeline.local_tokens / 1000).toFixed(0)}K</p><p className="text-xs text-[var(--color-rune-dim)]">Local (free)</p></div>
                        <div><p className="text-lg font-bold text-[var(--color-info)]">{(pipeline.cloud_tokens / 1000).toFixed(1)}K</p><p className="text-xs text-[var(--color-rune-dim)]">Cloud tokens</p></div>
                    </div>
                    {pipeline.lessons && (
                        <div>
                            <p className="text-xs text-[var(--color-rune-dim)] uppercase tracking-wider mb-2">Lessons Learned (by Muninn)</p>
                            <ul className="space-y-1">
                                {pipeline.lessons.map((l, i) => (
                                    <li key={i} className="text-sm text-[var(--color-rune)] flex gap-2">
                                        <span className="text-[var(--color-neon)]">•</span> {l}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {/* Iteration History */}
            <div className="mb-6">
                <h2 className="text-sm font-semibold text-[var(--color-rune-dim)] uppercase tracking-wider mb-3">Iteration History</h2>
                <div className="space-y-2 stagger-in">
                    {pipeline.iterations.map((iter) => (
                        <div key={iter.number} className="glass-card p-4">
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-semibold text-white">Iteration {iter.number}</span>
                                    {iter.number === pipeline.iteration && pipeline.status === "running" && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[rgba(68,170,255,0.12)] text-[var(--color-info)]">current</span>
                                    )}
                                </div>
                                <span
                                    className="text-xs font-bold px-2 py-0.5 rounded"
                                    style={{
                                        color: VERDICT_COLORS[iter.verdict],
                                        background: VERDICT_COLORS[iter.verdict] + "18",
                                    }}
                                >
                                    {iter.verdict}
                                </span>
                            </div>
                            <p className="text-sm text-[var(--color-rune)]">{iter.summary}</p>
                            {iter.tests_total && (
                                <div className="mt-2 flex items-center gap-2">
                                    <div className="flex-1 confidence-bar-track">
                                        <div
                                            className="confidence-bar-fill"
                                            style={{
                                                width: `${(iter.tests_passing! / iter.tests_total) * 100}%`,
                                                background: iter.verdict === "PASS" ? "var(--color-neon)" : "var(--color-info)",
                                            }}
                                        />
                                    </div>
                                    <span className="text-xs text-[var(--color-rune-dim)]">
                                        {iter.tests_passing}/{iter.tests_total} tests
                                    </span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Actions */}
            {pipeline.status === "running" && (
                <div className="flex gap-3">
                    <button onClick={handleCancel} className="text-xs px-4 py-2 rounded border border-[var(--color-danger)] text-[var(--color-danger)] hover:bg-[rgba(255,68,102,0.12)] transition-colors">
                        Cancel Pipeline
                    </button>
                    <button onClick={handleAdvance} className="text-xs px-4 py-2 rounded border border-[var(--color-warning)] text-[var(--color-warning)] hover:bg-[rgba(255,170,34,0.12)] transition-colors">
                        Force Advance
                    </button>
                </div>
            )}
        </div>
    );
}

"use client";

import type { ModelRouterStats } from "@/lib/api";

export default function ModelRouterStatsView({ stats }: { stats: ModelRouterStats }) {
    const maxTokens = Math.max(...stats.breakdown.map(b => b.tokens));

    return (
        <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 stagger-in">
                <div className="glass-card p-4 text-center">
                    <p className="text-xl font-bold text-white">{(stats.total_tokens / 1000).toFixed(0)}K</p>
                    <p className="text-xs text-[var(--color-rune-dim)]">Total Tokens</p>
                </div>
                <div className="glass-card p-4 text-center">
                    <p className="text-xl font-bold text-[var(--color-neon)]">${stats.total_cost.toFixed(2)}</p>
                    <p className="text-xs text-[var(--color-rune-dim)]">Total Cost</p>
                </div>
                <div className="glass-card p-4 text-center">
                    <p className="text-xl font-bold text-white">{(stats.local_tokens / 1000).toFixed(0)}K</p>
                    <p className="text-xs text-[var(--color-rune-dim)]">Local (Free)</p>
                </div>
                <div className="glass-card p-4 text-center">
                    <p className="text-xl font-bold text-[var(--color-info)]">{(stats.cloud_tokens / 1000).toFixed(0)}K</p>
                    <p className="text-xs text-[var(--color-rune-dim)]">Cloud (Paid)</p>
                </div>
            </div>

            {/* Token spend bar chart */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-4">Token Spend by Model</h3>
                <div className="space-y-3">
                    {stats.breakdown.map((b) => (
                        <div key={b.model} className="flex items-center gap-3">
                            <span className="text-xs text-[var(--color-rune)] w-36 truncate font-mono">{b.model}</span>
                            <div className="flex-1 confidence-bar-track">
                                <div
                                    className="confidence-bar-fill transition-all duration-500"
                                    style={{
                                        width: `${(b.tokens / maxTokens) * 100}%`,
                                        background: b.is_local ? "var(--color-neon)" : "var(--color-info)",
                                    }}
                                />
                            </div>
                            <span className="text-xs text-[var(--color-rune-dim)] w-14 text-right">
                                {(b.tokens / 1000).toFixed(1)}K
                            </span>
                            <span className="text-xs w-12 text-right" style={{ color: b.cost === 0 ? "var(--color-neon)" : "var(--color-warning)" }}>
                                {b.cost === 0 ? "Free" : `$${b.cost.toFixed(2)}`}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Routing rules */}
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold mb-4">Routing Rules</h3>
                <div className="space-y-2">
                    {stats.routing_rules.map((r) => (
                        <div key={r.task_type} className="flex items-center gap-3 text-sm">
                            <span className="text-xs px-2 py-0.5 rounded bg-[var(--color-glass)] text-[var(--color-neon)] font-mono w-20 text-center">
                                {r.task_type}
                            </span>
                            <span className="text-xs text-white font-medium">→ {r.model}</span>
                            <span className="text-xs text-[var(--color-rune-dim)] flex-1">{r.reason}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

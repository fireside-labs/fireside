"use client";

import Link from "next/link";
import type { MarketplaceAgent } from "@/lib/api";

function StarRating({ rating }: { rating: number }) {
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.3;
    return (
        <span className="text-amber-400 text-sm tracking-tight">
            {"★".repeat(full)}
            {half && "½"}
            {"☆".repeat(5 - full - (half ? 1 : 0))}
        </span>
    );
}

export default function AgentCard({ agent }: { agent: MarketplaceAgent }) {
    return (
        <Link href={`/marketplace/${agent.id}`}>
            <div className="glass-card p-5 cursor-pointer group h-full flex flex-col">
                {/* Header */}
                <div className="flex items-start gap-3 mb-3">
                    <div className="w-12 h-12 rounded-xl bg-[var(--color-glass)] flex items-center justify-center text-2xl">
                        {agent.avatar}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="text-white font-semibold group-hover:text-[var(--color-neon)] transition-colors truncate">
                            {agent.name}
                        </h3>
                        <p className="text-xs text-[var(--color-rune-dim)]">by {agent.author}</p>
                    </div>
                    {agent.price === 0 ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-neon-glow)] text-[var(--color-neon)] font-bold">
                            Free
                        </span>
                    ) : (
                        <span className="text-sm font-bold text-white">${agent.price.toFixed(2)}</span>
                    )}
                </div>

                {/* Description */}
                <p className="text-xs text-[var(--color-rune)] leading-relaxed mb-3 line-clamp-2 flex-1">
                    {agent.description}
                </p>

                {/* Stats */}
                <div className="flex items-center gap-3 mb-3">
                    <div className="flex items-center gap-1">
                        <StarRating rating={agent.rating} />
                        <span className="text-xs text-[var(--color-rune-dim)]">({agent.review_count})</span>
                    </div>
                </div>

                {/* Trust signals */}
                <div className="flex flex-wrap gap-2 text-[10px]">
                    <span className="px-2 py-0.5 rounded-full bg-[var(--color-glass)]" style={{
                        color: agent.crucible_survival >= 95 ? "var(--color-neon)" : agent.crucible_survival >= 85 ? "var(--color-info)" : "var(--color-warning)"
                    }}>
                        ✅ {agent.crucible_survival}% reliable
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-[var(--color-glass)] text-[var(--color-rune)]">
                        🧠 Knows {agent.procedures.toLocaleString()} things
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-[var(--color-glass)] text-[var(--color-rune)]">
                        📅 {Math.round(agent.days_evolved / 30)} months trained
                    </span>
                </div>

                {/* Model requirements */}
                <div className="mt-3 pt-3 border-t border-[var(--color-glass-border)] flex items-center gap-2">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[rgba(68,170,255,0.12)] text-[var(--color-info)]">
                        AI Memory {agent.model_requirements.gpu_vram}GB+
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[rgba(68,170,255,0.12)] text-[var(--color-info)]">
                        RAM {agent.model_requirements.ram}GB+
                    </span>
                    <span className="text-[10px] text-[var(--color-rune-dim)] ml-auto">
                        {agent.installs} installs
                    </span>
                </div>
            </div>
        </Link>
    );
}

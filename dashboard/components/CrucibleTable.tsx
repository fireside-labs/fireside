"use client";

import { useState } from "react";
import type { CrucibleProcedure } from "@/lib/api";

const VERDICT_ICON: Record<string, string> = {
    unbreakable: "✅",
    stressed: "⚠️",
    broken: "❌",
};

const VERDICT_COLOR: Record<string, string> = {
    unbreakable: "var(--color-neon)",
    stressed: "var(--color-warning)",
    broken: "var(--color-danger)",
};

export default function CrucibleTable({ procedures }: { procedures: CrucibleProcedure[] }) {
    const [expanded, setExpanded] = useState<string | null>(null);

    return (
        <div className="space-y-2">
            {procedures.map((proc) => (
                <div key={proc.id} className="glass-card p-0 overflow-hidden">
                    {/* Row */}
                    <button
                        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--color-glass-hover)] transition-colors"
                        onClick={() => setExpanded(expanded === proc.id ? null : proc.id)}
                    >
                        <span className="text-lg w-6 text-center">{VERDICT_ICON[proc.verdict]}</span>
                        <span className="flex-1 text-sm text-white font-medium">{proc.name}</span>
                        <div className="flex items-center gap-3">
                            <div className="w-16">
                                <div className="confidence-bar-track">
                                    <div
                                        className="confidence-bar-fill"
                                        style={{ width: `${proc.confidence * 100}%`, background: VERDICT_COLOR[proc.verdict] }}
                                    />
                                </div>
                            </div>
                            <span className="text-xs text-[var(--color-rune-dim)] w-10 text-right">
                                {Math.round(proc.confidence * 100)}%
                            </span>
                            <span className="text-xs text-[var(--color-rune-dim)] transition-transform" style={{
                                transform: expanded === proc.id ? "rotate(180deg)" : "rotate(0deg)",
                            }}>
                                ▾
                            </span>
                        </div>
                    </button>

                    {/* Expanded edge cases */}
                    {expanded === proc.id && (
                        <div className="px-4 pb-3 pt-1 border-t border-[var(--color-glass-border)]">
                            <p className="text-xs text-[var(--color-rune-dim)] mb-2">Edge cases tested:</p>
                            <ul className="space-y-1">
                                {proc.edge_cases.map((ec, i) => (
                                    <li key={i} className="text-xs text-[var(--color-rune)] pl-4 relative">
                                        <span className="absolute left-0">•</span>
                                        {ec}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

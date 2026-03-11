"use client";

import { useEffect, useState } from "react";
import { getCrucibleResults, runCrucible } from "@/lib/api";
import type { CrucibleResults } from "@/lib/api";
import CrucibleTable from "@/components/CrucibleTable";
import { useToast } from "@/components/Toast";

export default function CruciblePage() {
    const [results, setResults] = useState<CrucibleResults | null>(null);
    const [loading, setLoading] = useState(true);
    const { toast } = useToast();

    useEffect(() => {
        getCrucibleResults().then((data) => {
            setResults(data);
            setLoading(false);
        });
    }, []);

    const handleRun = async () => {
        await runCrucible();
        toast("Crucible cycle started — stress-testing all procedures...", "info");
    };

    if (loading || !results) {
        return (
            <div className="page-enter max-w-5xl">
                <div className="glass-card p-8 animate-pulse">
                    <div className="h-6 w-48 bg-[var(--color-void-lighter)] rounded mb-4" />
                    <div className="h-4 w-64 bg-[var(--color-void-lighter)] rounded" />
                </div>
            </div>
        );
    }

    return (
        <div className="page-enter max-w-5xl">
            {/* Header */}
            <div className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold mb-2">
                        <span className="text-[var(--color-neon)]">🧪</span> Crucible
                    </h1>
                    <p className="text-[var(--color-rune-dim)]">
                        Last run: {new Date(results.last_run).toLocaleString()} · {results.total_tested} procedures tested
                    </p>
                </div>
                <button onClick={handleRun} className="btn-neon px-4 py-2 text-sm">
                    Run Crucible
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-8 stagger-in">
                <div className="glass-card p-4 text-center">
                    <p className="text-3xl font-bold text-[var(--color-neon)]">{results.unbreakable}</p>
                    <p className="text-xs text-[var(--color-rune-dim)] mt-1">✅ Unbreakable</p>
                </div>
                <div className="glass-card p-4 text-center">
                    <p className="text-3xl font-bold text-[var(--color-warning)]">{results.stressed}</p>
                    <p className="text-xs text-[var(--color-rune-dim)] mt-1">⚠️ Stressed</p>
                </div>
                <div className="glass-card p-4 text-center">
                    <p className="text-3xl font-bold text-[var(--color-danger)]">{results.broken}</p>
                    <p className="text-xs text-[var(--color-rune-dim)] mt-1">❌ Broken</p>
                </div>
            </div>

            {/* Procedure Table */}
            <h2 className="text-sm font-semibold text-[var(--color-rune-dim)] uppercase tracking-wider mb-3">Procedures</h2>
            <CrucibleTable procedures={results.procedures} />
        </div>
    );
}

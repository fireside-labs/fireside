"use client";

import { useEffect, useState } from "react";
import { getDebates, interveneDebate } from "@/lib/api";
import type { Debate } from "@/lib/api";
import DebateTranscript from "@/components/DebateTranscript";
import ConsensusMeter from "@/components/ConsensusMeter";
import { useToast } from "@/components/Toast";

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
    active: { label: "🗣️ Active", color: "var(--color-info)" },
    consensus: { label: "✅ Consensus", color: "var(--color-neon)" },
    deadlock: { label: "⚠️ Deadlock", color: "var(--color-warning)" },
    escalated: { label: "🖐 Escalated", color: "var(--color-danger)" },
};

export default function DebatePage() {
    const [debates, setDebates] = useState<Debate[]>([]);
    const [selected, setSelected] = useState<Debate | null>(null);
    const [intervention, setIntervention] = useState("");
    const [loading, setLoading] = useState(true);
    const { toast } = useToast();

    useEffect(() => {
        getDebates().then((data) => {
            setDebates(data);
            setLoading(false);
            if (data.length > 0) setSelected(data[0]);
        });
    }, []);

    const handleIntervene = async () => {
        if (!selected || !intervention.trim()) return;
        await interveneDebate(selected.id, intervention.trim());
        toast("Your intervention has been added to the debate", "success");
        setIntervention("");
    };

    if (loading) {
        return (
            <div className="page-enter max-w-6xl">
                <div className="glass-card p-8 animate-pulse">
                    <div className="h-6 w-48 bg-[var(--color-void-lighter)] rounded mb-4" />
                    <div className="h-4 w-64 bg-[var(--color-void-lighter)] rounded" />
                </div>
            </div>
        );
    }

    return (
        <div className="page-enter max-w-6xl">
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2">
                    <span className="text-[var(--color-neon)]">🗣️</span> Socratic Debates
                </h1>
                <p className="text-[var(--color-rune-dim)]">
                    Multi-persona deliberation on design decisions
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Debate list */}
                <div className="space-y-2">
                    <h2 className="text-sm font-semibold text-[var(--color-rune-dim)] uppercase tracking-wider mb-3">History</h2>
                    {debates.map((d) => {
                        const badge = STATUS_BADGE[d.status] || STATUS_BADGE.active;
                        const isActive = selected?.id === d.id;
                        return (
                            <button
                                key={d.id}
                                onClick={() => setSelected(d)}
                                className="w-full text-left glass-card p-3 transition-all"
                                style={{
                                    borderColor: isActive ? badge.color : "var(--color-glass-border)",
                                    borderWidth: isActive ? 2 : 1,
                                }}
                            >
                                <p className="text-sm text-white font-medium line-clamp-2">{d.topic}</p>
                                <div className="flex items-center gap-2 mt-1.5">
                                    <span className="text-[10px]" style={{ color: badge.color }}>{badge.label}</span>
                                    <span className="text-[10px] text-[var(--color-rune-dim)]">
                                        R{d.rounds_completed}/{d.max_rounds}
                                    </span>
                                </div>
                            </button>
                        );
                    })}
                </div>

                {/* Debate detail */}
                <div className="lg:col-span-2">
                    {selected ? (
                        <div>
                            {/* Header */}
                            <div className="glass-card p-5 mb-4">
                                <h2 className="text-white font-semibold mb-2">{selected.topic}</h2>
                                <div className="flex items-center gap-4 mb-3">
                                    <span className="text-xs" style={{ color: STATUS_BADGE[selected.status]?.color }}>
                                        {STATUS_BADGE[selected.status]?.label}
                                    </span>
                                    <span className="text-xs text-[var(--color-rune-dim)]">
                                        Round {selected.rounds_completed}/{selected.max_rounds}
                                    </span>
                                </div>
                                <ConsensusMeter value={selected.consensus} max={0.7} />
                            </div>

                            {/* Transcript */}
                            <DebateTranscript messages={selected.messages} />

                            {/* Intervene */}
                            <div className="glass-card p-4 mt-4">
                                <p className="text-xs text-[var(--color-rune-dim)] mb-2">Add your take to the debate:</p>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={intervention}
                                        onChange={(e) => setIntervention(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && handleIntervene()}
                                        placeholder="Your objection or feedback..."
                                        className="flex-1 bg-transparent text-white placeholder-[var(--color-rune-dim)] text-sm outline-none"
                                    />
                                    <button
                                        onClick={handleIntervene}
                                        disabled={!intervention.trim()}
                                        className="btn-neon text-xs px-3 py-1.5"
                                        style={{ opacity: intervention.trim() ? 1 : 0.4 }}
                                    >
                                        🖐️ Intervene
                                    </button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-20 text-[var(--color-rune-dim)]">
                            Select a debate to view transcript
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

"use client";

import type { DebateMessage } from "@/lib/api";

const PERSONA_COLORS: Record<string, string> = {
    "🏛️ Architect": "#a855f7",
    "😈 Devil's Advocate": "#ef4444",
    "👤 End User": "#3b82f6",
    "💬 Thor": "#00ff88",
};

export default function DebateTranscript({ messages }: { messages: DebateMessage[] }) {
    // Group by round
    const rounds: Record<number, DebateMessage[]> = {};
    messages.forEach((m) => {
        if (!rounds[m.round]) rounds[m.round] = [];
        rounds[m.round].push(m);
    });

    return (
        <div className="space-y-4">
            {Object.entries(rounds).map(([round, msgs]) => (
                <div key={round}>
                    <p className="text-xs text-[var(--color-rune-dim)] mb-2 uppercase tracking-wider">
                        Round {round} — {msgs[0].type === "critique" ? "Critique" : msgs[0].type === "defense" ? "Defense" : "Response"}
                    </p>
                    <div className="space-y-2">
                        {msgs.map((msg, i) => {
                            const color = PERSONA_COLORS[msg.persona] || "var(--color-rune)";
                            return (
                                <div
                                    key={i}
                                    className="glass-card p-3"
                                    style={{ borderLeftWidth: 3, borderLeftColor: color }}
                                >
                                    <div className="flex items-center gap-2 mb-1.5">
                                        <span className="text-sm font-semibold" style={{ color }}>{msg.persona}</span>
                                        <span className="text-[10px] text-[var(--color-rune-dim)] font-mono">
                                            {msg.agent}/{msg.model}
                                        </span>
                                    </div>
                                    <p className="text-sm text-[var(--color-rune)] leading-relaxed">{msg.content}</p>
                                </div>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
}

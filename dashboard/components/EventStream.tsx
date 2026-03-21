"use client";

import { ValhallaEvent } from "@/lib/api";

interface Props {
    events: ValhallaEvent[];
    connected: boolean;
}

const TOPIC_COLORS: Record<string, { color: string; bg: string; icon: string }> = {
    hypothesis: { color: "#b380ff", bg: "rgba(179,128,255,0.12)", icon: "🧪" },
    prediction: { color: "#44aaff", bg: "rgba(68,170,255,0.12)", icon: "🔮" },
    "model-switch": { color: "#F59E0B", bg: "rgba(245,158,11,0.12)", icon: "⚡" },
    node: { color: "#ffaa22", bg: "rgba(255,170,34,0.12)", icon: "○" },
    plugin: { color: "#00ccaa", bg: "rgba(0,204,170,0.12)", icon: "◆" },
    config: { color: "#a0a0b8", bg: "rgba(160,160,184,0.12)", icon: "⚙" },
    error: { color: "#ff4466", bg: "rgba(255,68,102,0.12)", icon: "⚠" },
    pipeline: { color: "#F59E0B", bg: "rgba(245,158,11,0.12)", icon: "⚡" },
    "pipeline.stage_started": { color: "#60A5FA", bg: "rgba(96,165,250,0.12)", icon: "▶" },
    "pipeline.stage_complete": { color: "#34D399", bg: "rgba(52,211,153,0.12)", icon: "✔" },
    "pipeline.file_created": { color: "#A78BFA", bg: "rgba(167,139,250,0.12)", icon: "📄" },
    "pipeline.shipped": { color: "#F59E0B", bg: "rgba(245,158,11,0.15)", icon: "🚀" },
    "pipeline.escalated": { color: "#ff4466", bg: "rgba(255,68,102,0.12)", icon: "🖐" },
    "pipeline.human_intervention": { color: "#22D3EE", bg: "rgba(34,211,238,0.12)", icon: "💬" },
    "pipeline.gate_waiting": { color: "#FBBF24", bg: "rgba(251,191,36,0.12)", icon: "⏸" },
    "pipeline.gate_approved": { color: "#34D399", bg: "rgba(52,211,153,0.12)", icon: "✅" },
    "pipeline.gate_rejected": { color: "#F87171", bg: "rgba(248,113,113,0.12)", icon: "❌" },
};

export default function EventStream({ events, connected }: Props) {
    return (
        <div className="glass-card p-4 flex flex-col" style={{ height: "100%" }}>
            {/* Header */}
            <div className="flex items-center justify-between mb-3 pb-3 border-b border-[var(--color-glass-border)]">
                <h3 className="text-white font-semibold text-sm">📡 Event Stream</h3>
                <div className="flex items-center gap-2">
                    <div
                        className={connected ? "status-online" : "status-offline"}
                        style={{ width: 6, height: 6 }}
                    />
                    <span className="text-xs text-[var(--color-rune-dim)]">
                        {connected ? "Live" : "Polling"}
                    </span>
                </div>
            </div>

            {/* Event List */}
            <div className="flex-1 overflow-y-auto event-stream-list" style={{ maxHeight: 500 }}>
                {events.map((event) => {
                    const topic = TOPIC_COLORS[event.topic] || TOPIC_COLORS.config;
                    return (
                        <div
                            key={event.id}
                            className="event-item flex items-start gap-3 py-2.5 px-2 rounded-lg mb-1"
                            style={{ transition: "background 0.2s" }}
                        >
                            {/* Topic Icon */}
                            <span
                                className="text-xs mt-0.5 w-5 h-5 rounded flex items-center justify-center flex-shrink-0"
                                style={{ background: topic.bg, color: topic.color }}
                            >
                                {topic.icon}
                            </span>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-[var(--color-rune)] leading-relaxed truncate">
                                    {event.summary}
                                </p>
                                <div className="flex items-center gap-2 mt-0.5">
                                    <span className="text-xs font-mono text-[var(--color-rune-dim)]">
                                        {event.timestamp}
                                    </span>
                                    <span
                                        className="text-xs px-1.5 py-0.5 rounded"
                                        style={{ background: topic.bg, color: topic.color, fontSize: 10 }}
                                    >
                                        {event.source}
                                    </span>
                                </div>
                            </div>
                        </div>
                    );
                })}

                {events.length === 0 && (
                    <div className="text-center text-xs text-[var(--color-rune-dim)] py-8">
                        No events yet...
                    </div>
                )}
            </div>
        </div>
    );
}

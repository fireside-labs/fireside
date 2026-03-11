"use client";

import { useState } from "react";

interface QueuedTask {
    id: string;
    text: string;
    status: "pending" | "sent" | "completed" | "failed";
    timestamp: string;
    result?: string;
}

const MOCK_TASKS: QueuedTask[] = [
    { id: "1", text: "Summarize my last 5 git commits", status: "completed", timestamp: "2h ago", result: "You refactored the auth module, added rate limiting, and fixed 2 CSS bugs." },
    { id: "2", text: "Find all TODO comments in the codebase", status: "completed", timestamp: "1h ago", result: "Found 12 TODOs across 8 files. 3 are high priority." },
    { id: "3", text: "Analyze my package.json for security issues", status: "sent", timestamp: "30m ago" },
    { id: "4", text: "Help me draft a launch announcement", status: "pending", timestamp: "Just now" },
];

export default function TaskQueue() {
    const [tasks] = useState<QueuedTask[]>(MOCK_TASKS);
    const [expanded, setExpanded] = useState<string | null>(null);

    const pending = tasks.filter((t) => t.status === "pending").length;
    const sent = tasks.filter((t) => t.status === "sent").length;
    const done = tasks.filter((t) => t.status === "completed").length;

    const STATUS_STYLE: Record<string, { bg: string; text: string; label: string }> = {
        pending: { bg: "rgba(255,255,255,0.05)", text: "var(--color-rune-dim)", label: "⏳ Queued" },
        sent: { bg: "rgba(0,255,136,0.05)", text: "var(--color-neon)", label: "📡 Sent" },
        completed: { bg: "rgba(0,255,136,0.08)", text: "var(--color-neon)", label: "✅ Done" },
        failed: { bg: "rgba(255,68,102,0.05)", text: "var(--color-danger)", label: "❌ Failed" },
    };

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-semibold text-sm">📋 Task Queue</h3>
                <div className="flex gap-2 text-[9px]">
                    {pending > 0 && <span className="text-[var(--color-rune-dim)]">{pending} queued</span>}
                    {sent > 0 && <span className="text-[var(--color-warning)]">{sent} sending</span>}
                    {done > 0 && <span className="text-[var(--color-neon)]">{done} done</span>}
                </div>
            </div>
            <p className="text-[10px] text-[var(--color-rune-dim)] mb-3">
                Tasks queued while offline. They&apos;ll send to your home PC when you&apos;re back online.
            </p>

            <div className="space-y-1.5">
                {tasks.map((task) => {
                    const style = STATUS_STYLE[task.status];
                    return (
                        <div key={task.id}>
                            <button
                                onClick={() => setExpanded(expanded === task.id ? null : task.id)}
                                className="w-full text-left p-2.5 rounded-lg transition-colors"
                                style={{ background: style.bg }}
                            >
                                <div className="flex items-center justify-between">
                                    <p className="text-xs text-[var(--color-rune)] flex-1 mr-2">{task.text}</p>
                                    <span className="text-[9px] whitespace-nowrap" style={{ color: style.text }}>
                                        {style.label}
                                    </span>
                                </div>
                                <p className="text-[9px] text-[var(--color-rune-dim)] mt-0.5">{task.timestamp}</p>
                            </button>
                            {expanded === task.id && task.result && (
                                <div className="mx-2 mt-1 p-2 rounded bg-[var(--color-glass)] border-l-2 border-[var(--color-neon)]">
                                    <p className="text-xs text-[var(--color-rune)]">{task.result}</p>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

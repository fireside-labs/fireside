"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/api";

interface QueuedTask {
    id: string;
    text: string;
    status: "pending" | "sent" | "completed" | "failed" | "active" | "cancelled";
    timestamp: string;
    result?: string;
    schedule?: { description?: string; type?: string };
    run_count?: number;
}

export default function TaskQueue() {
    const [tasks, setTasks] = useState<QueuedTask[]>([]);
    const [expanded, setExpanded] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchTasks = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/v1/scheduler`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            const mapped: QueuedTask[] = (data.tasks || []).map((t: Record<string, unknown>) => ({
                id: t.id as string,
                text: t.task as string || "Untitled task",
                status: mapStatus(t.status as string),
                timestamp: formatAge(t.created_at as number),
                result: t.last_result ? JSON.stringify(t.last_result).slice(0, 200) : undefined,
                schedule: t.schedule as { description?: string; type?: string },
                run_count: t.run_count as number,
            }));
            setTasks(mapped);
            setError(null);
        } catch (e) {
            // If API is down, show empty state (not error)
            if (tasks.length === 0) setError("Scheduler offline");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTasks();
        const interval = setInterval(fetchTasks, 10_000); // Poll every 10s
        return () => clearInterval(interval);
    }, [fetchTasks]);

    const cancelTask = async (taskId: string) => {
        try {
            await fetch(`${API_BASE}/api/v1/scheduler/${taskId}`, { method: "DELETE" });
            fetchTasks();
        } catch {}
    };

    const runNow = async (taskId: string) => {
        try {
            await fetch(`${API_BASE}/api/v1/scheduler/run/${taskId}`, { method: "POST" });
            fetchTasks();
        } catch {}
    };

    const pending = tasks.filter((t) => t.status === "pending" || t.status === "active").length;
    const done = tasks.filter((t) => t.status === "completed").length;
    const cancelled = tasks.filter((t) => t.status === "cancelled").length;

    const STATUS_STYLE: Record<string, { bg: string; text: string; label: string }> = {
        pending: { bg: "rgba(255,255,255,0.05)", text: "var(--color-rune-dim)", label: "⏳ Queued" },
        active: { bg: "rgba(0,255,136,0.05)", text: "var(--color-neon)", label: "🔄 Active" },
        sent: { bg: "rgba(0,255,136,0.05)", text: "var(--color-neon)", label: "📡 Sent" },
        completed: { bg: "rgba(0,255,136,0.08)", text: "var(--color-neon)", label: "✅ Done" },
        failed: { bg: "rgba(255,68,102,0.05)", text: "var(--color-danger)", label: "❌ Failed" },
        cancelled: { bg: "rgba(255,255,255,0.03)", text: "var(--color-rune-dim)", label: "🚫 Cancelled" },
    };

    if (loading) {
        return (
            <div className="glass-card p-5">
                <h3 className="text-white font-semibold text-sm">📋 Task Queue</h3>
                <p className="text-[10px] text-[var(--color-rune-dim)] mt-2 animate-pulse">Loading tasks...</p>
            </div>
        );
    }

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-semibold text-sm">📋 Task Queue</h3>
                <div className="flex gap-2 text-[9px]">
                    {pending > 0 && <span className="text-[var(--color-warning)]">{pending} active</span>}
                    {done > 0 && <span className="text-[var(--color-neon)]">{done} done</span>}
                    {cancelled > 0 && <span className="text-[var(--color-rune-dim)]">{cancelled} off</span>}
                </div>
            </div>

            {error && tasks.length === 0 && (
                <p className="text-[10px] text-[var(--color-rune-dim)] mb-3">
                    {error} — tasks will appear when the backend is running.
                </p>
            )}

            {tasks.length === 0 && !error && (
                <p className="text-[10px] text-[var(--color-rune-dim)] mb-3">
                    No scheduled tasks yet. Ask your AI to &quot;remind me&quot; or &quot;schedule&quot; something!
                </p>
            )}

            <div className="space-y-1.5">
                {tasks.map((task) => {
                    const style = STATUS_STYLE[task.status] || STATUS_STYLE.pending;
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
                                <div className="flex items-center justify-between mt-0.5">
                                    <p className="text-[9px] text-[var(--color-rune-dim)]">{task.timestamp}</p>
                                    {task.schedule?.description && (
                                        <p className="text-[9px] text-[var(--color-rune-dim)]">{task.schedule.description}</p>
                                    )}
                                </div>
                            </button>
                            {expanded === task.id && (
                                <div className="mx-2 mt-1 p-2 rounded bg-[var(--color-glass)] border-l-2 border-[var(--color-neon)]">
                                    {task.result && <p className="text-xs text-[var(--color-rune)] mb-2">{task.result}</p>}
                                    {task.run_count !== undefined && task.run_count > 0 && (
                                        <p className="text-[9px] text-[var(--color-rune-dim)] mb-2">Ran {task.run_count} time(s)</p>
                                    )}
                                    <div className="flex gap-2">
                                        {task.status === "active" && (
                                            <>
                                                <button
                                                    onClick={() => runNow(task.id)}
                                                    className="text-[9px] px-2 py-1 rounded bg-[rgba(245,158,11,0.1)] text-[#F59E0B] hover:bg-[rgba(245,158,11,0.2)] transition-colors"
                                                >
                                                    ▶ Run Now
                                                </button>
                                                <button
                                                    onClick={() => cancelTask(task.id)}
                                                    className="text-[9px] px-2 py-1 rounded bg-[rgba(255,68,102,0.1)] text-[var(--color-danger)] hover:bg-[rgba(255,68,102,0.2)] transition-colors"
                                                >
                                                    ✕ Cancel
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ── Helpers ──

function mapStatus(s: string): QueuedTask["status"] {
    if (s === "active") return "active";
    if (s === "completed") return "completed";
    if (s === "cancelled") return "cancelled";
    if (s === "failed") return "failed";
    return "pending";
}

function formatAge(epochSeconds: number): string {
    if (!epochSeconds) return "Unknown";
    const diff = Math.floor(Date.now() / 1000 - epochSeconds);
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}
